=================
 Upgrade Testing
=================

Developers
==========

Testing + pep8
--------------

When making changes it is worth while checking them against the projects flake8
checker (which has custom ignores).

This can be achieved by running the script `.project-flake8.sh` found in the
project root.
This script is also run during package build.

Testfile Spec
=============

Provisioning Backends
=====================

Different provisioning needs have different options that can either stored in
the test spec itself or in a separate provisioning file.

The following supported backends detail their available settings both required and optional.

LXC
---

Ubuntu Touch
------------

This backend supports Ubuntu devices.

Backend name: **touch**

Required elements
~~~~~~~~~~~~~~~~~

:channel:
   Representing the channel that the device should be flashed
   from. e.g. ubuntu-touch/rc-proposed/bq-aquaris.en

:password: Password for the device

:revision: The revision of the provided channel to flash and provison on the
           device. The device will be upgraded to the latest revision of the
           same channel during the upgrade process.
           N.B. There is no mechanism to upgrade to an arbitary revision.


Optional elements
~~~~~~~~~~~~~~~~~

:serial: The serial of the specific device to interact with. If more than one
         device is attached an no serial is specified an error will be
         raised. If there is a single device no serial is required.

:ssid: Network ssid to connect to. After being flashed this ssid will be setup
       on the target device.


Virtual Machine
---------------

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
