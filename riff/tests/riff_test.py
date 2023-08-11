from pathlib import Path

import pytest

from riff.riff import filter_violations
from riff.violation import Violation


@pytest.mark.parametrize(
    ("modified_lines", "expected_violation_count", "always_fail_on"),
    [
        pytest.param({}, 0, None, id="nothing changed"),
        pytest.param({3}, 0, None, id="unrelated lines changed"),
        pytest.param({1}, 1, None, id="violation 1 line changed"),
        pytest.param({1, 3}, 1, None, id="violation 1 line changed, and unrelated"),
        pytest.param({1, 2}, 2, None, id="violation 1+2 lines changed"),
        pytest.param(
            {1, 2, 3}, 2, None, id="violation 1+2 lines changed, and unrelated"
        ),
        pytest.param({}, 1, {"E1"}, id="nothing changed, always fail on E1"),
        pytest.param({2}, 2, {"E1"}, id="line 1 changed, always fail on E2"),
        pytest.param({}, 2, {"E1", "E2"}, id="nothing changed, always fail on E1,E2"),
        pytest.param(
            {3}, 2, {"E1", "E2"}, id="unrelated line changed, always fail on E1,E2"
        ),
        pytest.param(
            {1, 2}, 2, {"E1", "E2"}, id="1+2 lines changed, always fail on E1,E2"
        ),
    ],
)
def test_filter_violations(
    modified_lines: set[int],
    expected_violation_count: int,
    always_fail_on: set[str] | None,
) -> None:
    violations = [
        Violation(
            error_code="E1",
            path=Path("file1.py"),
            line_start=1,
            message="Violation 1",
            linter_name="Linter 1",
        ),
        Violation(
            error_code="E2",
            path=Path("file1.py"),
            line_start=2,
            message="Violation 2",
            linter_name="Linter 2",
        ),
    ]
    git_modified_lines = {
        Path("file1.py"): modified_lines,
    }

    result = filter_violations(violations, git_modified_lines, always_fail_on)
    modified_lines_result = {violation.line_start for violation in result}

    assert len(result) == expected_violation_count
    assert len(modified_lines_result) == expected_violation_count
