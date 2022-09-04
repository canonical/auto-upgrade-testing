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
import shutil
import subprocess

logger = logging.getLogger(__name__)


def test_source_retriever(source_location, dest_dir):
    """Given a location path for the tests location retrieve a local copy.

    This allows us to copy across what we need to the testbed.

    :param location: string for location to retrieve the test directory
      from.
    :param dest_dir: where to move the files too. This could be a temp
      directory that gets cleaned up after a run, but that's not the
      responsibility of this method
    Currently support uri types:
      - 'file://' for local file locations
      - 'lp:' for launchpad bzr branch locations.

    :returns: string containing directory path to copy across

    """
    if source_location.startswith("file://"):
        return _local_file_retrieval(source_location, dest_dir)
    elif source_location.startswith("lp:"):
        return _bzr_file_retrieval(source_location, dest_dir)
    else:
        raise ValueError("Unknown file protocol")


def _local_file_retrieval(source, dest_dir):
    source_path = os.path.abspath(source.replace("file://", ""))
    shutil.copytree(source_path, dest_dir)
    return dest_dir


def _bzr_file_retrieval(source, dest_dir):
    bzr_cmd = ["bzr", "export", dest_dir, source]
    try:
        subprocess.check_output(bzr_cmd)
    except subprocess.CalledProcessError:
        logger.error("Failed to export path: {}".format(source))
        raise ValueError(
            "Unable to export from provided source: {}".format(source)
        )

    return dest_dir
