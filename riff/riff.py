import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import NoReturn

import typer
from loguru import logger

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
    ruff_args: list[str],
) -> subprocess.CompletedProcess:
    """
    Runs ruff with the given paths and extra arguments.

    Args:
        paths: A list of file paths.
        extra_ruff_args: Additional arguments for the 'ruff' command.

    Returns:
        A tuple containing the output of the 'ruff' command and its exit code.
    """
    if "--format" in ruff_args:
        logger.error("the `--format` argument is not (yet) supported")
        raise ArgumentNotSupportedError

    ruff_command = " ".join(
        (
            "ruff",
            *ruff_args,
            "--format=json",
        )
    ).rstrip()
    logger.debug(f"running '{ruff_command}'")

    process = subprocess.run(
        ruff_command,
        shell=True,  # noqa: S602
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode not in (0, 1, 2, 127):
        logger.info(f"ruff exit code:{process.returncode}")

    return process


def filter_violations(
    violations: Iterable[Violation],
    git_modified_lines: dict[Path, set[int]],
    always_fail_on: Iterable[str] | None,
) -> tuple[Violation, ...]:
    always_fail_on = set(always_fail_on) if always_fail_on else set()

    result = []
    for violation in violations:
        if violation.error_code in always_fail_on:
            result.append(violation)
            continue

        if violation.path not in git_modified_lines:
            logger.warning(f"{violation.path} not found in git diff")
            continue

        if violation.line_start in git_modified_lines[violation.path]:
            result.append(violation)
        else:
            logger.debug(
                f"ignoring violation of {violation.error_code} in {violation.path} line {violation.line_start}"  # noqa: E501
            )
    return tuple(
        sorted(
            result,
            key=lambda violation: str(
                (violation.path, violation.line_start, violation.error_code),
            ),
        )
    )


@app.command(
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }
)
def main(  # dead: disable
    # typer doesn't support `| None`
    context: typer.Context,  # ruff args
    always_fail_on: list[str] = None,  # type:ignore[assignment] # noqa: RUF013
    print_github_annotation: bool = False,
    base_branch: str = "origin/main",
) -> NoReturn:
    validate_repo_path()  # raises if a repo isn't found at cwd or above

    if not (modified_lines := parse_git_modified_lines(base_branch)):
        raise typer.Exit(1)

    try:
        ruff_process_result = run_ruff(context.args)
    except ArgumentNotSupportedError:
        raise typer.Exit(1) from None

    if filtered_violations := filter_violations(
        violations=parse_ruff_output(ruff_process_result.stdout),
        git_modified_lines=modified_lines,
        always_fail_on=(always_fail_on or []),
    ):
        logger.info(f"Found {len(filtered_violations)} ruff violations")
        for violation in filtered_violations:
            logger.error(violation)

            if print_github_annotation:
                print(  # noqa: T201 required for GitHub Annotations
                    violation.to_github_annotation(),
                )
        raise typer.Exit(1)

    logger.info("No ruff violations found ⚡")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
