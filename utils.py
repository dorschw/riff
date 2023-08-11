import json
import pprint
from pathlib import Path

from git.repo import Repo
from loguru import logger
from unidiff import PatchSet

from violation import Violation


def split_paths_by_max_len(
    paths: list[Path],
    max_length_sum: int = 4000,
) -> list[list[Path]]:
    """
    Splits a list of Path objects into sublists based on their total length.

    Args:
        paths (List[Path]): A list of Path objects.
        max_length_sum (int): The maximum total length of each sublist. Default is 4000.

    Returns:
        List[List[Path]]: A list of sublists, where each has a maximum total length.
    """
    result: list[list[Path]] = []
    current_list: list[Path] = []
    current_length_sum = 0

    for path in sorted(set(paths), key=lambda x: len(str(x))):
        path_length = len(str(path))
        if path_length >= max_length_sum:
            raise ValueError(f"Path is longer than {max_length_sum}: {path}")
        if current_length_sum + path_length <= max_length_sum:
            current_list.append(path)
            current_length_sum += path_length
        else:  # exceeded max length
            result.append(current_list)
            current_list = [path]
            current_length_sum = path_length
    if current_list:
        result.append(current_list)
    return result


def validate_paths_relative_to_repo(paths: list[Path], repo_path: Path) -> None:
    for path in paths:
        with logger.catch(
            ValueError,
            level="ERROR",
            message=f"{path} is not relative to {repo_path=}, may lead to false negatives",
            reraise=False,
        ):
            path.relative_to(repo_path)


def parse_ruff_output(ruff_result_raw: str) -> tuple[Violation, ...]:
    with logger.catch(json.JSONDecodeError, reraise=True):
        raw_violations = json.loads(ruff_result_raw)

    violations = tuple(map(Violation.parse, raw_violations))
    logger.info(f"Parsed {len(violations)} Ruff violations")
    return violations


def git_changed_lines(
    path: Path,
    base_branch: str,
) -> dict[Path, set[int]]:
    """Returns
    Dict[Path, Tuple[int]]: maps modified files, to the indices of the lines changed.
    """

    def parse_modified_lines(patched_file: PatchSet) -> set[int]:
        return {
            line.source_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_removed and line.value.strip()
        }

    repo = Repo(path, search_parent_directories=True)

    result = {
        Path(patch.file_path): parse_modified_lines(patch)
        for patch in PatchSet(
            repo.git.diff(
                "HEAD",
                base_branch,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            ),
        )
    }
    logger.debug(f"Modified lines:\n{pprint.pformat(result)}")
    return result
