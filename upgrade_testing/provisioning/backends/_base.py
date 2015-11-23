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


class ProviderBackend:
    """Abstract baseclass for all provision backends."""

    def __init__(self, **args):
        raise NotImplementedError(
            'Cannot be instatiated, please use an established backend'
        )

    def available(self):
        """Return true if there is an instance of this backend that can <> the
        required settings."""
        raise NotImplementedError()

    def create(self):
        """Creates an instance of this backend adhering to the provided args.

        :raises ValueError: if an instance already exists that matches these
          requirements.

        """
        raise NotImplementedError()

    def get_adt_run_args(self, *kwargs):
        """Return a list containing required args to pass to adt-run."""
        raise NotImplementedError()

    @property
    def name(self):
        raise NotImplementedError()
