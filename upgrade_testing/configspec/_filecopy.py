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

from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp

logger = logging.getLogger(__name__)


@contextmanager
def test_source_retriever(source_location):
    """Given a location path for the tests location retrieve a local copy.

    This allows us to copy across what we need to the testbed.

    :param location: string for location to retrieve the test directory
      from.
    Currently support uri types:
      - 'file://' for local file locations
      - 'lp:' for launchpad bzr branch locations.

    :returns: string containing directory path to copy across

    """
    needs_cleanup = False

    try:
        if source_location.startswith('file://'):
            local_location = _local_file_retrieval(source_location)
        elif source_location.startswith('lp:'):
            local_location = _bzr_file_retrieval(source_location)
            needs_cleanup = True
        else:
            raise
 ValueError('Unknown file protocol')
        yield local_location
    finally:
        if needs_cleanup:
            _cleanup_dir(local_location)


def _local_file_retrieval(source):
    return os.path.abspath(source.replace('file://', ''))


def _bzr_file_retrieval(source):
    tmp_dir = mkdtemp()
    bzr_cmd = ['bzr', 'export', tmp_dir, source]
    try:
        subprocess.check_output(bzr_cmd)
    except subprocess.CalledProcessError:
        logger.error('Failed to export path: {}'.format(source))
        raise ValueError(
            'Unable to export from provided source: {}'.format(source)
        )

    return tmp_dir


def _cleanup_dir(path):
    rmtree(path)
