import subprocess
from pathlib import Path

import toml
from git.repo import Repo
from loguru import logger  # noqa: TID251
from packaging.version import Version

README_PATH = Path("README.md")
repo = Repo(search_parent_directories=True)


def release(
    current_version: Version,
    target_version: Version,
) -> None:
    current_version_str = str(current_version)
    target_version_str = f"{target_version!s}.0"

    if current_version_str not in (readme := README_PATH.read_text()):
        raise RuntimeError(f"can't find {current_version_str} in README.md")
    README_PATH.write_text(readme.replace(current_version_str, target_version_str))

    for command in (
        ("poetry", "version", target_version_str),
        ("git", "add", "README.md"),
        ("git", "tag", f"v{target_version_str}"),
        ("git", "push"),
    ):
        subprocess.run(command, check=True)  # noqa: S603


class PyProject:
    def __init__(self) -> None:
        self.body = toml.load("pyproject.toml")

    def get_dependency_version(self, dependency: str) -> Version:
        raw = self.body["tool"]["poetry"]["dependencies"][dependency]
        result = raw

        for prefix in (">", "<", "==", "=", "^", "~"):
            result = result.removeprefix(prefix)

        if not result[0].isdigit():
            raise RuntimeError(f"failed parsing {raw=}, got {result}")

        return Version(result)

    @property
    def version(self) -> Version:
        return Version(self.body["tool"]["poetry"]["version"])


def main() -> None:
    pyproject = PyProject()

    riff_version = pyproject.version
    ruff_depencency_version = pyproject.get_dependency_version("ruff")

    logger.debug(f"{riff_version=}")
    logger.debug(f"{ruff_depencency_version=}")

    if ruff_depencency_version > Version(riff_version.base_version):
        logger.info("ruff dependency is newer, releasing a new Riff version")
        release(
            current_version=riff_version,
            target_version=ruff_depencency_version,
        )
    else:
        logger.info("Ruff dependency is not newer than Riff, exiting")


if __name__ == "__main__":
    main()
