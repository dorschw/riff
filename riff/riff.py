import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NoReturn

import typer

from riff.logger import logger
from riff.utils import (
    parse_git_modified_lines,
    parse_ruff_output,
    validate_repo_path,
)
from riff.violation import Violation

app = typer.Typer(no_args_is_help=True, invoke_without_command=True)


class ArgumentNotSupportedError(Exception):
    ...


def run_ruff(
    ruff_args: Sequence[str],
) -> subprocess.CompletedProcess:
    """
    Run Ruff with the given arguments.

    This function executes the 'ruff' command-line tool with the specified arguments.
    It captures the output and exit code of the command and returns a `subprocess.CompletedProcess`
    object containing this information.

    Args:
        ruff_args (list[str]): A list of arguments to be passed to the 'ruff' command.

    Returns:
        subprocess.CompletedProcess: A named tuple with the following attributes:
            - args: The list of arguments used to launch the 'ruff' command.
            - returncode: The exit status of the 'ruff' command process.
            - stdout: The standard output (stdout) of the 'ruff' command as a string.
            - stderr: The standard error (stderr) of the 'ruff' command as a string.
    Raises:
        ArgumentNotSupportedError: Raised if the `--output-format` argument is included in ruff_args.

    Note:
        If the `ruff` command exits with a non-zero status code, the returncode attribute
        of the returned CompletedProcess object will reflect that status code.
    """
    if not ruff_args:
        ruff_args = (".",)
    elif "--output-format" in ruff_args:
        logger.error("the `--output-format` argument is not (yet) supported")
        raise ArgumentNotSupportedError

    ruff_command = " ".join(
        (
            "ruff",
            *ruff_args,
            "--output-format=json",
        )
    )
    logger.debug(f"running '{ruff_command}'")

    return subprocess.run(
        ruff_command,
        shell=True,  # noqa: S602
        capture_output=True,
        text=True,
        check=False,
    )


def filter_violations(
    violations: Iterable[Violation],
    git_modified_lines: dict[Path, set[int]],
    always_fail_on: Iterable[str] | None,
) -> tuple[Violation, ...]:
    always_fail_on = set(always_fail_on or ())
    """
    Filters a collection of violations based on certain criteria.

    This function takes a collection of violations, a dictionary of Git-modified lines,
    and a set of error codes that should always result in a failure.
    It filters the violations based on whether they meet any of the following conditions:
    1. The error code is in the `always_fail_on` set.
    2. The starting line of the violation is among the modified lines for the corresponding file.

    Parameters:
    - violations (Iterable[Violation]): A collection of violation objects to be filtered.
    - git_modified_lines (dict[Path, set[int]]): A dictionary where keys are file paths and values
      are sets of modified line numbers for each file.
    - always_fail_on (Iterable[str] | None): A collection of error codes that should always
      result in a failure. If None, no error codes are treated as always failing.

    Returns:
    tuple[Violation, ...]: A tuple of sorted violation objects that meet the filtering criteria.
    """

    return tuple(
        sorted(
            (
                violation
                for violation in violations
                if (violation.error_code in always_fail_on)
                or (violation.line_start in git_modified_lines.get(violation.path, ()))
            ),
            key=lambda violation: str(
                (violation.path, violation.line_start, violation.error_code),
            ),
        )
    )


def validate_ruff_installation() -> None:
    """
    Check whether ruff is installed, and its version is supported.
    """
    from packaging.version import InvalidVersion, Version

    try:
        ruff_version_process = subprocess.run(
            ["ruff", "--version"],  # noqa: S603, S607
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as e:
        logger.exception("Make sure ruff is installed.")
        raise typer.Exit(1) from e

    try:
        version = Version(
            ruff_version_process.stdout.removeprefix("ruff ").rstrip("\n")
        )
        logger.debug(f"ruff {version=!s}")
    except InvalidVersion as e:
        logger.error(f"cannot parse version {version}")
        raise typer.Exit(1) from e

    if version < Version("0.0.291"):  # minimal version with --output-format
        logger.error(f"Found Ruff {version!s}, but 0.0.291 or newer is required.")
        typer.Exit(1)


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
)
def main(  # dead: disable
    context: typer.Context,  # ruff args
    always_fail_on: list[str] = None,  # type:ignore[assignment] # noqa: RUF013  # typer doesn't support `| None`
    print_github_annotation: bool = False,
    base_branch: str = "origin/main",
) -> NoReturn:
    validate_repo_path()  # raises if a repo isn't found at cwd or above
    validate_ruff_installation()  # raises if ruff is not installed/outdated version

    if not (modified_lines := parse_git_modified_lines(base_branch)):
        logger.info("No git-modified lines detected, exiting.")
        raise typer.Exit(0)

    try:
        ruff_process_result = run_ruff(context.args)
    except ArgumentNotSupportedError:
        raise typer.Exit(1) from None  # no need for whole stack trace

    if not (
        filtered_violations := filter_violations(
            violations=parse_ruff_output(ruff_process_result.stdout),
            git_modified_lines=modified_lines,
            always_fail_on=always_fail_on,
        )
    ):
        logger.success("No ruff violations found ⚡")
        raise typer.Exit(0)

    print(f"Found {len(filtered_violations)} ruff violations:")  # noqa: T201
    for violation in filtered_violations:
        logger.error(violation)
        if print_github_annotation:
            print(  # noqa: T201
                violation.to_github_annotation(),
            )
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
