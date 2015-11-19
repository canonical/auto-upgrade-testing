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


class TouchBackend(ProviderBackend):

    def __init__(self, channel, revision, password, serial=None):
        """Provide Touch device capabilities as defined in the provision spec.

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
        serials = _get_connected_serials()
        if self.serial:
            return self.serial in serials
        else:
            if not any(serials):
                raise RuntimeError('No devices found.')
            elif len(serials) > 1:
                raise RuntimeError(
                    'Multiple devices found with no serial '
                    'provided to identify target testbed.'
                )

            return True

    def create(self):
        """Ensures that the testbed is flashed and ready to use.

        This includes:
          - Flashing to the right channel/revision
          - Altering the device so that it is read/writeable.
            (This is a requirement for being able to test on it. without using
            the users directory or tmp. Hmm.)

        """

        required_state = TouchBackend.format_device_state_string(
            self.revision,
            self.channel
        )
        actual_state = _get_device_current_state(self.serial)

        if actual_state != required_state:
            logger.info(
                'Device not in required state. Flashing device for run.'
            )
            logger.warning('No actual command here.')
            logger.info('Flashing completed..')
        else:
            logger.info(
                'Device is in required state ({}) no need for flashing'.format(
                    required_state
                )
            )

    def get_adt_run_args(self):
        cmd = ['ssh', '-s', 'adb', '--', '-p', self.password]
        if self.serial is not None:
            cmd = cmd + ['-s', self.serial]
        return cmd

    @property
    def name(self):
        return 'touch'

    @staticmethod
    def format_device_state_string(channel, revision):
        return '{channel}:{rev}'.format(channel=channel, rev=revision)

    def __repr__(self):
        return '{classname}(channel={channel} revno={revno})'.format(
            classname=self.__class__.__name__,
            channel=self.channel,
            revno=self.revision
        )


def _get_connected_serials():
    cmd = ['adb', 'devices']
    output = subprocess.check_output(cmd, universal_newlines=True)
    serials = output.split('\n')[1:]  # Skip title line
    return [s for s in serials if s != '']


def _get_current_device_details(serial=None):
    if serial is not None:
        detail_cmd = ['adb', '-s', serial, 'shell', 'system-image-cli', '-i']
    else:
        detail_cmd = ['adb', 'shell', 'system-image-cli', '-i']

    try:
        output = subprocess.check_output(detail_cmd)
        return {
            detail[0].replace(' ', '_'): detail[1] for detail in
            [line.split(':') for line in output.split('\n') if line != '']
        }
    except subprocess.CalledProcessError as e:
        logger.error('Failed to collect device details: '.format(str(e)))


def _get_device_current_state(serial=None):
    """Return {channel}:{rev} detail for the requested device."""
    image_details = _get_current_device_details(serial)
    return TouchBackend.format_device_state_string(
        channel=image_details['channel'],
        rev=image_details['version_version']
    )
