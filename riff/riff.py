from enum import Enum
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple, NoReturn

import typer
from loguru import logger

from riff.utils import (
    git_changed_lines,
    parse_ruff_output,
)
from riff.violation import Violation

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)


class LinterErrorsFoundError(Exception):
    ...


def run_ruff(ruff_args: str) -> subprocess.CompletedProcess:
    """
    Runs ruff with the given paths and extra arguments.

    Args:
        paths: A list of file paths.
        extra_ruff_args: Additional arguments for the 'ruff' command.

    Returns:
        A tuple containing the output of the 'ruff' command and its exit code.
    """
    ruff_command = f"ruff {ruff_args} --format=json"
    logger.info(f"running {ruff_command}")

    process = subprocess.run(
        ruff_command,
        shell=True,  # noqa: S602
        capture_output=True,
        text=True,
        check=False,
    )

    if process.returncode not in (0, 1, 2):
        logger.warning(f"ruff quit with exit code {process.returncode}")

    return process


def filter_violations(
    violations: Iterable[Violation],
    git_modified_lines: dict[Path, set[int]],
    always_fail_on: Iterable[str] | None,
) -> tuple[Violation, ...]:
    always_fail_on = set(always_fail_on) if always_fail_on else set()

    return tuple(
        sorted(
            (
                violation
                for violation in violations
                if (
                    violation.line_start in git_modified_lines.get(violation.path, ())
                    or violation.error_code in always_fail_on
                )
            ),
            key=lambda violation: str(
                (violation.path, violation.line_start, violation.error_code),
            ),
        ),
    )

class OutputFormat(str, Enum):
    JSON = "json"
    GITHUB = "github"
    NO_OUTPUT = "no_output"

class RuffArgs(NamedTuple):
    comamnd:str
    github_format:bool

    @staticmethod
    def parse(command: str) -> "RuffArgs":
        command = command.removeprefix("ruff ")
        command = command.strip()

        output_format = OutputFormat.NO_OUTPUT

        if (format_match := re.match(r"--format[ =](\s+)",command,re.IGNORECASE)):
            if (format_lower := format_match[1].lower()) in OutputFormat:
                output_format = OutputFormat[format_lower]
            else:
                raise ValueError(f"Unsupported format {output_format}")

        if "--format" in command and (not github):
            raise ValueError("Using --format is not yet supported")

        return RuffArgs(command, github_format=github)

    @property
    def first_path(self:"RuffArgs") -> Path:
        if not self.comamnd:
            return Path()

        if (path:= Path(self.comamnd.split(" "[0],maxsplit=1))).exists():
            return path
        raise ValueError(f"path {path} does not exist")

@app.command()
def main(
    ruff_command: str,
    always_fail_on: list[str] = [],  # noqa: B006
    base_branch: str = "origin/main",
) -> NoReturn:
    ruff_args = RuffArgs.parse(ruff_command)

    violations = parse_ruff_output(run_ruff(ruff_args=ruff_command).stdout)

    path_to_modified_lines = git_changed_lines(
        repo_path=ruff_args.first_path, base_branch=base_branch
    )

    if filtered_violations := filter_violations(
        violations, path_to_modified_lines, always_fail_on=always_fail_on
    ):
        logger.info(f"Found {len(filtered_violations)}")

        for violation in filtered_violations:
            logger.error(violation)

            if ruff_args.github_format:
                print(  # noqa: T201 required for GitHub Annotations
                    violation.to_github_annotation(),
                )
        sys.exit(1)

    logger.info("No ruff violations found :)")
    sys.exit(0)


if __name__ == "__main__":
    app()
