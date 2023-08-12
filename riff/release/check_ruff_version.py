import os

import requests  # type:ignore[import]
from loguru import logger  # noqa: TID251
from packaging.version import Version


def set_output(key: str, value: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a") as fh:  # noqa: PTH123
        print(f"{key}={value}", file=fh)


def get_latest_version(project: str) -> Version:
    response = requests.get(f"https://pypi.org/pypi/{project}/json", timeout=5).json()
    return max(Version(version_string) for version_string in response["releases"])


ruff_version = get_latest_version("ruff")
riff_version = get_latest_version("riff")

logger.info(f"{ruff_version=}")
logger.info(f"{riff_version=}")

set_output("newer_ruff_version", str(ruff_version > Version(riff_version.base_version)))
