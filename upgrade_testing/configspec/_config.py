#
# Ubuntu Upgrade Testing
# Copyright (C) 2015 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import os
import yaml

from collections import namedtuple

from upgrade_testing.provisioning import ProvisionSpecification

logger = logging.getLogger(__name__)


ScriptStore = namedtuple('ScriptStore', ['executables', 'location'])


class TestSpecification:
    """Wraps details about the specification.

    :param provision_settings: ProvisionSpecification object.

    i.e. the provisioning parts etc.
    """
    def __init__(self, details, provision_spec):
        self.provisioning = provision_spec

        try:
            self._reader(details)
        except KeyError as e:
            logger.error(
                'Missing required configuration detail: {}'.format(str(e))
            )

    def _reader(self, details):
        self.name = details['testname']

        script_location = details.get('script_location', None)

        self.pre_upgrade_scripts = ScriptStore(
            *_generate_script_list(
                details['pre_upgrade_scripts'],
                script_location
            )
        )
        self.post_upgrade_tests = ScriptStore(
            *_generate_script_list(
                details['post_upgrade_tests'],
                script_location
            )
        )

    @property
    def test_source(self):
        if self._test_source_dir is None:
            return './'
        else:
            return self._test_source_dir

    def __repr__(self):
        return '{classname}(name={name}, provisioning={prov})'.format(
            classname=self.__class__.__name__,
            name=self.name,
            prov=self.provisioning
        )


def _generate_script_list(scripts_or_path, script_location=None):
    """Return a tuple containing a list of script names and a location string.

    Source can either be a path that contains executable files or a list of
    names of an executable

    """

    if isinstance(scripts_or_path, list):
        # Can we default script_location to './'?
        if script_location is None:
            raise ValueError('No script location supplied for scripts')
        # Already list of scripts, return it.
        return (scripts_or_path, script_location)
    elif os.path.isdir(scripts_or_path):
        abs_path = os.path.abspath(scripts_or_path)
        return (_get_executable_files(abs_path), abs_path)

    raise ValueError(
        'No scripts found. {} is neither a path or list of scripts'
    )


def _get_executable_files(abs_path):
    def is_executable(path):
        return os.access(path, os.X_OK)
    return [
        f for f in os.listdir(abs_path)
        if is_executable(os.join(abs_path, f))
    ]


def definition_reader(testdef_filepath, provisiondef_filepath=None):
    """Produce a TestSpecification from the provided testdef file.

    Given a provisiondef file path too incorporates those details into the
    specification otherwise collects these details from the testspec.
    Will raise an exception if this is incorrect.

    """
    testdef = _load_testdef(testdef_filepath)

    specs = []
    for test in testdef:
        if provisiondef_filepath is None:
            provision_details = ProvisionSpecification.from_testspec(test)
        else:
            # Perhaps we want to be able to pass args to the commandline
            # instead of writiing a file? We would always fudge that and
            # write to a file-like object and use that instead.
            provision_details = ProvisionSpecification.from_provisionspec(
                provisiondef_filepath
            )

        specs.append(TestSpecification(test, provision_details))
    return specs


def _load_testdef(testdef_filepath):
    # Need a better way to confirm this.
    if testdef_filepath.endswith('.yaml'):
        return _read_yaml_config(testdef_filepath)
    else:
        raise ValueError(
            'Unknown configuration file format: {}'.format(
                testdef_filepath
            )
        )


def _read_yaml_config(filepath):
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        err_msg = 'Unable to open config file: {}'.format(filepath)
        logger.error(err_msg)
        e.args += (err_msg, )
        raise
