import requests  # type:ignore[import]
from git.repo import Repo
from loguru import logger  # noqa: TID251
from packaging.version import Version


def get_latest_ruff_version() -> Version:
    response = requests.get("https://pypi.org/pypi/ruff/json", timeout=5).json()
    return max(Version(version_string) for version_string in response["releases"])


def get_latest_tag() -> Version:
    repo = Repo(search_parent_directories=True)
    logger.info(repo.tags)
    return Version(
        sorted(repo.tags, key=lambda t: t.commit.committed_datetime)[-1].name
    )


latest_ruff_version = get_latest_ruff_version()
latest_riff_tag = get_latest_tag()

logger.info(f"{latest_ruff_version=}")
logger.info(f"{latest_riff_tag=}")

print(  # noqa: T201
    f"::set-output name=newer_ruff_version::{latest_ruff_version > Version(latest_riff_tag.base_version)}"
)
