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

logger = logging.getLogger(__name__)


def run_command_with_logged_output(command):
    """Run provided command while outputting stdout & stderr in 'real time'.

    :returns: Returncode of command that was run.

    """
    logger.debug('Running command: {}'.format(command))
    with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
    ) as proc:
        for line in proc.stdout:
            logger.info(line.strip('\n'))
        proc.wait()
        return proc.returncode
