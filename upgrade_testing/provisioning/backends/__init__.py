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

from upgrade_testing.provisioning.backends._lxc import LXCBackend

__all__ = ['get_backend']

_backends = dict(lxc=LXCBackend)


def get_backend(backend_name):
    """Return a backend provider for the requested backend.

    :raises ValueError: if backend is unknown.

    """

    try:
        return _backends[backend_name]
    except KeyError:
        raise ValueError('Backend "{}" is unknown'.format(backend_name))
