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
import subprocess

from upgrade_testing.provisioning.backends._base import ProviderBackend

logger = logging.getLogger(__name__)


class DeviceBackend(ProviderBackend):

    def __init__(self, channel, revision, password, serial=None):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.channel = channel
        self.revision = revision
        self.serial = serial
        self.password = password

    def available(self):
        """Return true if a device is connected that we can flash.

        """
        cmd = ['adb', 'devices']
        output = subprocess.check_output(cmd, universal_newlines=True)
        serials = output.split('\n')[1:]  # Skip title line
        if self.serial:
            return self.serial in serials
        else:
            # Anything that's not an empty string
            return any(serials)

    def create(self):
        """Flash an attached device with the requested specficiations."""

        logger.info('Flashing device for run.')
        logger.warning('No actual command here.')
        logger.info('Flashing completed..')

    def get_adt_run_args(self):
        cmd = ['ssh', '-s', 'adb', '--', '-p', self.password]
        if self.serial is not None:
            cmd = cmd + ['-s', self.serial]
        return cmd

    def __repr__(self):
        return '{classname}()'.format(
            classname=self.__class__.__name__,
        )
