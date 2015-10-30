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
from upgrade_testing.configspec import definition_reader, test_source_retriever

import logging
import os
import subprocess
import tempfile

from argparse import ArgumentParser
from textwrap import dedent

logger = logging.getLogger(__name__)


def parse_args():
    """
    do_setup (better name) if the backend isn't setup do it.
    """
    parser = ArgumentParser('Run system tests for Upgrade Tests.')
    parser.add_argument('--config', '-c',
                        help='The config file to use for this run.')
    parser.add_argument('--provision',
                        default=False,
                        action='store_true',
                        help='Provision the requested backend')
    return parser.parse_args()


def prepare_environment(testsuite, temp_file):
    """Write testrun config details to `temp_file`.

    :param testsuite: TestSpecification instance.

    """
    pre_tests = ' '.join(testsuite.pre_upgrade_scripts)
    post_tests = ' '.join(testsuite.post_upgrade_tests)
    temp_file.write(
        dedent('''\
        # Auto Upgrade Test Configuration
        export PRE_TEST_LOCATION="/root/pre_scripts"
        export POST_TEST_LOCATION="/root/post_scripts"
        '''))
    temp_file.write('PRE_TESTS_TO_RUN="{}"\n'.format(pre_tests))
    temp_file.write('POST_TESTS_TO_RUN="{}"\n'.format(post_tests))


def execute_adt_run(testsuite, backend, run_config):
    """Prepare the adt-run to execute.

    Copy all the files into the expected place etc.

    :param testsuite: Dict containing testsuite details
    :param backend:  provisioning backend object
    :param test_file_name: filepath for . . .
    """
    with test_source_retriever(testsuite.test_source) as test_source_dir:
        adt_run_command = get_adt_run_command(
            testsuite,
            backend,
            run_config,
            test_source_dir
        )
        subprocess.check_call(adt_run_command)


def get_adt_run_command(testsuite, backend, run_config, test_source_dir):
    """Construct the adt command to run.

    :param testsuite: TestSpecification object containing test run details.

    """
    # Initial testing adt-run hardcoded stuff
    adt_cmd = ['adt-run', '-B', '--user=root', '--unbuilt-tree=.']

    # Copy across the test scripts.
    dest_dir = '/root/run_scripts/'
    copy_cmd = '--copy={src}:{dest}'.format(
        src=test_source_dir,
        dest=dest_dir
    )
    adt_cmd.append(copy_cmd)

    # Need to get some env vars across to the testbed. Namely tests to run and
    # test locations.
    adt_cmd.append(
        '--copy={}:/root/auto_upgrade_test_settings'.format(run_config))

    backend_args = backend.get_adt_run_args()

    return adt_cmd + ['---'] + backend_args


def main():
    args = parse_args()

    # if args.provision_file etc. . .
    test_def_details = definition_reader(args.config)

    # For each test definition ensure that the required backend is available,
    # if not either error or create it (depending on args.)
    for testsuite in test_def_details:
        backend = backends.get_backend(testsuite.provisioning)

        if not backend.available():
            if args.provision:
                logger.info('Creating backend for: {}'.format(backend))
                backend.create()
            else:
                logger.error('No available backend for test: {}'.format(
                    testsuite.name)
                )
                continue
        else:
            logger.info('Backend "{}" is available.'.format(backend))

        try:
            temp_file_name = tempfile.mkstemp()[1]
            with open(temp_file_name, 'w') as temp_file:
                prepare_environment(testsuite, temp_file)

            execute_adt_run(testsuite, backend, temp_file_name)
        finally:
            os.unlink(temp_file_name)


if __name__ == '__main__':
    main()
