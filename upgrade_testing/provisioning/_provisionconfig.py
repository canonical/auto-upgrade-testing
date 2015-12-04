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

from upgrade_testing.provisioning import backends

logger = logging.getLogger(__name__)


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

    @property
    def backend_name(self):
        """Return the name of the provision backend."""
        return self.backend.name

    def backend_available(self):
        """Return True if the provisioning backend is available."""
        raise NotImplementedError()

    def create(self):
        """Provision the stored backend."""
        raise NotImplementedError()

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
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
        touch=TouchProvisionSpecification,
        qemu=QemuProvisionSpecification,
    )
    try:
        return __spec_map[spec_name]
    except KeyError:
        logger.error('Unknown spec name: {}'.format(spec_name))
        raise


class LXCProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config):
        # Defaults to ubuntu
        self.distribution = provision_config.get('distribution', 'ubuntu')
        self.releases = provision_config['releases']

        self.backend = backends.LXCBackend(
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

    @property
    def backend_name(self):
        """Return the name of the provision backend."""
        return self.backend.name

    def backend_available(self):
        """Return True if the provisioning backend is available."""
        return self.backend.available()

    def create(self):
        """Provision the stored backend."""
        return self.backend.create()

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        return self.backend.get_adt_run_args(**kwargs)

    def __repr__(self):
        return '{classname}(backend={backend}, distribution={dist}, releases={releases})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases
        )


class TouchProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config):
        try:
            self.channel = provision_config['channel']
            self.revisions = provision_config['revisions']
            password = provision_config['password']
        except KeyError as e:
            raise ValueError('Missing config detail: {}'.format(str(e)))

        serial = provision_config.get('serial', None)
        recovery_file = provision_config.get('recovery_file', None)
        self.backend = backends.TouchBackend(
            self.initial_state,
            password,
            serial,
            recovery_file,
        )

    def _construct_state_string(self, rev):
        return backends.TouchBackend.format_device_state_string(
            self.channel,
            rev
        )

    @property
    def system_states(self):
        return [self._construct_state_string(r) for r in self.revisions]

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        return self._construct_state_string(self.revisions[0])

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        return self._construct_state_string(self.revisions[-1])

    @property
    def backend_name(self):
        """Return the name of the provision backend."""
        return self.backend.name

    def backend_available(self):
        """Return True if the provisioning backend is available."""
        return self.backend.available()

    def create(self):
        """Provision the stored backend."""
        return self.backend.create()

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        return self.backend.get_adt_run_args(**kwargs)

    def __repr__(self):
        return '{classname}(backend={backend}, channel={channel}, revisions={revisions})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            channel=self.channel,
            revisions=self.system_states
        )


class QemuProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config):
        self.releases = provision_config['releases']
        self.arch = provision_config.get('arch', 'amd64')
        self.image_name = provision_config.get(
            'image_name', 'adt-{}-{}-cloud.img'.format(self.initial_state,
                                                       self.arch))
        self.build_args = provision_config.get('build_args', [])

        self.backend = backends.QemuBackend(
            self.initial_state,
            self.arch,
            self.image_name,
            self.build_args,
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

    def backend_available(self):
        """Return True if the provisioning backend is available."""
        return self.backend.available()

    def create(self):
        """Provision the stored backend."""
        return self.backend.create()

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        return self.backend.get_adt_run_args(**kwargs)

    def __repr__(self):
        return '{classname}(backend={backend}, distribution={dist}, releases={releases})'.format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases
        )
