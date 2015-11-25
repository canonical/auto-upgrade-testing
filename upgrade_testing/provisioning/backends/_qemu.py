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

from upgrade_testing.provisioning.backends._base import ProviderBackend

CACHE_DIR='/var/cache/auto-upgrade-testing'

logger = logging.getLogger(__name__)


class QemuBackend(ProviderBackend):

    # We can change the Backends to require just what they need. In this case
    # it would be distribution, release name (, arch)
    def __init__(self, release, arch, image_name, build_args=[]):
        """Provide backend capabilities as requested in the provision spec.

        :param provision_spec: ProvisionSpecification object containing backend
          details.

        """
        self.release = release
        self.arch = arch
        self.image_name = image_name
        self.build_args = build_args

    def available(self):
        """Return true if a qemu exists that matches the provided args.

        """
        image_name = self.image_name
        logger.info('Checking for {}'.format(image_name))
        return image_name in os.listdir(CACHE_DIR)

    def create(self):
        """Create a qemu image."""

        logger.info('Creating qemu image for run.')
        cmd = 'adt-buildvm-ubuntu-cloud -a {} -r {} -o {} {}'.format(
            self.arch, self.release, CACHE_DIR, ' '.join(self.build_args),
        )
        # TODO: Provide further checking here.
        with subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE,
                bufsize=1, universal_newlines=True
        ) as p:
            for line in p.stdout:
                logger.info(line.strip('\n'))
        initial_image_name = 'adt-{}-{}-cloud.img'.format(self.release,
                                                          self.arch)
        initial_image_path = os.path.join(CACHE_DIR, initial_image_name)
        final_image_path = os.path.join(CACHE_DIR, self.image_name)
        os.rename(initial_image_path, final_image_path)
        logger.info('Image created.')

    def get_adt_run_args(self, **kwargs):
        return ['qemu', os.path.join(CACHE_DIR, self.image_name)]

    def __repr__(self):
        return '{classname}(release={release})'.format(
            classname=self.__class__.__name__,
            release=self.release
        )
