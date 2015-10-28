#!/usr/bin/env python3
#
# Ubuntu System Tests
# Copyright (C) 2014, 2015 Canonical
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

from upgrade_testing.provisioning import backends

import logging
import lxc
import os
import subprocess
import tempfile
import yaml

from argparse import ArgumentParser


def parse_args():
    """
    do_setup (better name) if the backend isn't setup do it.
    """
    parser = ArgumentParser('Run system tests for Upgrade Tests.')
    parser.add_argument('--config', '-c',
                        help='The config file to use for this run.')
    return parser.parse_args()


def get_test_def_file(file_path):
    """Return datastructure of test definition.

    Reads a yaml file and produces a datastructure of some sort.
    """
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        err_msg = 'Unable to open config file: {}'.format(file_path)
        logger.error(err_msg)
        e.args += (err_msg, )
        raise


# def ensure_backends_available(config_details, configure_missing):
#     """Ensure the required backends are available and setup as expected.

#     Parse the config details to see which backends are required, for those
#     backends make sure:
#       - They are available
#       - The required arch/release is setup/available

#     If there is a requirement not met raise exception. Unless we hve configure
#     missing? Is there a nicer way to do this?
#     """
#     # We expect the details to come through in a defined way, perhaps we should
#     # create a list of objects (Named Tuples for instance) to ease a bunch of
#     # the checking needed here.
#     # Config details should be a list.

#     # iterate through and find any reference to backend
#     issues = []
#     backends = dict()
#     for test_def in config_details:
#         error_if_backend_unavailable(test_def)


def error_if_backend_unavailable(test_def):
    """Raise ValueError if backend is unavailable in this environment."""
    # Meh, all true for now.
    backend = test_def['backend']
    release = test_def['test-details']['start-release']
    if backend == 'lxc':
        container_name = 'adt-{}'.format(release)
        if container_name not in lxc.list_containers():
            cmd = ['adt-build-lxc', 'ubuntu', release]
            subprocess.check_output(cmd)
        return container_name
    raise ValueError('%s backend not supported' % backend)


def prepare_environment(testsuite, temp_file):
    temp_file.write('''# Auto Upgrade Test Configuration
export PRE_TEST_LOCATION="/root/pre_scripts"
export POST_TEST_LOCATION="/root/post_scripts"
''')
    temp_file.write('PRE_TESTS_TO_RUN="{}"\n'.format(
        ','.join(testsuite['test-details']['pre_upgrade_tests'])))
    temp_file.write('POST_TESTS_TO_RUN="{}"\n'.format(
        ','.join(testsuite['test-details']['post_upgrade_tests'])))


def execute_adt_run(testsuite, backend, temp_file_name):
    """Prepare the adt-run to execute.

    Copy all the files into the expected place etc.

    :param testsuite: Dict containing testsuite details
    :param backend:  provisioning backend object
    :param test_file_name: filepath for . . .
    """
    # Huh, do we need to sep. backend out here?
    # Ah yes, there are the test details, that's what should be passed in to
    # execute_adt_run.
    adt_run_command = get_adt_run_command(testsuite, backend, temp_file_name)
    subprocess.check_call(adt_run_command)


def get_adt_run_command(testsuite, backend, temp_file_name):
    # Initial testing adt-run hardcoded stuff
    adt_cmd = ['adt-run', '-B', '--user=root', '--unbuilt-tree=.']

    # adt-run command needs to copy across the the test scripts.
    # the script stuff needs to be de-deuped. No need to copy the same things
    # many times
    for script in testsuite['test-details']['pre_upgrade_tests']:
        src_script = '{script}'.format(script=script)
        dest_script = '/root/pre_scripts/{}'.format(script)
        copy_cmd = '--copy={src}:{dest}'.format(
            src=src_script, dest=dest_script)
        adt_cmd.append(copy_cmd)

    for script in testsuite['test-details']['post_upgrade_tests']:
        src_script = '{script}'.format(script=script)
        dest_script = '/root/post_scripts/{}'.format(script)
        copy_cmd = '--copy={src}:{dest}'.format(
            src=src_script, dest=dest_script)
        adt_cmd.append(copy_cmd)

    # Need to get some env vars across to the testbed. Namely tests to run and
    # test locations.
    # Write temp file with env details in it and source it at the other end.
    adt_cmd.append(
        '--copy={}:/root/auto_upgrade_test_settings'.format(temp_file_name))

    backend_args = backend.get_adt_run_args()

    return adt_cmd + ['---'] + backend_args

def main():
    args = parse_args()

    test_def_details = get_test_def_file(args.config)

    # ensure_backends_available(test_def_details, args.do_setup)


    # For each test definition ensure that the required backend is available,
    # if not either error or create it (depending on args.)

    for testsuite in test_def_details:
        # this could be tidier
        backend = backends.get_backend(testsuite['backend'])(
            testsuite['test-details']
        )

        if not backend.available():
            if args.do_setup:
                backend.create()
            else:
                logger.error('No available backend for test. . .')
                continue

        temp_file_name = tempfile.mkstemp()[1]
        with open(temp_file_name, 'w') as temp_file:
            prepare_environment(testsuite, temp_file)
        execute_adt_run(testsuite, temp_file_name)
        os.unlink(temp_file_name)


if __name__ == '__main__':
    main()
