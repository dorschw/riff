import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NoReturn

import typer
from loguru import logger

from utils import (
    git_changed_lines,
    parse_ruff_output,
    split_paths_by_max_len,
    validate_paths_relative_to_repo,
)
from violation import Violation

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)


class LinterErrorsFoundError(Exception):
    ...


def run_ruff(paths: list[Path], extra_ruff_args: str) -> subprocess.CompletedProcess:
    """
    Runs ruff with the given files and extra arguments.

    Args:
        files: A list of file paths.
        extra_ruff_args: Additional arguments for the 'ruff' command.

    Returns:
        A tuple containing the output of the 'ruff' command and its exit code.
    """

    ruff_command = f"ruff {','.join(str(file) for file in paths)} --format=json {extra_ruff_args}"  # noqa: E501
    logger.info(f"running {ruff_command}")

    with logger.catch(
        subprocess.CalledProcessError, message="Failed running ruff", reraise=True
    ):
        process = subprocess.run(
            ruff_command,
            shell=True,  # noqa: S602
            capture_output=True,
            text=True,
            check=True,
        )
        logger.debug(f"ruff output:\n{process.stdout}")
        logger.debug(f"ruff exit code:{process.returncode}")

    return process


def filter_violations(
    violations: Iterable[Violation],
    git_modified_lines: dict[Path, set[int]],
    always_fail_on: set[str] | frozenset = frozenset(),
) -> tuple[Violation, ...]:
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
def main(
    paths: list[Path],
    repo_path: Path,
    print_github_annotation: bool,
    extra_ruff_args: str,
    base_branch: str = "origin/master",
) -> NoReturn:
    validate_paths_relative_to_repo(paths=paths, repo_path=repo_path)

    violations: list[Violation] = []
    for path_group in split_paths_by_max_len(paths):
        violations.extend(
            parse_ruff_output(
                run_ruff(paths=path_group, extra_ruff_args=extra_ruff_args).output
            )
        )

    path_to_modified_lines = git_changed_lines(
        repo_path=repo_path, base_branch=base_branch
    )

    if filtered_violations := filter_violations(violations, path_to_modified_lines):
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
