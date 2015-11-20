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
import yaml

from upgrade_testing.provisioning import ProvisionSpecification

logger = logging.getLogger(__name__)


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
        self.pre_upgrade_scripts = details['pre_upgrade_scripts']
        self.post_upgrade_tests = details['post_upgrade_tests']
        self._test_source_dir = details['script_location']

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
