#
# Ubuntu Upgrade Testing
# Copyright (C) 2017 Canonical
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


import os
import sys
import time
from abc import ABCMeta, abstractmethod

import paramiko

TIMEOUT_CMD = 60
TIMEOUT_CONNECT = 120
TIMEOUT_WAIT_FOR_DEVICE = 120


class Result:
    """Result of command with status and output properties."""

    def __init__(self):
        self.status = None
        self.output = ""


class SSHClient:
    """This class manages the paramiko ssh client"""

    def __init__(self):
        """The ssh can be initialized either through a password or with a
        private key file and the passphrase
        :param hostname: The hostname to connect
        :param user: The remote user in the host
        :param keyfile: The private key used to connect to the remote host
        :param password: The password used to connect to the remote host
        :param timeout: An optional timeout (in seconds) for the TCP connect
        """
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, hostname, user, password, port, timeout=60):
        """Connect to remote host."""
        timeout = float(timeout)
        self.client.connect(
            hostname,
            username=user,
            password=password,
            port=port,
            timeout=timeout,
            banner_timeout=timeout,
        )

    def close(self):
        """Close the connection"""
        self.client.close()

    def run(self, cmd, timeout=TIMEOUT_CMD, log_stdout=True):
        """Run a command in the remote host.
        :param cmd: Command to run.
        :param timeout: Period to wait before raising TimeoutError.
        :param log_stdout: Whether to log output to stdout.
        :return: Result object containing command output and status code.
        """
        channel = self.client.get_transport().open_session()
        channel.set_combine_stderr(True)
        end = time.time() + timeout
        result = Result()
        channel.exec_command(cmd)
        while not channel.exit_status_ready() or (
            channel.exit_status_ready() and channel.recv_ready()
        ):
            if channel.recv_ready():
                self._process_output(
                    result, log_stdout, channel.recv(1024).decode()
                )
            elif time.time() > end:
                print(
                    "Timeout waiting {} seconds for command to "
                    "complete: {}".format(timeout, cmd)
                )
                raise TimeoutError
            time.sleep(0.2)
        # Add a new line after command has completed to ensure output
        # is separated.
        self._process_output(result, log_stdout, "\n")
        result.status = channel.recv_exit_status()
        return result

    def _process_output(self, result, log_stdout, content):
        """Save output to result and print to stdout if required."""
        result.output += content
        if log_stdout:
            sys.stdout.write(content)
            sys.stdout.flush()

    def put(self, local_path, remote_path):
        """Copy a file through sftp from the local_path to the remote_path"""
        if not os.path.isfile(local_path):
            raise RuntimeError("File to copy does not exist")

        with self.client.open_sftp() as sftp:
            sftp.put(local_path, remote_path)

    def get(self, remote_path, local_path):
        """Copy a file through sftp from the remote_path to the local_path"""
        with self.client.open_sftp() as sftp:
            sftp.get(remote_path, local_path)

        if not os.path.isfile(local_path):
            raise RuntimeError("File couldn't be copied")


class Executor:
    __metaclass__ = ABCMeta
    """Base class for all target executors."""

    @abstractmethod
    def connect(self, username, password, port, host=None, timeout=None):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def run(self, cmd, timeout=None, log_stdout=True):
        pass

    @abstractmethod
    def run_sudo(self, cmd, timeout=None, log_stdout=True):
        pass

    def reboot(self):
        result = self.run_sudo("shutdown -r now")
        if result.status > 0:
            raise PermissionError("Reboot failed, check password.")

    def shutdown(self):
        result = self.run_sudo("shutdown now")
        if result.status > 0:
            raise PermissionError("Shutdown failed, check password.")

    @abstractmethod
    def wait_for_device(self, timeout=None):
        pass

    @abstractmethod
    def put(self, localpath, remotepath):
        pass

    @abstractmethod
    def get(self, remotepath, localpath):
        pass

    def _get_sudo_command(self, cmd):
        command = "sudo {}".format(cmd)
        if self.password:
            command = "echo {} | sudo -S {}".format(self.password, cmd)
        return command


class SSHExecutor(Executor):
    def __init__(self):
        self.ssh_client = SSHClient()

    def connect(
        self,
        username,
        password,
        port,
        host="localhost",
        timeout=TIMEOUT_CONNECT,
    ):
        self.password = password
        count = max(1, timeout)
        for attempt in range(count):
            try:
                self.ssh_client.connect(
                    host, username, password, port, timeout
                )
            except TypeError:
                # This can happen when target not yet running so just try again
                time.sleep(1)
            except paramiko.ssh_exception.AuthenticationException:
                raise
            else:
                return
        raise RuntimeError("Could not connect to target.")

    def close(self):
        self.ssh_client.close()

    def _run(self, cmd, timeout=TIMEOUT_CMD, log_stdout=True):
        return self.ssh_client.run(cmd, timeout, log_stdout)

    def run(self, cmd, timeout=TIMEOUT_CMD, log_stdout=True):
        return self._run(cmd, timeout, log_stdout)

    def run_sudo(self, cmd, timeout=TIMEOUT_CMD, log_stdout=True):
        return self._run(self._get_sudo_command(cmd), timeout, log_stdout)

    def put(self, localpath, remotepath):
        self.ssh_client.put(localpath, remotepath)

    def get(self, remotepath, localpath):
        self.ssh_client.get(remotepath, localpath)
