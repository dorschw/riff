import json
import pprint
from pathlib import Path

import git
import typer
from git.repo import Repo
from loguru import logger
from unidiff import PatchedFile, PatchSet

from riff.violation import Violation


def parse_ruff_output(ruff_result_raw: str) -> tuple[Violation, ...]:
    if not ruff_result_raw:
        return ()

    with logger.catch(json.JSONDecodeError, reraise=True):
        raw_violations = json.loads(ruff_result_raw)

    violations = tuple(map(Violation.parse, raw_violations))
    logger.debug(f"parsed {len(violations)} ruff violations")
    return violations


def parse_git_changed_lines(
    base_branch: str,
) -> dict[Path, set[int]]:
    """Returns
    Dict[Path, Tuple[int]]: maps modified files, to the indices of the lines changed.
    """

    def parse_modified_lines(patched_file: PatchedFile) -> set[int]:
        return {
            line.target_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_added and line.value.strip()
        }

    repo = Repo(search_parent_directories=True)
    result = {
        Path(patched_file.path): parse_modified_lines(patched_file)
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
        repo_path = Path(repo.git_dir).parent.resolve()
        logger.error(
            f"could not find any git-modified lines in {repo_path}: Are the files committed?"  # noqa: E501
        )
    return result


def validate_repo_path() -> None:
    try:
        git.Repo(search_parent_directories=True)
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"Cannot detect repository in {Path().resolve()}")
        raise typer.Exit(1) from None  # no need for whole stack trace


def detect_base_branch(repo: Repo) -> str | None:
    all_branch_names = [branch.name for branch in repo.branches]
    match len(result := {"main", "master"}.intersection(all_branch_names)):
        case 1:
            return result
        case 2:
            error = (
                "both `main` and `master` branches found, can not tell which to use."
                "Use --base-branch <the branch to use>."
            )

        case _:
            error = "can not detect main/master branch. Use --base-branch <the branch to use>"
    raise RuntimeError(error)
