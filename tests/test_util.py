import os
import re

import pytest

from takeoff import util as victim


class TestPatternMatching(object):
    pattern = re.compile("(^foo)-([0-9]{1,3})-snapshot$")
    test_strings = [
        "foo-031-snapshot",
        "foo-12-snapshot",
        "foo-1234-snapshot",
        "foobar-309-snapshot",
        "foo-20-snap",
    ]

    def test_has_prefix_match(self):
        values = [True, True, False, False, False]
        for string, value in zip(self.test_strings, values):
            assert victim.has_prefix_match(string, "foo", self.pattern) == value

    def test_get_matching_group(self):
        values = [(1, "031"), (0, "foo")]
        for string, (idx, value) in zip(self.test_strings[:2], values):
            assert victim.get_matching_group(string, self.pattern, idx) == value

    def test_get_matches_no_group_found(self):
        values = [(1, "031"), (0, "foo"), (3, "snap")]
        for string, (idx, value) in zip(self.test_strings[2:], values):
            with pytest.raises(ValueError):
                assert victim.get_matching_group(string, self.pattern, idx) == value

    def test_get_matching_group_not_enough_groups(self):
        values = [(3, "031"), (7, "foo")]
        for string, (idx, value) in zip(self.test_strings[:2], values):
            with pytest.raises(IndexError):
                assert victim.get_matching_group(string, self.pattern, idx) == value

    def test_get_full_yaml_filename_file_exists(self):
        filename = "deployment"
        result = victim.get_full_yaml_filename(filename)
        expected_result = os.path.join(".takeoff", "deployment.yml")
        assert result == expected_result

    def test_get_full_yaml_filename_file_not_exists(self):
        filename = "my_stupid_file"
        with pytest.raises(FileNotFoundError):
            victim.get_full_yaml_filename(filename)


def test_is_base64_valid_string():
    assert victim.is_base64("c29tZXRoaW5n")


def test_is_base_64_invalid_string():
    assert not victim.is_base64("something")


def test_is_base64_valid_bytes():
    assert victim.is_base64(b'c29tZXRoaW5n')


def test_is_base64_invalid_bytes():
    assert not victim.is_base64(b'c29tZXRoaW5')


def test_ensure_base64_non_encoded():
    result = victim.ensure_base64("something")
    assert result == "c29tZXRoaW5n"


def test_ensure_base64_encoded():
    result = victim.ensure_base64("c29tZXRoaW5n")
    assert result == "c29tZXRoaW5n"


def test_get_main_py_name():
    result = victim.get_main_py_name("project-name", "my-branch", "my_app/src/some.py")
    assert result == "project-name/project_name-main-my_branch.py"


def test_get_main_py_name_with_original_filename():
    result = victim.get_main_py_name("project-name", "my-branch", "my_app/src/some.py", True)
    assert result == "project-name/project_name-main-my_branch-some.py"
