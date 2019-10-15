import unittest
from fv3config import config_dict_to_namelist, config_dict_from_namelist, config_dict_from_directory, InvalidFileError, default_config_dict
import os
import shutil
import f90nml


test_directory = os.path.dirname(os.path.realpath(__file__))


one_item_namelist = """&fms_io_nml
   checksum_required   = .false.
/"""
one_item_dict = {
    'fms_io_nml': {
        'checksum_required': False
    }
}

all_types_namelist = """&my_nml
    integer_option = 1
    float_option = 2.0
    string_option = "three"
    true_option = .true.
    false_option = .false.
/"""
all_types_dict = {
    'my_nml': {
        'integer_option': 1,
        'float_option': 2.,
        'string_option': 'three',
        'true_option': True,
        'false_option': False,
    }
}


class RunDirectory(object):

    def __init__(self, directory_path):
        os.mkdir(directory_path)
        self.directory_path = directory_path

    def cleanup(self):
        shutil.rmtree(self.directory_path)


class ConfigDictTests(unittest.TestCase):

    def setUp(self):
        self._run_directory_list = []

    def tearDown(self):
        for directory in self._run_directory_list:
            directory.cleanup()

    def make_run_directory(self, directory_name):
        full_path = os.path.join(test_directory, directory_name)
        self._run_directory_list.append(RunDirectory(full_path))
        return full_path

    def test_init_from_empty_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        open(namelist_filename, 'a').close()
        config = config_dict_from_namelist(namelist_filename)
        self.assertIsInstance(config, dict)

    def test_init_from_corrupted_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with open(namelist_filename, 'w') as f:
            f.write('This is not a namelist.')
        with self.assertRaises(InvalidFileError):
            config_dict_from_namelist(namelist_filename)

    def test_init_from_missing_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with self.assertRaises(InvalidFileError):
            config_dict_from_namelist(namelist_filename)

    def test_init_from_one_item_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with open(namelist_filename, 'w') as f:
            f.write(one_item_namelist)
        config = config_dict_from_namelist(namelist_filename)
        self.assertEqual(config, one_item_dict)

    def test_init_from_many_item_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with open(namelist_filename, 'w') as f:
            f.write(all_types_namelist)
        config = config_dict_from_namelist(namelist_filename)
        self.assertEqual(config, all_types_dict)

    def test_init_from_empty_directory(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with self.assertRaises(InvalidFileError):
            config_dict_from_directory(rundir)

    def test_init_from_directory_with_corrupted_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with open(namelist_filename, 'w') as f:
            f.write('This is not a namelist.')
        with self.assertRaises(InvalidFileError):
            config_dict_from_directory(rundir)

    def test_init_from_directory_with_namelist(self):
        rundir = self.make_run_directory('test_rundir')
        namelist_filename = os.path.join(rundir, 'input.nml')
        with open(namelist_filename, 'w') as f:
            f.write(all_types_namelist)
        config = config_dict_from_directory(rundir)
        self.assertEqual(config, all_types_dict)

    def test_empty_write_to_namelist(self):
        pass

    def test_one_item_write_to_namelist(self):
        pass

    def test_many_items_write_to_namelist(self):
        pass

    def test_write_to_existing_namelist(self):
        pass

    def test_write_namelist_int(self):
        pass

    def test_write_namelist_float(self):
        pass

    def test_write_namelist_true(self):
        pass

    def test_write_namelist_false(self):
        pass

    def test_write_namelist_str(self):
        pass


if __name__ == '__main__':
    unittest.main()
