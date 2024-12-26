from pathlib import Path

import pytest
from pytest_mock.plugin import MockerFixture

from riff.violation import Violation

# ruff: noqa: PLR2004

VIOLATIONS_EXPECTED_ANNOTATIONS = [
    pytest.param(
        Violation(
            error_code="E123",
            path=Path("/path/to/file.py"),
            line_start=10,
            message="Indentation error",
            linter_name="Ruff",
            is_autofixable=True,
            fix_suggestion="Use 4 spaces for indentation",
            line_end=12,
            column_start=5,
            column_end=20,
        ),
        (
            "::error file=file.py,line=10,endLine=12,col=5,endColumn=20::"
            'Ruff E123 (Indentation error)'
        ),
        id="Full data",
    ),
    pytest.param(
        Violation(
            error_code="E123",
            path=Path("/path/to/file.py"),
            line_start=10,
            message="Indentation error",
            linter_name="Ruff",
            is_autofixable=True,
        ),
        '::error file=file.py,line=10::Ruff E123: Indentation error',
        id="Without optional fields",
    ),
]


def test_violation_init() -> None:
    violation = Violation(
        error_code="E123",
        path=Path("/path/to/file.py"),
        line_start=10,
        message="Indentation error",
        linter_name="Ruff",
        is_autofixable=True,
        fix_suggestion="Use 4 spaces for indentation",
        line_end=12,
        column_start=5,
        column_end=20,
    )

    assert violation.error_code == "E123"
    assert violation.path == Path("/path/to/file.py")
    assert violation.line_start == 10
    assert violation.message == "Indentation error"
    assert violation.linter_name == "Ruff"
    assert violation.is_autofixable
    assert violation.fix_suggestion == "Use 4 spaces for indentation"
    assert violation.line_end == 12
    assert violation.column_start == 5
    assert violation.column_end == 20


@pytest.mark.parametrize(
    ("violation", "expected_annotation"), VIOLATIONS_EXPECTED_ANNOTATIONS
)
def test_github_annotation(
    violation: Violation, expected_annotation: str, mocker: MockerFixture
) -> None:
    mocker.patch.object(Path, "cwd", return_value=Path("/path/to/"))
    assert violation.github_annotation == expected_annotation


def test_parse() -> None:
    raw_data = {
        "code": "E123",
        "filename": "/path/to/file.py",
        "location": {"row": 10, "column": 5},
        "end_location": {"row": 12, "column": 20},
        "message": "Indentation error",
        "fix": {"message": "Use 4 spaces for indentation"},
    }
    violation = Violation.parse(raw_data)

    assert violation.error_code == "E123"
    assert violation.path == Path("/path/to/file.py")
    assert violation.line_start == 10
    assert violation.column_start == 5
    assert violation.line_end == 12
    assert violation.column_end == 20
    assert violation.message == "Indentation error"
    assert violation.fix_suggestion == "Use 4 spaces for indentation"
    assert violation.is_autofixable
    assert violation.linter_name == "Ruff"
