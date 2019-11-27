import logging
import os
import shutil
from subprocess import check_call, Popen, PIPE
from ._datastore import (
    get_initial_conditions_directory, get_orographic_forcing_directory,
    get_base_forcing_directory, is_gsbucket_url
)
from ._tables import (
    get_data_table_filename, get_diag_table_filename, get_field_table_filename
)
from ._exceptions import ConfigError, DelayedImportError
from fsspec.implementations.local import LocalFileSystem

try:
    import gcsfs
except ImportError as err:
    gcsfs = DelayedImportError(err)

LOCAL_FS = LocalFileSystem()


def _get_gcloud_project():
    # import here because this is an optional dependency
    import google.auth
    return os.environ.get(google.auth.environment_vars.PROJECT)


def is_dict_or_list(option):
    return isinstance(option, dict) or isinstance(option, list)


def ensure_is_list(asset):
    """If argument is a dict, return length 1 list containing dict"""
    if isinstance(asset, dict):
        return [asset]
    elif isinstance(asset, list):
        return asset
    else:
        raise ConfigError('Asset must be a dict or list of dicts')


def get_orographic_forcing_asset_list(config):
    """Return asset_list for orographic forcing"""
    source_directory = get_orographic_forcing_directory(config)
    return asset_list_from_path(source_directory, target_location='INPUT',
                                copy_method='link')


def get_base_forcing_asset_list(config):
    """Return asset_list for base forcing"""
    if is_dict_or_list(config['forcing']):
        return ensure_is_list(config['forcing'])
    else:
        source_directory = get_base_forcing_directory(config)
        return asset_list_from_path(source_directory, copy_method='link')


def get_initial_conditions_asset_list(config):
    """Return asset_list for initial conditions. """
    if is_dict_or_list(config['initial_conditions']):
        return ensure_is_list(config['initial_conditions'])
    else:
        source_directory = get_initial_conditions_directory(config)
        return asset_list_from_path(source_directory, target_location='INPUT')


def get_data_table_asset(config):
    """Return asset for data_table"""
    data_table_filename = get_data_table_filename(config)
    location, name = os.path.split(data_table_filename)
    return get_asset_dict(location, name, target_name='data_table')


def get_diag_table_asset(config):
    """Return asset for diag_table"""
    diag_table_filename = get_diag_table_filename(config)
    location, name = os.path.split(diag_table_filename)
    return get_asset_dict(location, name, target_name='diag_table')


def get_field_table_asset(config):
    """Return asset for field_table"""
    field_table_filename = get_field_table_filename(config)
    location, name = os.path.split(field_table_filename)
    return get_asset_dict(location, name, target_name='field_table')


def get_asset_dict(source_location, source_name, target_location='',
                   target_name=None, copy_method='copy'):
    """Helper function to generate asset for a particular file

    Args:
        source_location (str): path to directory containing source file
        source_name (str): filename of source file
        target_location (str, optional): sub-directory to which file will
            be written, relative to run directory root. Defaults to empty
            string (i.e. root of run directory).
        target_name (str, optional): filename to which file will be written.
            Defaults to None, in which case source_name is used.
        copy_method (str, optional): flag to determine whether file is
            copied ('copy') or hard-linked ('link'). Defaults to 'copy'.

    Returns:
        dict: an asset dictionary
    """
    if target_name is None:
        target_name = source_name
    asset = {
        'source_location': source_location,
        'source_name': source_name,
        'target_location': target_location,
        'target_name': target_name,
        'copy_method': copy_method,
    }
    return asset


def _get_gcloud_fs():
    return gcsfs.GCSFileSystem(project=_get_gcloud_project())


def asset_list_from_path(location, target_location='', copy_method='copy'):
    """Return asset_list from all files within a given path.

    Args:
        location (str): local path or google cloud storage url.
        target_location (str, optional): target_location used for generated assets.
            Defaults to '' which is root of run-directory.
        copy_method ('copy' or 'link', optional): whether to copy or link assets,
            defaults to 'copy'. If location is a google cloud storage url, this option
            is ignored and files are copied.

    Returns:
        list: a list of asset dictionaries
        """
    if is_gsbucket_url(location):
        copy_method = 'copy'
        fs = _get_gcloud_fs()
    else:
        fs = LOCAL_FS
    asset_list = []
    path_list = fs.walk(location)
    for dirname, _, files in path_list:
        print(dirname, files, target_location)
        subdir_target_location = os.path.join(
            target_location, os.path.relpath(dirname, start=location)
        )
        for basename in files:
            asset_list.append(
                get_asset_dict(
                    dirname,
                    basename,
                    target_location=subdir_target_location,
                    copy_method=copy_method,
                )
            )
    return asset_list


def write_asset(asset, target_directory):
    """Write file represented by asset to target_directory

    Args:
        asset (dict): an asset dict
        target_directory (str): path to a directory in which all files will be written
    """
    check_asset_has_required_keys(asset)
    source_path = os.path.join(asset['source_location'], asset['source_name'])
    target_path = os.path.join(target_directory, asset['target_location'], asset['target_name'])
    copy_method = asset['copy_method']
    if not os.path.exists(os.path.dirname(target_path)):
        os.makedirs(os.path.dirname(target_path))
    if copy_method == 'copy':
        copy_file(source_path, target_path)
    elif copy_method == 'link':
        link_file(source_path, target_path)
    else:
        raise ConfigError(
            f'Behavior of copy_method {copy_method} not defined for {source_path} asset'
        )


def write_assets_to_directory(config, target_directory):
    asset_list = config_to_asset_list(config)
    write_asset_list(asset_list, target_directory)


def write_asset_list(asset_list, target_directory):
    """Loop over list of assets and write them all"""
    for asset in asset_list:
        write_asset(asset, target_directory)


def check_asset_has_required_keys(asset):
    """Check asset has all of its required keys"""
    required_asset_keys = ['source_location', 'source_name', 'target_location',
                           'target_name', 'copy_method']
    for required_asset_key in required_asset_keys:
        if required_asset_key not in asset:
            raise ConfigError(f'Assets must have a {required_asset_key}')


def config_to_asset_list(config):
    """Convert a configuration dictionary to an asset list. The asset list
    will contain all files for the run directory except the namelist."""
    asset_list = get_initial_conditions_asset_list(config)
    asset_list += get_base_forcing_asset_list(config)
    asset_list += get_orographic_forcing_asset_list(config)
    asset_list.append(get_field_table_asset(config))
    asset_list.append(get_diag_table_asset(config))
    asset_list.append(get_data_table_asset(config))
    if 'patch_files' in config:
        if is_dict_or_list(config['patch_files']):
            asset_list += ensure_is_list(config['patch_files'])
        else:
            raise ConfigError(
                'patch_files item in config dictionary must be an asset dict or '
                'list of asset dicts')
    return asset_list


def link_file(source_item, target_item):
    if is_gsbucket_url(source_item) or is_gsbucket_url(target_item):
        raise NotImplementedError(
            'cannot perform linking operation involving remote urls '
            f'from {source_item} to {target_item}'
        )
    if os.path.exists(target_item):
        os.remove(target_item)
    os.link(source_item, target_item)


def copy_file(source_path, target_path):
    if is_gsbucket_url(source_path):
        _get_gcloud_fs().get(source_path, target_path)
    else:
        LOCAL_FS.get(source_path, target_path)