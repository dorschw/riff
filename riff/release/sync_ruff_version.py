import subprocess
from pathlib import Path

import requests  # type:ignore[import]
from git.repo import Repo
from loguru import logger  # noqa: TID251
from packaging.version import Version

README_PATH = Path("README.md")
repo = Repo(search_parent_directories=True)


def get_latest_version(project: str) -> Version:
    response = requests.get(f"https://pypi.org/pypi/{project}/json", timeout=5).json()
    result = max(Version(version_string) for version_string in response["releases"])
    logger.info(f"latest {project} version is {result!s}")
    return result


def release(current_version: Version, target_version: Version) -> None:
    readme = README_PATH.read_text()

    current_version_str = str(current_version)
    target_version_str = str(target_version)

    if current_version_str not in readme:
        raise RuntimeError(f"can't find {current_version_str} in README.md")
    README_PATH.write_text(readme.replace(current_version_str, target_version_str))

    for command in (
        ("poetry", "add", f"ruff=={target_version_str}"),
        ("poetry", "version", target_version_str),
        ("git", "add", "poetry.lock", "pyproject.toml", "README.md"),
        ("git", "tag", f"v{target_version_str}"),
    ):
        subprocess.run(command, check=True)  # noqa: S603


def main() -> None:
    ruff_version = get_latest_version("ruff")
    riff_version = get_latest_version("riff")

    if ruff_version > riff_version:
        logger.info("ruff version is newer, creating a new riff version")
        release(current_version=riff_version, target_version=ruff_version)
    else:
        logger.info("ruff version is not newer, stopping.")


main()
