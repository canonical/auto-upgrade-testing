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
import lxc
import os

from upgrade_testing.provisioning._util import run_command_with_logged_output
from upgrade_testing.provisioning.backends._base import ProviderBackend

logger = logging.getLogger(__name__)


class LXCBackend(ProviderBackend):

    def __init__(self, release, distribution, arch):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.release = release
        self.distro = distribution
        self.arch = arch

    def available(self):
        """Return true if an lxc container exists that matches the provided
        args.

        """
        container_name = self._get_container_name()
        logger.info('Checking for {}'.format(container_name))
        return container_name in lxc.list_containers()

    def _get_container_name(self):
        return 'adt-{}-{}'.format(self.release, self.arch)

    def create(self, adt_base_path):
        """Create an lxc container."""

        logger.info('Creating lxc container for run.')

        cmd = [
            os.path.join(adt_base_path, 'tools', 'adt-build-lxc'),
            self.distro,
            self.release,
            self.arch,
        ]
        retcode = run_command_with_logged_output(cmd)
        if retcode != 0:
            raise RuntimeError('Failed to create lxc container.')

        logger.info('Container created.')

    def get_adt_run_args(self, **kwargs):
        return ['lxc', '-s', self._get_container_name()]

    @property
    def name(self):
        return 'lxc'

    def __repr__(self):
        return '{classname}(release={release}, arch={arch})'.format(
            classname=self.__class__.__name__,
            release=self.release,
            arch=self.arch,
        )
