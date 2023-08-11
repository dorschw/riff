import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NoReturn

import typer
from loguru import logger

from riff.utils import (
    git_changed_lines,
    parse_ruff_output,
    split_paths_by_max_len,
    validate_paths_relative_to_repo,
)
from riff.violation import Violation

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)


class LinterErrorsFoundError(Exception):
    ...


def run_ruff(paths: list[Path], extra_ruff_args: str) -> subprocess.CompletedProcess:
    """
    Runs ruff with the given paths and extra arguments.

    Args:
        paths: A list of file paths.
        extra_ruff_args: Additional arguments for the 'ruff' command.

    Returns:
        A tuple containing the output of the 'ruff' command and its exit code.
    """
    ruff_command = f"ruff {' '.join(str(file) for file in paths)} --format=json {extra_ruff_args}"  # noqa: E501
    logger.info(f"running {ruff_command}")
    3
    process = subprocess.run(
        ruff_command,
        shell=True,  # noqa: S602
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode not in (0,1,127):
        logger.info(f"ruff exit code:{process.returncode}")

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


@app.command()
def main(  # noqa: PLR0913
    paths: list[Path],
    print_github_annotation: bool = False,
    extra_ruff_args: str = "",
    always_fail_on: list[str] = (),
    repo_path: Path = Path(),
    base_branch: str = "origin/main",
) -> NoReturn:
    validate_paths_relative_to_repo(paths=paths, repo_path=repo_path)

    violations: list[Violation] = []
    for path_group in split_paths_by_max_len(paths):
        violations.extend(
            parse_ruff_output(
                run_ruff(paths=path_group, extra_ruff_args=extra_ruff_args).stdout
            )
        )

    path_to_modified_lines = git_changed_lines(
        repo_path=repo_path, base_branch=base_branch
    )

    if filtered_violations := filter_violations(
        violations, path_to_modified_lines, always_fail_on=always_fail_on
    ):
        logger.info(f"Found {len(filtered_violations)}")

        for violation in filtered_violations:
            logger.error(violation)

            if print_github_annotation:
                print(  # noqa: T201 required for GitHub Annotations
                    violation.to_github_annotation(),
                )
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    app()
