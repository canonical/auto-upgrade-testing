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
import re

from upgrade_testing.provisioning import backends

logger = logging.getLogger(__name__)


class ProvisionSpecification:
    def __init__(self):
        raise NotImplementedError()

    @property
    def system_states(self):
        # Note: Rename from releases
        raise NotImplementedError()

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        raise NotImplementedError()

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        raise NotImplementedError()

    @property
    def backend_name(self):
        """Return the name of the provision backend."""
        return self.backend.name

    def backend_available(self):
        """Return True if the provisioning backend is available."""
        return self.backend.available()

    def create(self, adt_base_path):
        """Provision the stored backend."""
        return self.backend.create(adt_base_path)

    def close(self):
        return self.backend.close() if hasattr(self.backend, "close") else None

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        raise NotImplementedError()

    @staticmethod
    def from_testspec(spec, spec_path):
        backend_name = spec["provisioning"]["backend"]
        spec_type = get_specification_type(backend_name)
        return spec_type(spec["provisioning"], spec_path)

    @staticmethod
    def from_provisionspec(spec, spec_path):
        # A provision spec is almost the same as a testdef provision spec
        # except it doesn't have the parent stanza.
        backend_name = spec["backend"]
        spec_type = get_specification_type(backend_name)
        return spec_type(spec, spec_path)


def get_specification_type(spec_name):
    __spec_map = dict(
        lxc=LXCProvisionSpecification,
        qemu=QemuProvisionSpecification,
    )
    try:
        return __spec_map[spec_name]
    except KeyError:
        logger.error("Unknown spec name: {}".format(spec_name))
        raise


class LXCProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config, provision_path):
        # Defaults to ubuntu
        self.distribution = provision_config.get("distribution", "ubuntu")
        self.releases = provision_config["releases"]
        self.arch = provision_config["arch"]
        self._provisionconfig_path = provision_path

        self.backend = backends.LXCBackend(
            self.initial_state, self.distribution, self.arch
        )

    @property
    def system_states(self):
        # Note: Rename from releases
        return self.releases

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        return self.releases[0]

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        return self.releases[-1]

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        return self.backend.get_adt_run_args(**kwargs)

    def __repr__(self):
        return "{classname}(backend={backend}, distribution={dist}, releases={releases})".format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases,
        )


class QemuProvisionSpecification(ProvisionSpecification):
    def __init__(self, provision_config, provision_path):
        self._provisionconfig_path = provision_path

        self.releases = provision_config["releases"]
        self.arch = provision_config.get("arch", "amd64")
        self.image_name = provision_config.get(
            "image_name",
            "autopkgtest-{}-{}-cloud.img".format(
                self.initial_state, self.arch
            ),
        )
        provision_config_directory = os.path.dirname(
            os.path.abspath(provision_path)
        )
        self.build_args = _render_build_args(
            provision_config.get("build_args", []), provision_config_directory
        )
        logger.info("Using build args: {}".format(self.build_args))

        self.backend = backends.QemuBackend(
            self.initial_state,
            self.arch,
            self.image_name,
            self.build_args,
        )

    @property
    def system_states(self):
        # Note: Rename from releases
        return self.releases

    @property
    def initial_state(self):
        """Return the string indicating the required initial system state."""
        return self.releases[0]

    @property
    def final_state(self):
        """Return the string indicating the required final system state."""
        return self.releases[-1]

    def get_adt_run_args(self, **kwargs):
        """Return list with the adt args for this provisioning backend."""
        return self.backend.get_adt_run_args(**kwargs)

    def __repr__(self):
        return "{classname}(backend={backend}, distribution={dist}, releases={releases})".format(  # NOQA
            classname=self.__class__.__name__,
            backend=self.backend,
            dist=self.distribution,
            releases=self.releases,
        )


def _render_build_args(build_args, profile_path):
    """Modify build args if required, returns a build args list.append

    For instance replaces any tokens in the string with the relevant parts.

    :param build_args: A list of strings.
    :param profile_path: String containing the path of the profile file in use.
    :returns: A list containing the build arg strings.

    """
    _token_lookup = dict(PROFILE_PATH=lambda: profile_path)

    if not isinstance(build_args, list):
        raise TypeError("build_args must be a list")
    if not all(isinstance(s, str) for s in build_args):
        raise ValueError("build_args must contain strings.")

    new_args = []
    for arg in build_args:
        new_args.append(_replace_placeholders(arg, _token_lookup))
    return new_args


def _replace_placeholders(original_string, token_lookup):
    token_strings = list(token_lookup.keys())
    # Ensure we replace the longest tokens first so we don't confuse substrings
    # (i.e. do $FOOBAR before $FOO otherwise we'll get $<changed>BAR)
    token_strings.sort(reverse=True)

    for token in token_strings:
        result = re.sub(
            r"\${}".format(token), token_lookup[token](), original_string
        )
        original_string = result

    return original_string
