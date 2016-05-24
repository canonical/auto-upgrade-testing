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
import tempfile

from collections import namedtuple
from contextlib import contextmanager
from distutils.spawn import find_executable
from textwrap import dedent

from upgrade_testing.configspec import test_source_retriever
from upgrade_testing.preparation._testbed import get_testbed_storage_location
from upgrade_testing.provisioning import run_command_with_logged_output
from upgrade_testing.configspec import get_file_data_location

DEFAULT_GIT_URL = 'git://anonscm.debian.org/autopkgtest/autopkgtest.git'

logger = logging.getLogger(__name__)


# Definition for the tempfiles that are created for a run and cleaned up
# afterwards.
TestrunTempFiles = namedtuple(
    'TestrunTempFiles', [
        'adt_base_path',
        'adt_cmd',
        'run_config_file',
        'testrun_tmp_dir',
        'unbuilt_dir',
        'pre_scripts',
        'post_scripts',
    ]
)


@contextmanager
def prepare_test_environment(testsuite):
    """Return a TestrunTempFiles instance that is cleaned up once out of scope.

    Creates a temp directory an populates it with the required data structure
    to copy across to the testbed.
    Namely:
      - Test run config details
      - 'Dummy' debian/autopkgtest details for this run.

    :param testsuite: TestSpecification instance.

    """

    try:
        temp_dir = tempfile.mkdtemp()
        run_config_path = _write_run_config(testsuite, temp_dir)
        unbuilt_dir = _create_autopkg_details(temp_dir)
        logger.info('Unbuilt dir: {}'.format(unbuilt_dir))

        pre_path = os.path.join(temp_dir, 'pre_scripts')
        _copy_script_files(testsuite.pre_upgrade_scripts.location, pre_path)

        post_path = os.path.join(temp_dir, 'post_scripts')
        _copy_script_files(testsuite.post_upgrade_tests.location, post_path)

        adt_base_path, adt_cmd=_get_adt_path(temp_dir)

        yield TestrunTempFiles(
            adt_base_path=adt_base_path,
            adt_cmd=adt_cmd,
            run_config_file=run_config_path,
            # Should we create a dir so that it won't interfer?
            unbuilt_dir=temp_dir,
            testrun_tmp_dir=temp_dir,
            pre_scripts=pre_path,
            post_scripts=post_path,
        )
    finally:
        _cleanup_dir(temp_dir)


def _copy_script_files(script_location, script_destination):
    return test_source_retriever(script_location, script_destination)


def _cleanup_dir(dir):
    shutil.rmtree(dir)


def _write_run_config(testsuite, temp_dir):
    """Write a config file for this run of testing.

    Populates a config file with the details from the test config spec as well
    as the dynamic details produced each run (temp dir etc.).

    """
    run_config_file = tempfile.mkstemp(dir=temp_dir)[1]
    with open(run_config_file, 'w') as f:
        config_string = dedent('''\
            # Auto Upgrade Test Configuration
            PRE_TEST_LOCATION="{testbed_location}/pre_scripts"
            POST_TEST_LOCATION="{testbed_location}/post_scripts"
        '''.format(testbed_location=get_testbed_storage_location()))
        f.write(config_string)
        pre_tests = ' '.join(testsuite.pre_upgrade_scripts.executables)
        post_tests = ' '.join(testsuite.post_upgrade_tests.executables)
        f.write('PRE_TESTS_TO_RUN="{}"\n'.format(pre_tests))
        f.write('POST_TESTS_TO_RUN="{}"\n'.format(post_tests))
        # Need to store the expected pristine system and the post-upgrade
        # system
        # Note: This will only support one upgrade, for first -> final
        f.write(
            'INITIAL_SYSTEM_STATE="{}"\n'.format(
                testsuite.provisioning.initial_state
            )
        )
        f.write(
            'POST_SYSTEM_STATE="{}"\n'.format(
                testsuite.provisioning.final_state
            )
        )
        f.write(
            'RUNNING_BACKEND={}\n'.format(testsuite.provisioning.backend_name)
        )
    return run_config_file


def _create_autopkg_details(temp_dir):
    """Create a 'dummy' debian dir structure for autopkg testing.

    Given a temp dir build the required dir tree and populate it with the
    needed files.

    The test file that is executed is already populated and part of this
    project.

    """
    dir_tree = os.path.join(temp_dir, 'debian')
    test_dir_tree = os.path.join(dir_tree, 'tests')
    os.makedirs(test_dir_tree)

    source_dir = get_file_data_location()

    def _copy_file(dest, name):
        """Copy a file from the source data dir to dest."""
        src = os.path.join(source_dir, name)
        dst = os.path.join(dest, name)
        shutil.copyfile(src, dst)

    _copy_file(test_dir_tree, 'control')
    _copy_file(test_dir_tree, 'upgrade')
    _copy_file(dir_tree, 'changelog')

    # Main control file can be empty
    dummy_control = os.path.join(dir_tree, 'control')
    open(dummy_control, 'a').close()

    return dir_tree


def _get_adt_path(tmp_dir):
    # Check if we need to get a git version of autopkgtest
    # (If environment variables are set or a local version can't be found)
    git_url = os.environ.get('AUTOPKGTEST_GIT_REPO', None)
    git_hash = os.environ.get('AUTOPKGTEST_GIT_HASH', None)
    local_adt = _get_local_adt()
    if git_url or git_hash or local_adt is None:
        git_url = git_url or DEFAULT_GIT_URL
        logger.info('Fetching autopkgtest from git url: %s', git_url)
        git_trunk_path = os.path.join(tmp_dir, 'local_autopkgtest')
        git_command = ['git', 'clone', git_url, git_trunk_path]
        retval = run_command_with_logged_output(git_command)
        if retval != 0:
            raise ChildProcessError('{} exited with status {}'.format(
                git_command, retval))
        if git_hash:
            logger.info('Checking out specific git hash: %s', git_hash)
            git_hash_command = ['git',
                           '--git-dir', os.path.join(git_trunk_path, '.git'),
                           '--work-tree', git_trunk_path,
                           'checkout', git_hash]
            run_command_with_logged_output(git_hash_command)
        adt_path = os.path.join(git_trunk_path, 'tools')
        adt_cmd = os.path.join(git_trunk_path, 'run-from-checkout')
    else:
        logger.info('Using installed autopkgtest:')
        run_command_with_logged_output(['dpkg-query', '-W', 'autopkgtest'])
        adt_path, adt_cmd = local_adt
        adt_cmd = os.path.join(adt_path, adt_cmd)
    return (adt_path, adt_cmd)

def _get_local_adt():
    path = find_executable('adt-run')
    if path:
        return path.rsplit('/', 1)
    return None
