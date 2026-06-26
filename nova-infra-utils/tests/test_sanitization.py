"""Behaviour tests for the InputSanitizer (pure logic, no network/credentials)."""
import pytest

from nova_infra_utils.web_hardening.sanitization import InputSanitizer


@pytest.fixture
def sanitizer():
    return InputSanitizer()


def test_html_sanitization_strips_scripts(sanitizer):
    out = sanitizer.sanitize_html_content("<script>alert(1)</script><b>ok</b>")
    assert "<script>" not in out
    assert "<b>ok</b>" in out


def test_file_path_blocks_traversal(sanitizer):
    with pytest.raises(ValueError):
        sanitizer.sanitize_file_path("../../etc/passwd")


def test_file_path_strips_leading_slash(sanitizer):
    assert sanitizer.sanitize_file_path("/foo/bar.txt") == "foo/bar.txt"


def test_validate_project_name_rejects_injection(sanitizer):
    # Disallowed characters (spaces, slashes, shell metachars) should not survive.
    cleaned = sanitizer.validate_project_name("evil; rm -rf /")
    assert "/" not in cleaned
    assert ";" not in cleaned
    assert " " not in cleaned
