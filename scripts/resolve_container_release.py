#!/usr/bin/env python3
"""Resolve a public GHCR development or stable tag to a multiarch index."""

import argparse
import json
import re
import sys
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen


REGISTRY = "https://ghcr.io"
SEMVER = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
INDEX_TYPES = (
    "application/vnd.oci.image.index.v1+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json"
)


def get_json(url, headers=None):
    with urlopen(Request(url, headers=headers or {}), timeout=30) as response:
        return json.load(response), response.headers


def resolve(repository, *, use_main=False, allow_unprefixed=False):
    query = urlencode({"service": "ghcr.io", "scope": f"repository:{repository}:pull"})
    token, _ = get_json(f"{REGISTRY}/token?{query}")
    auth = {"Authorization": f"Bearer {token['token']}"}
    tag = "main" if use_main else stable_tag(repository, auth, allow_unprefixed)
    return image_reference(repository, tag, auth)


def stable_tag(repository, auth, allow_unprefixed):
    stable = re.compile(("v?" if allow_unprefixed else "v") + SEMVER)
    path = f"/v2/{repository}/tags/list"
    url = f"{REGISTRY}{path}?n=100"
    seen = set()
    releases = []
    while url:
        if url in seen:
            raise ValueError("Repeated registry pagination link")
        seen.add(url)
        page, headers = get_json(url, auth)
        for tag in page["tags"] or []:
            match = stable.fullmatch(tag)
            if match:
                releases.append((tuple(map(int, match.groups())), tag))

        next_link = re.search(r'<([^>]+)>\s*;\s*rel="?next"?', headers.get("Link", ""))
        url = urljoin(url, next_link[1]) if next_link else ""
        if url:
            next_url = urlsplit(url)
            if (next_url.scheme, next_url.netloc, next_url.path) != ("https", "ghcr.io", path):
                raise ValueError("Unexpected registry pagination link")

    if not releases:
        raise ValueError("no published stable version tag")
    return max(releases)[1]


def image_reference(repository, tag, auth):
    index, headers = get_json(
        f"{REGISTRY}/v2/{repository}/manifests/{tag}",
        {**auth, "Accept": INDEX_TYPES},
    )
    platforms = {
        (descriptor.get("platform", {}).get("os"),
         descriptor.get("platform", {}).get("architecture"))
        for descriptor in index.get("manifests", [])
    }
    if not {("linux", "amd64"), ("linux", "arm64")} <= platforms:
        raise ValueError(f"{tag} does not include Linux AMD64 and ARM64")
    digest = headers.get("Docker-Content-Digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError(f"{tag} has no valid manifest digest")
    return f"ghcr.io/{repository}:{tag}@{digest}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository")
    parser.add_argument("--main", action="store_true")
    parser.add_argument("--allow-unprefixed", action="store_true")
    args = parser.parse_args()
    try:
        print(resolve(args.repository, use_main=args.main, allow_unprefixed=args.allow_unprefixed))
    except (OSError, ValueError, KeyError) as error:
        sys.exit(f"Cannot resolve a container image for {args.repository}: {error}")
