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
import subprocess

from upgrade_testing.configspec import get_file_data_location
from upgrade_testing.provisioning.backends._base import ProviderBackend
from upgrade_testing.provisioning._util import run_command_with_logged_output

logger = logging.getLogger(__name__)


class TouchBackend(ProviderBackend):

    def __init__(self, initial_state, password, serial=None):
        """Provide Touch device capabilities as defined in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.channel, self.revision = initial_state.split(':')
        self.serial = serial
        self.password = password

        # TODO: Might require recovery file
        self.recovery_file = None

    def available(self):
        """Return true if a device is connected that we can flash.

        """
        return _device_connected(self.serial)

    def _device_in_required_state(self):
        required_state = TouchBackend.format_device_state_string(
            self.channel,
            self.revision
        )
        actual_state = _get_device_current_state(self.serial)
        return required_state == actual_state

    def create(self):
        """Ensures that the testbed is flashed and ready to use.

        This includes:
          - Flashing to the right channel/revision
          - Altering the device so that it is read/writeable.
            (This is a requirement for being able to test on it. without using
            the users directory or tmp. Hmm.)

        """

        if self._device_in_required_state():
            logger.info('Device is already in required state')
            return

        if not self.available():
            err = 'No device available to flash.'
            logger.error(err)
            raise RuntimeError(err)

        logger.info('Preparing to flash device')

        self._put_device_in_bootloader()
        flash_cmd = self._get_flash_command()
        run_command_with_logged_output(flash_cmd)

        logger.info('Flashing completed..')

    def _put_device_in_bootloader(self):
        logger.info('Putting device into bootloader')
        if self.serial is not None:
            cmd = ['adt', '-s', self.serial, 'reboot', 'bootloader']
        else:
            cmd = ['adt', 'reboot', 'bootloader']

        run_command_with_logged_output(cmd)

    def _get_flash_command(self):
        cmd = [
            'ubuntu-device-flash',
            '--revision', self.revision,
            'touch',
            '--bootstrap',
            '--developer-mode',
            '--password', self.password,
            '--channel', self.channel,
        ]
        if self.serial is not None:
            cmd.extend(['--serial', self.serial])
        if self.recovery_file is not None:
            cmd.extend(['--recovery-image', self.recovery_file])
        return cmd

    def get_adt_run_args(self, **kwargs):
        try:
            tmp_dir = os.path.join(kwargs['tmp_dir'], 'identity')
            os.makedirs(tmp_dir)
        except KeyError:
            logger.error('Require tmp_dir is required for Touch backend.')
            raise

        adb_script = _get_adb_script_location()
        logger.info('Using adb: {}'.format(adb_script))
        cmd = [
            'ssh', '-s', adb_script,
            '--', '-p', self.password,
            '--identity', tmp_dir
        ]
        if self.serial is not None:
            cmd = cmd + ['-s', self.serial]
        logger.info('Touch adt command: {}'.format(cmd))
        return cmd

    @property
    def name(self):
        return 'touch'

    @staticmethod
    def format_device_state_string(channel, revision):
        return '{channel}:{revision}'.format(
            channel=channel,
            revision=revision
        )

    def __repr__(self):
        return '{classname}(channel={channel} revno={revno})'.format(
            classname=self.__class__.__name__,
            channel=self.channel,
            revno=self.revision
        )


def _device_connected(serial):
    serials = _get_connected_serials()

    if not any(serials):
        raise RuntimeError('No Touch devices found.')

    if serial is not None:
        # Looking for a specific device.
        return serial in serials
    else:
        if len(serials) > 1:
            raise RuntimeError(
                'Multiple devices found with no serial '
                'provided to identify target testbed.'
            )

        # There is a device connected.
        return True
    return False


def _get_adb_script_location():
    """Return path to adb script.

    We ship a customised adb script currently that adds some features we
    need. This will change in the future at some point when this is upstreamed.

    """
    adb_script = os.path.join(get_file_data_location(), 'adb')
    logger.info('Looking for adb script at: {}'.format(adb_script))
    if os.path.exists(adb_script):
        return adb_script
    return 'adb'


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
        output = subprocess.check_output(detail_cmd, universal_newlines=True)
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
        revison=image_details['version_version']
    )
