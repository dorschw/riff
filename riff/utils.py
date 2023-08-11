import json
import pprint
from pathlib import Path

from git.repo import Repo
from loguru import logger
from unidiff import PatchSet

from riff.violation import Violation


def parse_ruff_output(ruff_result_raw: str) -> tuple[Violation, ...]:
    with logger.catch(json.JSONDecodeError, reraise=True):
        raw_violations = json.loads(ruff_result_raw)

    violations = tuple(map(Violation.parse, raw_violations))
    logger.info(f"Parsed {len(violations)} Ruff violations")
    return violations


def git_changed_lines(
    repo_path: Path,
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

    repo = Repo(repo_path, search_parent_directories=True)
    result = {
        Path(patch.path): parse_modified_lines(patch)
        for patch in PatchSet(
            repo.git.diff(
                "HEAD",
                base_branch,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
                merge_base=True,
            ),
        )
    }
    logger.debug(f"Modified lines:\n{pprint.pformat(result,compact=True)}")
    return result
