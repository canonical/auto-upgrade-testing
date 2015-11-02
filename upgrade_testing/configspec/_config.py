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


logger = logging.getLogger(__name__)


class TestSpecification:
    """Wraps details about the specification.

    :param provision_settings: ProvisionSpecification object.

    i.e. the provisionin parts etc.
    """
    def __init__(self, details, provision_settings):
        self.provisioning = provision_settings
        conf_version = str(details.get('conf_version', None))

        # Rudimentary example of versioned configs.l
        try:
            if conf_version is None:
                self._reader(details)
            elif conf_version == "1.0":
                self._reader_1_0(details)
        except KeyError as e:
            logger.error(
                'Missing required configuration detail: {}'.format(str(e))
            )

    def _reader(self, details):
        self.name = details['testname']
        # XXX There is a miss-naming here that needs to be touched up in the
        # schema
        self.pre_upgrade_scripts = details['test-details']['pre_upgrade_tests']
        self.post_upgrade_tests = details['test-details']['post_upgrade_tests']
        # This will cause issues! Perhaps we need to deprecate non 1.0 config.
        self._test_source_dir = './'

    def _reader_1_0(self, details):
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


class ProvisionSpecification:

    def __init__(self, backend, releases, distribution='ubuntu'):
        """Instantiate an object containing Provisioning details.

        :param backend: String stating which backend is required.
        :param releases: List of strings stating which releases will be
          needed. Element 0 will be the starting release.

        """
        # Architecture isn't mentioned here but could be in the future.
        self.backend = backend
        self.distribution = distribution
        if len(releases) == 0:
            raise ValueError('No releases were provided')
        self.releases = releases
        self.initial_release = releases[0]
        self.final_release = releases[-1]

    @staticmethod
    def from_testspec(spec):
        # Initial example of being able to version configs.
        version = str(spec.get('conf_version', None))
        if version is None:
            # Based off the current schema which will change shortly
            backend = spec['backend']
            releases = [
                spec['test-details']['start-release'],
                spec['test-details']['end-release']
            ]
        elif version == "1.0":
            # I think we can match the required details to commandline args so
            # this could become:
            # return ProvisionSpecification.from_provisionspec(spec)
            backend = spec['provisioning']['backend']
            releases = spec['provisioning']['releases']
        else:
            raise ValueError('Insufficent provisioning details.')

        return ProvisionSpecification(backend, releases)

    @staticmethod
    def from_provisionspec(spec):
        pass

    def __repr__(self):
        return '{classname}(backend={backend}, distribution={dist}, releases={releases})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases
        )


def definition_reader(testdef_filepath, provisiondef_filepath=None):
    """Produce a TestSpecification from the provided testdef file.

    Given a provisiondef file path too incorporates those details into the
    specification otherwise collects these details from the testspec.
    Will raise an exception if this is incorrect.

    """
    # Need a better way to confirm this.
    if testdef_filepath.endswith('.yaml'):
        testdef = _read_yaml_config(testdef_filepath)
    else:
        raise ValueError(
            'Unknown configuration file format: {}'.format(
                testdef_filepath
            )
        )

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


def _read_yaml_config(filepath):
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        err_msg = 'Unable to open config file: {}'.format(filepath)
        logger.error(err_msg)
        e.args += (err_msg, )
        raise
