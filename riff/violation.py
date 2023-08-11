from pathlib import Path
from typing import NamedTuple


class Violation(NamedTuple):
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
        endline = self.line_end if self.line_end is not None else self.line_start
        suffix = f"\n{self.fix_suggestion}" if self.fix_suggestion else ""
        return f"::error file={self.path},line={self.line_start},endline={endline},title={self.linter_name}:{self.error_code}{suffix}".replace(  # noqa: E501
            "\n",
            "%0A",  # GitHub annotations syntax
        )

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
