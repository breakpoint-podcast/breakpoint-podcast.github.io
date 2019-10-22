"""Generate episode items from *releases* on GitHub."""

import os
import pathlib
import re

import holocron
import isodate
import requests


# Setting custom GitHub token may help to get over GitHub API rate limits. At
# the time of this writing, non authorized user can make only 60 HTTP requests
# per hour, while authorized - 5000.
_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def process(app, stream, *, repository, enclosure):
    yield from stream
    yield from _releases_to_episodes(
        _iterate_over_releases(repository), app.metadata["url"], enclosure
    )


def _iterate_over_releases(repo):
    """Yield GitHub Releases for a given repo."""

    session = requests.Session()
    session.headers["Accept"] = "application/vnd.github.v3+json"

    if _GITHUB_TOKEN:
        session.headers["Authorization"] = f"token {_GITHUB_TOKEN}"

    endpoint = f"https://api.github.com/repos/{repo}/releases"

    while endpoint:
        response = session.get(endpoint, params={"per_page": "50"})
        response.raise_for_status()
        endpoint = response.links.get("next")

        for release in response.json():
            if release["draft"] or release["prerelease"]:
                continue
            yield release


def _releases_to_episodes(releases, siteurl, enclosure_pattern):
    """Yield Holocron's WebSiteItem-s created from GitHub's Releases."""

    for release in releases:
        enclosure = next(
            filter(
                # Normally we have only 1 uploaded mp3 for a release.
                # Nevertheless, we want to be overprotective here and only
                # look for the mp3 with the expected name.
                lambda asset: asset["name"] == enclosure_pattern.format(**release),
                release["assets"],
            )
        )

        # Releases on GitHub may lack some necessary information to set in
        # the podcast feed or show on the website. Thus, we need some
        # mechanism to store extra information for an episode. The approach
        # we're taking below is to parse release's body and look for special
        # comments inside.
        extra = {
            match.group(1): match.group(2)
            for match in re.finditer(
                r'<!--\s*meta:\s*(\w+)\s*=\s*"(.+?)"\s*-->', release["body"]
            )
        }

        yield holocron.WebSiteItem(
            {
                "source": pathlib.Path("episode://", release["tag_name"]),
                "destination": pathlib.Path(
                    "episodes", release["tag_name"], "index.markdown"
                ),
                "name": release["name"],
                "content": release["body"],
                "episode_number": release["tag_name"],
                "created_at": isodate.parse_datetime(release["published_at"]),
                "published_at": isodate.parse_datetime(release["published_at"]),
                "enclosure_type": enclosure["content_type"],
                "enclosure_url": enclosure["browser_download_url"],
                # FIXME: Due to the bug in python-feedgen, the library Holocron
                # uses underneath to produce a feed, we need to pass string
                # as enclosure.length, not int.
                "enclosure_size": str(enclosure["size"]),
                "baseurl": siteurl,
                # FIXME: Currently Holocron's feed processor internally relies
                # on this property to sort received items. However, Holocron
                # tries to be as general as possible, and to be more like a
                # framework for building static sites, and so it plans to relax
                # dependencies on attribute names. Once such dependency is
                # relaxed, we can remove this duplicated property.
                "published": isodate.parse_datetime(release["published_at"]),
            },
            **extra,
        )
