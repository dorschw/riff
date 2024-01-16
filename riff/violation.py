from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
    """
    Represents a code violation reported by a linter.

    Attributes:
        error_code (str): The error code associated with the violation.
        path (Path): The file path where the violation occurred.
        line_start (int): The starting line number of the violation.
        message (str): The detailed description of the violation.
        linter_name (str): The name of the linter that reported the violation.
        is_autofixable (bool, optional): Indicates whether the violation is autofixable.
        fix_suggestion (str, optional): Suggested fix for the violation.
        line_end (int, optional): The ending line number of the violation.
        column_start (int, optional): The starting column number of the violation.
        column_end (int, optional): The ending column number of the violation.
    """

    error_code: str
    path: Path
    line_start: int
    message: str
    linter_name: str
    is_autofixable: bool | None = None
    fix_suggestion: str | None = None
    line_end: int | None = None
    column_start: int | None = None
    column_end: int | None = None

    def to_github_annotation(self: "Violation") -> str:
        relativized_path = self.path.relative_to(Path.cwd())
        first_part = f"::error title=Ruff ({self.error_code}),file={self.path},line={self.line_start},col={self.column_start},endLine={self.line_end},endColumn={self.column_end}::"
        second_part = f"{relativized_path}:{self.line_start}:{self.column_start}: {self.error_code} {self.message}"
        return first_part + second_part

    @staticmethod
    def parse(raw: dict) -> "Violation":
        fix: dict = raw.get("fix") or {}
        return Violation(
            linter_name="Ruff",
            error_code=raw["code"],
            line_start=raw["location"]["row"],
            column_start=raw["location"]["column"],
            line_end=raw["end_location"]["row"],
            column_end=raw["end_location"]["column"],
            path=Path(raw["filename"]),
            message=raw["message"],
            fix_suggestion=fix.get("message"),
            is_autofixable=bool(fix),
        )
