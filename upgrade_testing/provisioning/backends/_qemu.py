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
import shlex
import shutil
import signal
import subprocess
import tempfile
import threading

from paramiko.ssh_exception import SSHException

from upgrade_testing.provisioning._util import run_command_with_logged_output
from upgrade_testing.provisioning.backends._ssh import SshBackend

CACHE_DIR = '/var/cache/auto-upgrade-testing'
OVERLAY_DIR = os.path.join(CACHE_DIR, 'overlay')
QEMU_LAUNCH_OPTS = (
    '{qemu} -m {ram} -smp {cpu} -pidfile {workdir}/qemu.pid -localtime '
    '-cpu core2duo -enable-kvm '
)
QEMU_SYSTEM_AMD64 = 'qemu-system-x86_64'
QEMU_SYSTEM_I386 = 'qemu-system-i386'
ARCH_AMD64 = 'amd64'
ARCH_I386 = 'i386'
QEMU_DISPLAY_OPTS = (
    '-display sdl '
)
QEMU_DISPLAY_VGA_OPTS = (
    '-vga qxl '
)
QEMU_SOUND_OPTS = (
    '-soundhw all '
)
QEMU_DISPLAY_HEADLESS = (
    '-display none '
)
QEMU_NET_OPTS = (
    '-net nic,model=virtio -net user'
)
QEMU_PORT_OPTS = (
    ',hostfwd=tcp::{port}-:22 '
)
QEMU_DISK_IMAGE_OPTS = (
    '-drive file={disk_img},if=virtio '
)
QEMU_DISK_IMAGE_OVERLAY_OPTS = (
    '-drive file={overlay_img},cache=unsafe,if=virtio,index=0 '
)
DEFAULT_RAM = '2048'
DEFAULT_CPU = '2'
TIMEOUT_REBOOT = '300'
HEADLESS = True

logger = logging.getLogger(__name__)


class QemuBackend(SshBackend):

    # We can change the Backends to require just what they need. In this case
    # it would be distribution, release name (, arch)
    def __init__(self, release, arch, image_name, build_args=[]):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        super().__init__(release, arch, image_name, build_args)
        self.release = release
        self.arch = arch
        self.image_name = image_name
        self.build_args = build_args
        self.working_dir = None
        self.qemu_runner = None
        self.find_free_port()

    def available(self):
        """Return true if a qemu exists that matches the provided args.

        """
        image_name = self.image_name
        logger.info('Checking for {}'.format(image_name))
        return image_name in os.listdir(CACHE_DIR)

    def create(self, adt_base_path):
        """Create a qemu image."""

        logger.info('Creating qemu image for run.')
        cmd = '{builder_cmd} -a {arch} -r {release} -o {output} {args}'.format(
            builder_cmd=os.path.join(
                adt_base_path, 'autopkgtest-buildvm-ubuntu-cloud'
            ),
            arch=self.arch,
            release=self.release,
            output=CACHE_DIR,
            args=' '.join(self.build_args),
        )
        run_command_with_logged_output(cmd, shell=True)

        initial_image_name = 'autopkgtest-{}-{}.img'.format(self.release,
                                                          self.arch)
        initial_image_path = os.path.join(CACHE_DIR, initial_image_name)
        final_image_path = os.path.join(CACHE_DIR, self.image_name)
        os.rename(initial_image_path, final_image_path)
        logger.info('Image created.')

    def close(self):
        if self.qemu_runner:
            try:
                self.shutdown()
            except PermissionError:
                print('Shutdown sudo command failed. '
                      'Check password: "{}".'.format(self.password))
                self.stop_qemu()
            except SSHException:
                self.stop_qemu()
            finally:
                self.qemu_runner.join(timeout=5)
            shutil.rmtree(self.working_dir)
            self.working_dir = None
            self.qemu_runner = None
            super().close()

    def reboot(self):
        self.close()
        self.connect()

    def stop_qemu(self):
        pid_file = os.path.join(self.working_dir, 'qemu.pid')
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)

    def get_adt_run_args(self, keep_overlay=False, **kwargs):
        if keep_overlay:
            self.qemu_runner = self.launch_qemu(
                self.image_name,
                kwargs.get('ram', DEFAULT_RAM),
                kwargs.get('cpu', DEFAULT_CPU),
                kwargs.get('headless', HEADLESS),
                port=self.port,
                overlay=os.path.join(OVERLAY_DIR,
                                     self.image_name))
            super().connect()
            return super().get_adt_run_args()
        return ['qemu', '-c', DEFAULT_CPU, '--ram-size', DEFAULT_RAM,
                '--timeout-reboot', TIMEOUT_REBOOT,
                os.path.join(CACHE_DIR, self.image_name)]

    def create_overlay_image(self, overlay_img):
        """Create an overlay image for specified base image."""
        overlay_dir = os.path.dirname(overlay_img)
        if os.path.isfile(overlay_img):
            os.remove(overlay_img)
        elif not os.path.isdir(overlay_dir):
            os.makedirs(overlay_dir)
        subprocess.check_call(
            ['qemu-img', 'create', '-f', 'qcow2', '-b',
             os.path.join(CACHE_DIR, self.image_name),
             overlay_img])
        subprocess.check_call(['sudo', 'chmod', '777', overlay_img])

    @property
    def name(self):
        return 'qemu'

    def __repr__(self):
        return '{classname}(release={release})'.format(
            classname=self.__class__.__name__,
            release=self.release
        )

    @staticmethod
    def get_architecture():
        """Return architecture string for system."""
        return subprocess.check_output(
            ['dpkg', '--print-architecture']).decode().strip()

    def get_qemu_path(self):
        """Return path of qemu-system executable for system."""
        if self.get_architecture() == ARCH_AMD64:
            target = QEMU_SYSTEM_AMD64
        else:
            target = QEMU_SYSTEM_I386
        return subprocess.check_output(['which', target]).decode().strip()

    def get_disk_args(self, overlay):
        """Return qemu-system disk args. If overlay is specified then an overlay
        image at that path will be created and specified in returned arguments.
        If no overlay is none then the base image will be returned in
        the arguments.
        :param overlay: Path of overlay image to use, otherwise None
        if not needed.
        :return: Disk image arguments as string.
        """
        if overlay:
            self.create_overlay_image(overlay)
            return QEMU_DISK_IMAGE_OVERLAY_OPTS.format(overlay_img=overlay)
        else:
            return QEMU_DISK_IMAGE_OPTS.format(disk_img=self.image_name)

    @staticmethod
    def get_display_args(headless):
        """Return qemu-system display arguments based on headless parameter.
        :param headless: Whether qemu-system should run in headless mode or not.
        :return: Display parameters for required display state.
        """
        if headless:
            return QEMU_DISPLAY_HEADLESS + QEMU_DISPLAY_VGA_OPTS
        else:
            return QEMU_DISPLAY_OPTS + QEMU_DISPLAY_VGA_OPTS + QEMU_SOUND_OPTS

    def launch_qemu(self, img, ram, cpu, headless, port, overlay):
        """Boot the qemu from a different thread to stop this thread from being
        blocked whilst the qemu is running.
        """
        self.working_dir = tempfile.mkdtemp()
        runner = threading.Thread(
            target=self._launch_qemu,
            args=(self.working_dir, img, ram, cpu, headless, port, overlay))
        runner.start()
        return runner

    def _launch_qemu(self, working_dir, disk_image_path, ram, cpu, headless,
                     port=None, overlay=None):
        """Launch qemu-system to install the iso file into the disk image.
        :param working_dir: Working directory to use.
        :param disk_image_path: Path of the disk image file used for
        installation.
        :param ram: Amount of ram allocated to qemu.
        :param cpu: Number of cpus allocated to qemu.
        :param headless: Whether to run installer in headless mode or not.
        :param port: Host port number to enable port forwarding to qemu port 22.

        """
        cmd = self.get_qemu_launch_command(
            working_dir, disk_image_path, ram, cpu, headless,
            port, overlay)
        print(' '.join(cmd))
        subprocess.check_call(cmd)

    def get_qemu_launch_command(self, work_dir, disk_img, ram, cpu,
                                headless, port=None, overlay=None):
        """Return command to launch qemu process using optional install parameters.
        :param work_dir: Working directory to use.
        :param disk_img: Path of the disk image file used for installation.
        :param ram: Amount of ram allocated to qemu.
        :param cpu: Number of cpus allocated to qemu.
        :param headless: Whether to run installer in headless mode or not.
        :return: Qemu launch command string.
        :param port: Host port number to enable port forwarding to qemu port 22.
        :param overlay: path to the overlay image to be created
        """
        # Create command base with resource parameters
        cmd = QEMU_LAUNCH_OPTS.format(
            qemu=self.get_qemu_path(), ram=ram, cpu=cpu, disk_img=disk_img,
            workdir=work_dir)
        # Get disk args including overlay image if specified
        cmd += self.get_disk_args(overlay)
        # Add display parameters
        cmd += self.get_display_args(headless)
        # Add network. This must preceed the port forwarding option.
        cmd += QEMU_NET_OPTS
        # Add port forwarding if specified
        if port:
            cmd += QEMU_PORT_OPTS.format(port=port)
        else:
            # Add space to separate options
            cmd += ' '
        return shlex.split(cmd)
