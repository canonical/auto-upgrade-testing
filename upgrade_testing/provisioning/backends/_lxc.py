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

from upgrade_testing.provisioning.backends._base import ProviderBackend

class LXCBackend(ProviderBackend):

    @classmethod
    def available(cls, **args):
        """Return true if an lxc container exists based on requirements in
        args.

        """
        release, _, _ = get_required_details(args)
        container_name = 'adt-{release}'.format(release)
        return container_name in lxc.list_containers()

    @classmethod
    def create(cls, *args):
        """Create an lxc container from provided args.

        Required args:
          - release (i.e. Trusty, Precise)

        Optional args:
          - architecture (e.g. i386, amd64) defaults to native architecture.
          - distribution (either ubuntu or debian) defaults to ubuntu.

        :raises ValueError: If no release is provided.

        """

        release, arch, dist = get_required_details(args)

        cmd = ['adt-build-lxc', release, dist, arch]
        subprocess.check_output(cmd)

    @classmethod
    def get_adt_run_args(cls, **args):
        # This doesn't currently care about distribution or arch.
        release, arch, dist = get_required_details(args)
        return return ['lxc', '-s', 'adt-{release}'.format(release)]

def get_required_details(args):
    """Returns triplet tuple containing sanitised args: release, arch,
    distribution

    :raises ValueError: if no release is provided

    """
    try:
        release = args['release']
    except KeyError:
        raise ValueError('No release provided.')

    arch = args.get('architecture', None)
    distribution = args.get('distribution', None)

    return (release, arch, distribution)
