import json
import pprint
from pathlib import Path

import git
import typer
from git.repo import Repo
from unidiff import PatchedFile, PatchSet

from riff.logger import logger
from riff.violation import Violation


def parse_ruff_output(ruff_result_raw: str) -> tuple[Violation, ...]:
    if not ruff_result_raw:
        return ()

    with logger.catch(json.JSONDecodeError, reraise=True):
        raw_violations = json.loads(ruff_result_raw)

    violations = tuple(map(Violation.parse, raw_violations))
    logger.debug(f"parsed {len(violations)} ruff violations")
    return violations


def parse_git_modified_lines(
    base_branch: str,
) -> dict[Path, set[int]]:
    """
    Parse and return a dictionary mapping modified files to their changed line indices.

    This function analyzes the modifications between the current branch and the specified base branch.
    It identifies the lines that have been added (with non-empty content) in each modified file.
    The result is a dictionary where keys are file paths and values are sets of changed line indices.

    Args:
        base_branch (str): The base branch to compare modifications against.

    Returns:
        Dict[Path, Set[int]]: A dictionary mapping modified files to sets of line indices that were added.
    """

    def parse_modified_lines(patched_file: PatchedFile) -> set[int]:
        """
        Parse and return the line indices of added non-empty lines in a modified file.

        Args:
            patched_file (PatchedFile): A 'PatchedFile' object representing a modified file.

        Returns:
            set[int]: A set of line indices that have been added with non-empty content.
        """
        return {
            line.target_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_added and line.value.strip()
        }

    repo = Repo(search_parent_directories=True)
    repo_root = Path(repo.git_dir).parent

    result = {
        Path(repo_root, patched_file.path): parse_modified_lines(patched_file)
        for patched_file in PatchSet(
            repo.git.diff(
                base_branch,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            ),
        )
    }
    if result:
        logger.debug(
            "modified lines:\n"
            + pprint.pformat(
                {
                    str(file): sorted(changed_lines)
                    for file, changed_lines in result.items()
                },
                compact=True,
            )
        )
    else:
        logger.info(
            f"could not find any git-modified lines in {repo_root}: Are the files committed?"
        )
    return result


def validate_repo_path() -> Path:
    """
    Validate and retrieve the repository path.

    This function attempts to identify the parent directory of the current Git repository.
    It does so by searching upwards from the current working directory for the nearest Git repository.
    If a valid Git repository is found, the function returns the resolved path of its parent directory.
    If no Git repository is found, an error message is logged, and the application exits with a non-zero status.

    Returns:
        Path: The resolved path of the parent directory of the detected Git repository.

    Raises:
        typer.Exit: Raised with a status code of 1 if a Git repository is not found in the directory hierarchy.
    """
    try:
        return Path(git.Repo(search_parent_directories=True).git_dir).parent.resolve()
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"Cannot detect repository in {Path().resolve()}")
        raise typer.Exit(1) from None  # no need for whole stack trace
