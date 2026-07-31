"""Import-order tests: no circular import for any first-import submodule."""

from __future__ import annotations

import subprocess
import sys


def _import_in_fresh_interpreter(module: str) -> subprocess.CompletedProcess[str]:
    """Import ``module`` as the first user import in a clean interpreter."""
    return subprocess.run(
        [sys.executable, "-c", f"import {module}; print('ok', {module!r})"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_import_choreo_reliability_first() -> None:
    """import choreo.reliability must work as the very first import."""
    result = _import_in_fresh_interpreter("choreo.reliability")
    assert result.returncode == 0, (
        f"circular import or failure importing choreo.reliability first:\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "ok" in result.stdout


def test_import_choreo_core_first() -> None:
    result = _import_in_fresh_interpreter("choreo.core")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_choreo_package_first() -> None:
    result = _import_in_fresh_interpreter("choreo")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
