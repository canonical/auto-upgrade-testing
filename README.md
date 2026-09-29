# Auto Upgrade Testing

A test framework for testing Ubuntu system upgrades, using autopkgtest with
QEMU virtual machine testbeds. Test profiles are defined in the
[auto-upgrade-testing-specifications](https://git.launchpad.net/auto-upgrade-testing-specifications)
repository.

## Setup

Install the system dependencies (QEMU/OVMF for the virtual machine testbeds):

```bash
sudo apt install ovmf qemu-system-x86 lxc python3-lxc
```

Create the image cache directory:

```bash
sudo mkdir -p /var/cache/auto-upgrade-testing
```

Create a Python virtual environment:

```bash
rm -rf venv
python3 -m venv --system-site-packages venv
```

Clone this repository and the test specification profiles:

```bash
git clone https://github.com/canonical/auto-upgrade-testing.git aut
git clone https://git.launchpad.net/auto-upgrade-testing-specifications aut-spec
```

Install the framework and its runtime dependencies into the venv:

```bash
venv/bin/pip install -e "$(realpath aut)"
venv/bin/pip install junitparser paramiko retrying
```

Create a directory to store the test results:

```bash
mkdir results
```

## Run

Run an upgrade test against a profile from the specifications repository
(replace `<profile_yaml>` with the profile you want to run, e.g.
`ubuntu-noble-resolute-basic-amd64_qemu.yaml`):

```bash
sudo --preserve-env=AUTOPKGTEST_APT_SOURCES_FILE,RELEASE_UPGRADE_NO_FORCE_OVERWRITE \
  venv/bin/python3 -m upgrade_testing.command_line \
  -c "$(realpath aut-spec)/profiles/<profile_yaml>" \
  --provision \
  --results-dir "$(realpath results)" \
  --adt-args=--timeout-factor=10
```

### Options

| Option | Description |
| ------ | ----------- |
| `-c`, `--config` | The profile/config file to use for this run. |
| `--provision` | Provision the requested backend before running. |
| `-v`, `--verbose-provision` | Provision with build output enabled. |
| `-f`, `--force-provision` | Provision a new image regardless of cache. |
| `--results-dir` | Directory to store results generated during the run. |
| `-a`, `--adt-args` | Arguments to pass through to the autopkgtest runner. |
| `-k`, `--keep-overlay` | Keep the resulting overlay image. |

## Results layout

Each test script run gets a unique directory inside the suite results
directory, named `{pre|post}_{script_name}` depending on whether it runs
before or after the upgrade:

```
-- $TEST_RESULTS_DIR/
---- pre_setup_background/
------ output.log
---- post_test_background_exists/
------ output.log
```

During a script run, its own directory is available via the
`TESTRUN_RESULTS_DIR` environment variable, and the parent suite directory via
`TEST_RESULTS_DIR`.
