""""Module to add update functionality to the program.
    Checking github for a newer release."""
import requests
import json
import logging
from dataclasses import dataclass
from .config import *


logger = logging.getLogger("backend")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse the version string.

    Args:
        version (str): The version string to parse.

    Returns:
        tuple[int, int, int]: Returns the major, minor, patch for the version.
    """
    version = version.replace("v", "")
    major, minor, patch = version.split(".")
    return major, minor, patch


@dataclass
class Version:
    """Class to hold the version information."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def number(self) -> int:
        return self.major * 100 + self.minor * 10 + self.patch

    def is_newer(self, __o: 'Version') -> bool:
        return self > __o

    def __eq__(self, __o: 'Version') -> bool:
        return self.number == __o.number

    def __lt__(self, __o: 'Version') -> bool:
        return self.number < __o.number

    def __gt__(self, __o: 'Version') -> bool:
        return self.number > __o.number

    def __le__(self, __o: 'Version') -> bool:
        return self.number <= __o.number

    def __ge__(self, __o: 'Version') -> bool:
        return self.number >= __o.number

    @staticmethod
    def from_string(version: str) -> 'Version':
        """Method to create a version object from a string."""
        major, minor, patch = parse_version(version)
        return Version(int(major), int(minor), int(patch))


CURRENT_VERSION = Version.from_string(PROGRAM_VERSION)


@dataclass
class Author:
    """Class to hold the author information."""

    login: str
    id: int
    node_id: str
    avatar_url: str
    gravatar_id: str
    url: str
    html_url: str
    followers_url: str
    following_url: str
    gists_url: str
    starred_url: str
    subscriptions_url: str
    organizations_url: str
    repos_url: str
    events_url: str
    received_events_url: str
    type: str
    site_admin: bool

    def json(self) -> str:
        """Return the release as a json string."""
        return json.dumps(self.__dict__, indent=4)

    @staticmethod
    def from_dict(data: dict) -> 'Author':
        """Method to create an author object from a dictionary."""
        return Author(**data)


@dataclass
class Asset:
    """Class to hold the asset information."""

    url: str
    id: int
    node_id: str
    name: str
    label: str
    content_type: str
    state: str
    size: int
    download_count: int
    created_at: str
    updated_at: str
    browser_download_url: str

    def json(self) -> str:
        """Return the release as a json string."""
        return json.dumps(self.__dict__, indent=4)

    @staticmethod
    def from_dict(data: dict) -> 'Asset':
        """Create a new Asset object from a dictionary."""
        if "uploader" in data:
            del data["uploader"]
        return Asset(**data)


@dataclass
class ReleaseResponse:
    """Class to hold the release information."""

    url: str
    assets_url: str
    html_url: str
    id: int
    author: Author
    node_id: str
    tag_name: str
    target_commitish: str
    name: str
    draft: bool
    prerelease: bool
    created_at: str
    published_at: str
    assets: list[Asset]
    tarball_url: str
    zipball_url: str
    body: str

    @property
    def version(self) -> str:
        """Return the version of the release."""
        return self.tag_name.replace("v", "")

    def json(self) -> str:
        """Return the release as a json string."""
        x = {
            "url": self.url,
            "assets_url": self.assets_url,
            "html_url": self.html_url,
            "id": self.id,
            "author": json.loads(self.author.json()),
            "node_id": self.node_id,
            "tag_name": self.tag_name,
            "target_commitish": self.target_commitish,
            "name": self.name,
            "draft": self.draft,
            "prerelease": self.prerelease,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "assets": [json.loads(asset.json()) for asset in self.assets],
            "tarball_url": self.tarball_url,
            "zipball_url": self.zipball_url,
            "body": self.body,
        }
        return json.dumps(x, indent=4)

    @staticmethod
    def from_json(json_data: dict) -> 'ReleaseResponse':
        """Method to create a ReleaseResponse object from a json object."""
        return ReleaseResponse(
            url=json_data["url"],
            assets_url=json_data["assets_url"],
            html_url=json_data["html_url"],
            id=json_data["id"],
            author=Author.from_dict(json_data["author"]),
            node_id=json_data["node_id"],
            tag_name=json_data["tag_name"],
            target_commitish=json_data["target_commitish"],
            name=json_data["name"],
            draft=json_data["draft"],
            prerelease=json_data["prerelease"],
            created_at=json_data["created_at"],
            published_at=json_data["published_at"],
            assets=[Asset.from_dict(asset) for asset in json_data["assets"]],
            tarball_url=json_data["tarball_url"],
            zipball_url=json_data["zipball_url"],
            body=json_data["body"],
        )


def get_latest_release() -> ReleaseResponse:
    """Get the latest release from the github API."""
    logger.debug("Getting latest release from Github.")
    response = requests.get(GITHUB_LATEST_RELEASE_ENDPOINT)
    response.raise_for_status()
    return ReleaseResponse.from_json(json.loads(response.text))


def check_for_updates() -> tuple[bool, str, str]:
    """Checks for newer releases. Returns (True, version, url) if a newer."""
    try:
        latest_release = get_latest_release()
        # logger.debug(f"Latest release:\n{latest_release.json()}\n")
        if not Version.from_string(latest_release.version).is_newer(CURRENT_VERSION):
            logger.info("No new release available.")
            return False, "", ""

        logger.info(f"New release available: {latest_release.version}")

        return True, latest_release.version, latest_release.html_url
    except Exception as e:
        logger.exception("Error checking for updates.")
        return False, "", ""