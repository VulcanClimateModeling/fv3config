import os
import f90nml
from .exceptions import InvalidFileError
from .datastore import (
    get_base_forcing_directory, get_orographic_forcing_directory,
    get_initial_conditions_directory, link_directory, link_file,
    get_field_table_filename, get_diag_table_filename,
)


package_directory = os.path.dirname(os.path.realpath(__file__))

def get_default_config_dict():
    return f90nml.read(os.path.join(package_directory, 'data/default.nml'))


def config_dict_to_namelist(config_dict, namelist_filename):
    if os.path.isfile(namelist_filename):
        os.remove(namelist_filename)
    f90nml.write(config_dict, namelist_filename)


def config_dict_from_namelist(namelist_filename):
    try:
        return_dict = f90nml.read(namelist_filename)
    except FileNotFoundError:
        raise InvalidFileError(f'namelist {namelist_filename} does not exist')
    return return_dict


def config_dict_from_directory(dirname):
    return config_dict_from_namelist(os.path.join(dirname, 'input.nml'))


def write_run_directory(config_dict, target_directory):
    initial_conditions_dir = get_initial_conditions_directory(config_dict)
    base_forcing_dir = get_base_forcing_directory(config_dict)
    orographic_forcing_dir = get_orographic_forcing_directory(config_dict)
    field_table_filename = get_field_table_filename(config_dict)
    diag_table_filename = get_diag_table_filename(config_dict)
    if not os.path.isdir(target_directory):
        os.mkdir(target_directory)
    link_directory(base_forcing_dir, target_directory)
    link_directory(orographic_forcing_dir, target_directory)
    link_directory(initial_conditions_dir, target_directory)
    link_file(field_table_filename, os.path.join(target_directory, 'field_table'))
    link_file(diag_table_filename, os.path.join(target_directory, 'diag_table'))
    config_dict_to_namelist(config_dict, os.path.join(target_directory, 'input.nml'))

