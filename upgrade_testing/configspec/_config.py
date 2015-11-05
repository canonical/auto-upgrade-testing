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

from upgrade_testing.provisioning import backends


logger = logging.getLogger(__name__)


class TestSpecification:
    """Wraps details about the specification.

    :param provision_settings: ProvisionSpecification object.

    i.e. the provisionin parts etc.
    """
    def __init__(self, details, provision_spec):
        self.provisioning = provision_spec
        conf_version = str(details.get('conf_version', None))

        # Rudimentary example of versioned configs.
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
    def __init__(self):
        raise NotImplementedError()

    @property
    def system_states(self):
        # Note: Rename from releases
        raise NotImplementedError()

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        raise NotImplementedError()

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        raise NotImplementedError()

    @staticmethod
    def from_testspec(spec):
        backend_name = spec['provisioning']['backend']
        spec_type = get_specification_type(backend_name)
        return spec_type(spec['provisioning'])

    @staticmethod
    def from_provisionspec(spec):
        # A provision spec is almost the same as a testdef provision spec
        # except it doesn't have the parent stanza.
        backend_name = spec['backend']
        spec_type = get_specification_type(backend_name)
        return spec_type(spec)


def get_specification_type(spec_name):
    __spec_map = dict(
        lxc=LXCProvisionSpecification,
        device=DeviceProvisionSpecification
    )
    return __spec_map[spec_name]


class LXCProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config):
        # Defaults to ubuntu
        self.distribution = provision_config.get('distribution', 'ubuntu')
        self.releases = provision_config['releases']

        self.backend = backends. LXCBackend(
            self.initial_state,
            self.distribution
        )

    @property
    def system_states(self):
        # Note: Rename from releases
        return self.releases

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        return self.releases[0]

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        return self.releases[-1]

    def __repr__(self):
        return '{classname}(backend={backend}, distribution={dist}, releases={releases})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases
        )


class DeviceProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config):
        try:
            self.channel = provision_config['channel']
            self.revisions = provision_config['revisions']
        except KeyError as e:
            raise ValueError('Missing config detail: {}'.format(str(e)))

        serial = provision_config.get('serial', None)
        password = provision_config.get('password', None)
        self.backend = backends.DeviceBackend(
            self.channel,
            self.initial_state,
            password,
            serial,
        )

    def _get_revisions(self, config):
        return [config['start-revision'], config['end-revision']]

    def _construct_state_string(self, rev):
        return '{channel}:{rev}'.format(channel=self.channel, rev=rev)

    @property
    def system_states(self):
        # Note: Rename from releases
        return [self._construct_state_string(r) for r in self.revisions]

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        return self._construct_state_string(self.revisions[0])

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        return self._construct_state_string(self.revisions[-1])

    def __repr__(self):
        return '{classname}(backend={backend}, channel={channel}, revisions={revisions})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            channel=self.channel,
            revisions=self.system_states
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
