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

import lxc
import subprocess

from upgrade_testing.provisioning.backends._base import ProviderBackend


class LXCBackend(ProviderBackend):

    def __init__(self, **args):
        """
        Required args:
          - release (i.e. Trusty, Precise)

        Optional args:
          - architecture (e.g. i386, amd64) defaults to native architecture.
          - distribution (either ubuntu or debian) defaults to ubuntu.

        :raises ValueError: If no release is provided.

        """
        # Currently args won't be this clean, I don't want to have to know the
        # setup above this call so we will make an intermediately dict/class
        # that takes care of this stuff.
        try:
            self.release = args['start-release']
        except KeyError:
            raise ValueError('No release provided.')

        self.arch = args.get('architecture', None)
        self.distribution = args.get('distribution', 'ubuntu')

    def available(self):
        """Return true if an lxc container exists that matches the provided
        args.

        """
        container_name = 'adt-{}'.format(self.release)
        return container_name in lxc.list_containers()

    def create(self):
        """Create an lxc container."""

        # Currently ignores dist and arch
        # cmd = ['adt-build-lxc', self.release, self.dist, self.arch]
        cmd = ['adt-build-lxc', self.distribution, self.release]
        # Provide further checking here.
        subprocess.check_output(cmd)

    def get_adt_run_args(self):
        # This doesn't currently care about distribution or arch.
        return ['lxc', '-s', 'adt-{}'.format(self.release)]
