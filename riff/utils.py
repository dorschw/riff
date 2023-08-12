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
        logger.error(
            f"could not find any git-modified lines in {repo_root}: Are the files committed?"  # noqa: E501
        )
    return result


def validate_repo_path() -> Path:
    try:
        return Path(git.Repo(search_parent_directories=True).git_dir).parent.resolve()
    except git.exc.InvalidGitRepositoryError:
        logger.error(f"Cannot detect repository in {Path().resolve()}")
        raise typer.Exit(1) from None  # no need for whole stack trace
