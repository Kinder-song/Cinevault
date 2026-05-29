"""Security utilities for path validation and login attempt tracking."""

import os
import time
from threading import Lock


def validate_video_path(base_path: str, user_provided_path: str) -> str | None:
    """
    Validates that user-provided path doesn't escape base_path to prevent path traversal attacks.

    Args:
        base_path: The base directory that should be the root of allowed paths.
        user_provided_path: The path provided by the user (can be relative or absolute).

    Returns:
        The validated absolute path if valid, None if the path would escape base_path.
    """
    # Resolve base_path to absolute path
    base_path = os.path.abspath(base_path)

    # Resolve user_provided_path - if absolute, os.path.abspath handles it
    # If relative, it will be resolved relative to current working directory
    # We need to join it with base_path first for relative paths
    if not os.path.isabs(user_provided_path):
        resolved_path = os.path.abspath(os.path.join(base_path, user_provided_path))
    else:
        resolved_path = os.path.abspath(user_provided_path)

    # Check if the resolved path starts with base_path
    # Using os.path.commonpath would be cleaner but can raise ValueError
    # if paths are on different drives on Windows
    if not resolved_path.startswith(base_path + os.sep) and resolved_path != base_path:
        return None

    return resolved_path


class LoginAttemptTracker:
    """
    Tracks login attempts per IP with brute-force protection.

    Attributes:
        max_attempts: Maximum failed attempts before lockout (default 5).
        lockout_seconds: Duration of lockout in seconds (default 300).
    """

    def __init__(self, max_attempts: int = 5, lockout_seconds: int = 300):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts: dict[str, tuple[int, float]] = {}  # ip -> (count, first_attempt_time)
        self._lock = Lock()

    def is_locked_out(self, ip: str) -> bool:
        """Check if IP is currently locked out."""
        with self._lock:
            if ip not in self._attempts:
                return False
            count, first_attempt_time = self._attempts[ip]
            if count < self.max_attempts:
                return False
            # Check if lockout period has expired
            elapsed = time.time() - first_attempt_time
            if elapsed >= self.lockout_seconds:
                # Lockout expired, clear the record
                del self._attempts[ip]
                return False
            return True

    def record_failure(self, ip: str) -> int:
        """
        Record failed login attempt.

        Returns:
            Number of remaining attempts before lockout (0 when locked out).
        """
        with self._lock:
            current_time = time.time()
            if ip not in self._attempts:
                self._attempts[ip] = (1, current_time)
                return self.max_attempts - 1

            count, first_attempt_time = self._attempts[ip]

            # Check if lockout period has expired and reset if so
            elapsed = current_time - first_attempt_time
            if elapsed >= self.lockout_seconds:
                self._attempts[ip] = (1, current_time)
                return self.max_attempts - 1

            # Increment count
            count += 1
            self._attempts[ip] = (count, first_attempt_time)

            remaining = self.max_attempts - count
            return max(0, remaining)

    def record_success(self, ip: str) -> None:
        """Clear attempts on successful login."""
        with self._lock:
            if ip in self._attempts:
                del self._attempts[ip]