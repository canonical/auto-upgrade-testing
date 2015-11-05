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

import datetime
import logging
import os
import pkg_resources
import shutil
import sys
import subprocess
import tempfile
import yaml

from argparse import ArgumentParser
from collections import namedtuple
from contextlib import contextmanager
from textwrap import dedent

logger = logging.getLogger(__name__)


def setup_logging():
    """Ensure logging is doing something sensible."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)
    root.addHandler(ch)


def parse_args():
    """
    do_setup (better name) if the backend isn't setup do it.
    """
    parser = ArgumentParser('Run system tests for Upgrade Tests.')
    parser.add_argument(
        '--config', '-c',
        help='The config file to use for this run.')
    parser.add_argument(
        '--provision',
        default=False,
        action='store_true',
        help='Provision the requested backend')
    parser.add_argument(
        '--results-dir',
        help='Directory to store results generated during the run.')
    return parser.parse_args()


TestrunTempFiles = namedtuple(
    'TestrunTempFiles', ['run_config_file', 'testrun_tmp_dir', 'unbuilt_dir']
)


@contextmanager
def prepare_test_environment(testsuite):
    """Return a TestrunTempFiles instance that is cleaned up out of scope.

    :param testsuite: TestSpecification instance.

    """

    try:
        temp_dir = tempfile.mkdtemp()
        run_config_path = _write_run_config(testsuite, temp_dir)
        unbuilt_dir = _create_autopkg_details(temp_dir)
        logger.info('Unbuilt dir: {}'.format(unbuilt_dir))
        yield TestrunTempFiles(
            run_config_file=run_config_path,
            # Should we create a dir so that it won't interfer?
            unbuilt_dir=temp_dir,
            testrun_tmp_dir=temp_dir,
        )
    finally:
        _cleanup_dir(temp_dir)


def _cleanup_dir(dir):
    from shutil import rmtree
    rmtree(dir)


def _write_run_config(testsuite, temp_dir):
    run_config_file = tempfile.mkstemp(dir=temp_dir)[1]
    with open(run_config_file, 'w') as f:
        pre_tests = ' '.join(testsuite.pre_upgrade_scripts)
        post_tests = ' '.join(testsuite.post_upgrade_tests)
        f.write(
            dedent('''\
            # Auto Upgrade Test Configuration
            export PRE_TEST_LOCATION="/root/pre_scripts"
            export POST_TEST_LOCATION="/root/post_scripts"
            '''))
        f.write('PRE_TESTS_TO_RUN="{}"\n'.format(pre_tests))
        f.write('POST_TESTS_TO_RUN="{}"\n'.format(post_tests))
        # Need to store the expected pristine system and the post-upgrade
        # system Currently this will only support one upgrade, for first ->
        # final
        f.write(
            'INITIAL_SYSTEM_STATE="{}"\n'.format(
                testsuite.provisioning.initial_release
            )
        )
        f.write(
            'POST_SYSTEM_STATE="{}"\n'.format(
                testsuite.provisioning.final_release
            )
        )
    return run_config_file


def get_output_dir(args):
    # This will be updated to take in the directory in which to create it in
    # and will be renamed create_... as all it will do is create the ts dir.
    """Return directory path that the results should be put into.

    If no directory is provided in the commandline args then create a temp
    dir. It is the responsibility of the script runner to clean up this temp
    dir.

    Within this base dir a timestamped directory will be created in which the
    output will reside.

    """
    if args.results_dir is not None:
        base_dir = args.results_dir
    else:
        base_dir = tempfile.mkdtemp(prefix='upgrade-tests')
        logger.info('Creating folder for results.')

    ts_dir = datetime.datetime.now().strftime('%Y%m%d.%H%M%S')
    full_path = os.path.join(os.path.abspath(base_dir), ts_dir)

    logger.info('Creating results dir: {}'.format(full_path))
    os.makedirs(full_path, exist_ok=True)

    return full_path


def display_results(artifacts_directory):
    # Read in yaml results file and output results.
    results_yaml = os.path.join(artifacts_directory, 'runner_results.yaml')
    with open(results_yaml, 'r') as f:
        results = yaml.safe_load(f)

    # this can be html/xml/whatver
    output = []
    output.append('Pre script results:')
    for test, result in results['pre_script_output'].items():
        output.append('\t{test}: {result}'.format(test=test, result=result))

    output.append('Post upgrade test results:')
    for test, result in results['post_test_output'].items():
        output.append('\t{test}: {result}'.format(test=test, result=result))
    print('\n'.join(output))


def execute_adt_run(testsuite, backend, testrun_files, output_dir):
    """Prepare the adt-run to execute.

    Copy all the files into the expected place etc.

    :param testsuite: Dict containing testsuite details
    :param backend:  provisioning backend object
    :param test_file_name: filepath for . . .
    """
    # we can change 'test_source_retriever' so that it uses the testurn_files
    # and doesn't need to worry about cleanup.
    with test_source_retriever(testsuite.test_source) as test_source_dir:
        adt_run_command = get_adt_run_command(
            backend,
            testrun_files,
            test_source_dir,
            output_dir,
        )
        subprocess.check_call(adt_run_command)


def _create_autopkg_details(temp_dir):
    # Given a temp dir build the required dir tree and populate it with the
    # needed files.
    dir_tree = os.path.join(temp_dir, 'debian')
    test_dir_tree = os.path.join(dir_tree, 'tests')
    os.makedirs(test_dir_tree)

    import upgrade_testing
    # And copy the data files there.
    source_dir = pkg_resources.resource_filename(
        upgrade_testing.__name__, 'data'
    )

    def _copy_file(dest, name):
        """Copy a file from the source data dir to dest."""
        src = os.path.join(source_dir, name)
        dst = os.path.join(dest, name)
        shutil.copyfile(src, dst)

    _copy_file(test_dir_tree, 'control')
    _copy_file(test_dir_tree, 'upgrade')
    _copy_file(dir_tree, 'changelog')

    # Create a couple of empty files.
    dummy_control = os.path.join(dir_tree, 'control')
    open(dummy_control, 'a').close()

    return dir_tree


def get_adt_run_command(backend, testrun_files, test_source_dir, results_dir):
    """Construct the adt command to run.

    :param testsuite: TestSpecification object containing test run details.

    """
    # Default adt-run hardcoded adt command
    adt_cmd = [
        'adt-run',
        '-B',
        '--user=root',
        '--unbuilt-tree={}'.format(testrun_files.unbuilt_dir),
        '--output-dir={}'.format(results_dir),
    ]

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
        '--copy={}:/root/auto_upgrade_test_settings'.format(
            testrun_files.run_config_file
        )
    )

    backend_args = backend.get_adt_run_args()

    return adt_cmd + ['---'] + backend_args


def main():
    setup_logging()
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

        # Setup output dir
        output_dir = get_output_dir(args)

        with prepare_test_environment(testsuite) as created_files:
            # Created files is a named tuple that contains:
            # run_config_file -> file containing details for the run
            # XXX output_directory ->  Path for output
            # testrun_tmp_dir -> tmp dir used for the run, can create files
            # here (i.e. debian/tests/)
            # Currently output dir is separate
            execute_adt_run(testsuite, backend, created_files, output_dir)

        artifacts_directory = os.path.join(
            output_dir, 'artifacts', 'upgrade_run'
        )
        logger.info(
            'Results can be found here: {}'.format(artifacts_directory)
        )
        display_results(artifacts_directory)


if __name__ == '__main__':
    main()
