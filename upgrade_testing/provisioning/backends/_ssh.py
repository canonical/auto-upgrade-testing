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
import socket
import subprocess

import time

import errno
import pexpect
from retrying import retry

from upgrade_testing.provisioning.backends._base import ProviderBackend
from upgrade_testing.provisioning.executors import SSHExecutor

CACHE_DIR = '/var/cache/auto-upgrade-testing'

logger = logging.getLogger(__name__)
TIMEOUT_CMD = 60
TIMEOUT_CONNECT = 120
TIMEOUT_WAIT_FOR_DEVICE = 120


class SshBackend(ProviderBackend):

    # We can change the Backends to require just what they need. In this case
    # it would be distribution, release name (, arch)
    def __init__(self, release, arch, image_name, build_args=[],
                 username=None, password=None, device_ip=None):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.release = release
        self.arch = arch
        self.image_name = image_name
        self.build_args = build_args
        self.executor = SSHExecutor()
        self.username = username or 'ubuntu'
        self.password = password or 'ubuntu'
        self.connected = False
        self.key_file = None
        self.device_ip = device_ip or 'localhost'
        self.port = -1

    def available(self):
        """Return true if a qemu exists that matches the provided args.

        """
        image_name = self.image_name
        logger.info('Checking for {}'.format(image_name))
        return image_name in os.listdir(CACHE_DIR)

    def create(self, adt_base_path):
        raise NotImplementedError('Cannot create ssh backend directly')

    def get_adt_run_args(self, **kwargs):
        return ['ssh', '--port', str(self.port),
                '--login', self.username,
                '--password', self.password,
                '--identity', self.key_file,
                '--hostname',
                self.device_ip,
                '--reboot']

    @property
    def name(self):
        return 'ssh'

    def __repr__(self):
        return '{classname}(release={release})'.format(
            classname=self.__class__.__name__,
            release=self.release
        )

    port_from = 22220
    port_to = 23000

    def connect(self, timeout=TIMEOUT_CONNECT):
        if not self.connected:
            self.enable_ssh()
            self.executor.connect(
                self.username, self.password, self.port, self.device_ip,
                timeout)
            self.connected = True

    def close(self):
        if self.connected:
            self.executor.close()
            self.connected = False

    def reboot(self):
        self.executor.reboot()

    def shutdown(self):
        self.executor.shutdown()

    def put(self, src, dst):
        self.executor.put(src, dst)

    def run(self, command, timeout=TIMEOUT_CMD, log_stdout=True):
        return self.executor.run(command, timeout, log_stdout)

    def run_sudo(self, command, timeout=TIMEOUT_CMD, log_stdout=True):
        return self.executor.run_sudo(command, timeout, log_stdout)

    def find_free_port(self):
        for port in range(self.port_from, self.port_to):
            try:
                s = socket.create_connection(('127.0.0.1', port))
            except socket.error as e:
                if e.errno == errno.ECONNREFUSED:
                    # This means port is not currently used, so use this one
                    self.port = port
                    return
                else:
                    pass
            else:
                # port is already taken
                s.close()
        raise RuntimeError('Could not find free port for SSH connection.')

    def enable_ssh(self):
        """Enable ssh using public key."""
        self._wait_for_device()
        self._get_ssh_id_path()
        if not self._try_public_key_login():
            self._update_device_host_key()
            self._copy_ssh_id_to_device()
            self._verify_ssh_connect()

    def _wait_for_device(self, timeout=TIMEOUT_CONNECT):
        end = time.time() + timeout
        while time.time() < end:
            try:
                s = socket.create_connection(
                    (self.device_ip, str(self.port)), timeout)
            except ConnectionRefusedError:
                time.sleep(1)
            else:
                s.close()
                return
        raise TimeoutError(
            'Could not connect to {} '
            'port {}.'.format(self.device_ip, self.port))

    def _update_device_host_key(self):
        hosts_path = os.path.expanduser('~/.ssh/known_hosts')
        subprocess.call([
            'ssh-keygen', '-f', hosts_path, '-R',
            '[{}]:{}'.format(self.device_ip, self.port)])

    @retry(stop_max_attempt_number=20, wait_fixed=2000,
           retry_on_exception=lambda exception: isinstance(
               exception, RuntimeError))
    def _copy_ssh_id_to_device(self):
        pub_path = '{}.pub'.format(self.key_file)
        home_ssh = '/home/{u}/.ssh'.format(u=self.username)
        authorized_keys = os.path.join(home_ssh, 'authorized_keys')
        self._run(['mkdir', '-p', home_ssh])
        self._put(pub_path, authorized_keys)
        self._run(
            ['chown', '{u}:{u}'.format(u=self.username), '-R', home_ssh])
        self._run(['chmod', '700', home_ssh])
        self._run(['chmod', '600', authorized_keys])

    def _get_ssh_id_path(self):
        match = False
        for id in ['~/.ssh/id_rsa', '~/.ssh/id_autopkgtest']:
            path = os.path.expanduser(id)
            if os.path.exists(path):
                match = True
                break
        if not match:
            subprocess.check_call([
                'ssh-keygen', '-q', '-t', 'rsa', '-f', path, '-N', ''])
        self.key_file = path

    def _try_public_key_login(self):
        """Try and log in using public key. If this succeeds then there is no
        need to do any further ssh setup.
        :return: True if login was successful, False otherwise
        """
        cmd = ' '.join(['ssh', '-p', str(self.port),
                        '-o', 'UserKnownHostsFile=/dev/null',
                        '-o', 'StrictHostKeyChecking=no',
                        '-i', self.key_file, '-l', self.username,
                        self.device_ip])
        child = pexpect.spawn(cmd)
        try:
            index = child.expect(
                ['\$', 'password', 'denied'], timeout=TIMEOUT_CONNECT)
        except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF):
            index = -1
        finally:
            child.close()
        return index == 0

    def _verify_ssh_connect(self):
        """Verify that an ssh connection can be established without using
        password.
        """
        for count in range(20):
            if self._try_public_key_login():
                return
            else:
                time.sleep(1)
        raise RuntimeError('Could not create ssh connection')

    def _run(self, commands, timeout=TIMEOUT_CMD):
        """Run a command setting up an ssh connection using password."""
        ssh_cmd = [
            'ssh', '-o', 'StrictHostKeyChecking=no', '-p', str(self.port),
            '{}@{}'.format(self.username, self.device_ip)]
        self._run_with_password(ssh_cmd + commands, self.password, timeout)

    def _put(self, src, dst, timeout=TIMEOUT_CMD):
        """Put file onto device setting up an ssh connection using password."""
        scp_cmd = [
            'scp', '-o', 'StrictHostKeyChecking=no', '-P', str(self.port),
            src, '{}@{}:{}'.format(self.username, self.device_ip, dst)]
        self._run_with_password(scp_cmd, self.password, timeout)

    def _run_with_password(self, commands, password, timeout=TIMEOUT_CMD):
        """Run command expecting a password prompt to be displayed."""
        command = ' '.join(commands)
        child = pexpect.spawn(command)
        try:
            child.expect('password', timeout=timeout)
        except pexpect.exceptions.EOF:
            # No password prompt is displayed, so just continue
            pass
        else:
            child.sendline(password)
            if child.expect([pexpect.EOF, 'denied'], timeout=timeout):
                raise PermissionError(
                    'Check password is correct: "{}"'.format(password))
        finally:
            child.close()
        if child.exitstatus:
            raise RuntimeError('Error running {}'.format(command))
