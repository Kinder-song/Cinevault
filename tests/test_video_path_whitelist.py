"""Verify video_path is restricted to configured whitelist roots."""
import os
import tempfile
import pytest

from config import Config
from utils.security import validate_video_path_against_roots


class TestVideoPathWhitelist:
    def test_directory_inside_allowed_root_passes(self, monkeypatch):
        """A directory inside an allowed root should validate as its realpath."""
        with tempfile.TemporaryDirectory() as allowed:
            monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
            sub = os.path.join(allowed, "videos")
            os.makedirs(sub)
            result = validate_video_path_against_roots(sub)
            assert result == os.path.realpath(sub)

    def test_path_outside_allowed_root_rejected(self, monkeypatch):
        with tempfile.TemporaryDirectory() as allowed:
            with tempfile.TemporaryDirectory() as outside:
                monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
                result = validate_video_path_against_roots(outside)
                assert result is None

    def test_path_etc_rejected(self, monkeypatch):
        monkeypatch.setattr(Config, "VIDEO_ROOTS", ["/tmp/videos"])
        result = validate_video_path_against_roots("/etc/passwd")
        assert result is None

    def test_symlink_escape_rejected(self, monkeypatch):
        with tempfile.TemporaryDirectory() as allowed:
            with tempfile.TemporaryDirectory() as outside:
                monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
                secret = os.path.join(outside, "secret.txt")
                open(secret, "w").close()
                link = os.path.join(allowed, "sneaky")
                os.symlink(secret, link)
                result = validate_video_path_against_roots(link)
                assert result is None

    def test_nonexistent_path_rejected(self, monkeypatch):
        """Non-existent paths must be rejected (the function validates a directory)."""
        with tempfile.TemporaryDirectory() as allowed:
            monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
            result = validate_video_path_against_roots(os.path.join(allowed, "does_not_exist"))
            assert result is None

    def test_file_path_rejected(self, monkeypatch):
        """A file (not a directory) must be rejected — video_path must be a directory."""
        with tempfile.TemporaryDirectory() as allowed:
            monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
            f = os.path.join(allowed, "a_file.txt")
            open(f, "w").close()
            result = validate_video_path_against_roots(f)
            assert result is None

    def test_empty_string_rejected(self, monkeypatch):
        with tempfile.TemporaryDirectory() as allowed:
            monkeypatch.setattr(Config, "VIDEO_ROOTS", [os.path.abspath(allowed)])
            assert validate_video_path_against_roots("") is None
