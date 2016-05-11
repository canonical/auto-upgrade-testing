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

import unittest

from upgrade_testing.configspec import _config as _c


class HelperMethodTestCases(unittest.TestCase):

    def test_load_configdef_raises_ValueError_on_non_yaml_filename(self):
        self.assertRaises(ValueError, _c._load_configdef, 'test.txt')

    def test_read_yaml_config_raises_on_nonexistant_file(self):
        self.assertRaises(FileNotFoundError, _c._read_yaml_config, 'test.txt')
