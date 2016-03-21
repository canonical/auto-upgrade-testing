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

from upgrade_testing.provisioning import _provisionconfig as _p


class ReplacePlaceholdersTestCases(unittest.TestCase):

    def test_returns_untouched_string_when_no_tokens_involved(self):
        noplaceholder_string = 'This is a normal string, no placeholders'
        self.assertEqual(
            noplaceholder_string,
            _p._replace_placeholders(noplaceholder_string, {})
        )

    def test_replaces_simple_token(self):
        base_string = '$FOO'
        expected_string = 'texthaschanged'
        _token_lookup = dict(FOO=lambda: expected_string)
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            expected_string
        )

    def test_replaces_simple_token_while_leaving_other_text_alone(self):
        base_string = 'nottoken $FOO nottoken'
        expected_string = 'texthaschanged'
        _token_lookup = dict(FOO=lambda: expected_string)
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            'nottoken {} nottoken'.format(expected_string)
        )

    def test_leaves_non_tokens_alone(self):
        """FOO isn't a valid token it's lacking a '$' and must be left alone.

        """
        base_string = 'FOO'
        _token_lookup = dict(FOO=lambda: 'FAIL')
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            base_string
        )

    def test_replaces_multiple_tokens_within_a_string(self):
        base_string = '$FOO and $BAR'
        expected_string = '123 and abc'
        _token_lookup = dict(FOO=lambda: '123', BAR=lambda: 'abc')
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            expected_string
        )

    def test_does_not_replace_unknown_token(self):
        base_string = '$FOO and $BAR'
        _token_lookup = dict(FOO=lambda: '123')
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            '123 and $BAR'
        )

    def test_replaces_superstr_first(self):
        """If there are tokens with similar names the right tokens must be
        replaced.

        """
        base_string = '$FOOBAR and $FOO and $BAR'
        _token_lookup = dict(
            FOO=lambda: 'foo',
            BAR=lambda: 'bar',
            FOOBAR=lambda: 'baz'
        )
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            'baz and foo and bar'
        )

    def test_confirms_full_token_word(self):
        """Similar tokens must not be confused. i.e. FOOA is different to FOOB.

        """
        base_string = '$FOOA and $FOOB'
        _token_lookup = dict(
            FOO=lambda: 'FAIL',
            FOOA=lambda: 'A',
            FOOB=lambda: 'B',
        )
        self.assertEqual(
            _p._replace_placeholders(base_string, _token_lookup),
            'A and B'
        )


class RenderBuildArgsTestCase(unittest.TestCase):

    def test_raises_ValueError_if_not_passed_list_of_strings(self):
        self.assertRaises(ValueError, _p._render_build_args, [1], '')

    def test_raises_TypeError_if_not_passed_list(self):
        self.assertRaises(TypeError, _p._render_build_args, '', '')

    def test_returns_empty_list_when_empty_list_passed_in(self):
        self.assertEqual(_p._render_build_args([], ''), [])

    def test_returns_unmodified_list_string(self):
        build_args = ['no tokens here']
        self.assertEqual(_p._render_build_args(build_args, ''), build_args)

    def test_returns_list_string_with_tokens_modified(self):
        build_args = ['$PROFILE_PATH here', '$PROFILE_PATH there']
        self.assertEqual(
            _p._render_build_args(build_args, '/tmp'),
            ['/tmp here', '/tmp there']
        )

    def test_returns_a_list_of_equal_elements_of_that_passed_in(self):
        build_args = ['1', '2', '3']
        self.assertEqual(
            len(_p._render_build_args(build_args, '')),
            len(build_args)
        )


class QemuProvisionSpecificationTestCases(unittest.TestCase):

    def test_stores_passed_specification_details(self):
        """QemuProvisionSpecification must store the passed details regarding
        the qemu image and run details.

        """
        spec = dict(
            releases=['release 1', 'release 2'],
            arch='test arch',
            image_name='image name',
            build_args=['$PROFILE_PATH']
        )
        spec_path = '/test/path/test.yaml'

        qemu_spec = _p.QemuProvisionSpecification(spec, spec_path)

        self.assertEqual(qemu_spec.releases, spec['releases'])
        self.assertEqual(qemu_spec.arch, spec['arch'])
        self.assertEqual(qemu_spec.image_name, spec['image_name'])
        self.assertEqual(qemu_spec.build_args, ['/test/path'])
        self.assertEqual(qemu_spec.initial_state, 'release 1')
