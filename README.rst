=================
 Upgrade Testing
=================

Output directory
================

Each test script run will have a unique directory prepared for it in the main
artifacts directory.
The path to this directory will be stored in the env-var TESTRUN_RESULTS_DIR.
The naming convention of this directory is: '{post|pre}_{script_name}'
(post/pre depending if it's run before or pafter the upgrade.)

This directory will be a sub-directory within the full suite directory. This
directory path is stored in TEST_RESULTS_DIR.

For instance if you're running a pre-upgrade script named setup_background and
a post-upgrade test script named test_background_exists and each script outputs details to a file: "${TESTRUN_RESULTS_DIR}/output.log" the directory structure will look like this::

  -- $TEST_RESULTS_DIR/
  ---- pre_setup_background/  # Known during the script run as $TESTRUN_RESULTS_DIR
  -------- output.log
  ---- post_test_background_exists/  # Known during the script run as $TESTRUN_RESULTS_DIR
  -------- output.log
