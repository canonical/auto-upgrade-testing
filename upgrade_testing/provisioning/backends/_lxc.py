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
import subprocess

from upgrade_testing.provisioning.backends._base import ProviderBackend

logger = logging.getLogger(__name__)


class LXCBackend(ProviderBackend):

    def __init__(self, provision_spec):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.spec = provision_spec

    def available(self):
        """Return true if an lxc container exists that matches the provided
        args.

        """
        container_name = 'adt-{}'.format(self.spec.initial_release)
        return container_name in lxc.list_containers()

    def create(self):
        """Create an lxc container."""

        logger.info('Creating lxc container for run.')
        # Use sudo here as it's needed for building the lxc container.
        cmd = 'sudo adt-build-lxc {} {}'.format(
            self.spec.distribution, self.spec.initial_release
        )
        # TODO: Provide further checking here.
        subprocess.check_output(cmd, shell=True)

    def get_adt_run_args(self):
        return ['lxc', '-s', 'adt-{}'.format(self.spec.initial_release)]

    def __repr__(self):
        return '{classname}(release={release})'.format(
            classname=self.__class__.__name__,
            release=self.spec.initial_release
        )
