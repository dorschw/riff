import json
from pathlib import Path

from riff.utils import parse_ruff_output
from riff.violation import Violation


def test_parse_ruff_output_valid_one() -> None:
    code = "E0001"
    file = "file.py"
    start_row = 1
    start_column = 2
    end_row = 3
    end_column = 4
    error_message = "Error message"
    fix_suggestion= "Fix suggestion"

    mocked_ruff_output = json.dumps(
        [
            {
                "code": code,
                "filename": file,
                "location": {"row": start_row, "column": start_column},
                "end_location": {"row": end_row, "column": end_column},
                "message":error_message,
                "fix": {"message": fix_suggestion},
            }
        ]
    )
    violation = Violation(
        error_code=code,
        path=Path(file),
        line_start=start_row,
        message=error_message,
        linter_name="Ruff",
        is_autofixable=True,
        fix_suggestion=fix_suggestion,
        line_end=end_row,
        column_start=start_column,
        column_end=end_column,
    )
    assert parse_ruff_output(mocked_ruff_output) == (violation,)
