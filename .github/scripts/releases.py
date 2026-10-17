"""Validate InkStack releases and check whether their GitHub channel pointers can advance."""

import argparse
import json
import re
import sys

_VERSION_RE = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+(?:-(?:alpha(?:\.[0-9]+){0,2}"
    r"|beta(?:\.[0-9]+)?))?$"
)


def is_valid_release_version(version: str) -> bool:
    return _VERSION_RE.fullmatch(version) is not None


def is_valid_stable_release_version(version: str) -> bool:
    return is_valid_release_version(version) and "-" not in version


def _version_key(version: str) -> tuple[tuple[int, ...], int, tuple[int, ...]]:
    base, _, prerelease = version.partition("-")
    channel, _, suffix = prerelease.partition(".")
    return (
        tuple(int(part) for part in base.split(".")),
        {"alpha": 0, "beta": 1, "": 2}[channel],
        tuple(int(part) for part in suffix.split(".")) if suffix else (),
    )


def should_update_version(version: str, current_version: str) -> bool:
    """Compare version strings; replace an unreadable current version."""
    if not is_valid_release_version(version):
        raise ValueError(f"invalid release version: {version}")
    if not is_valid_release_version(current_version):
        # Replace an unreadable pointer so publishing can repair it.
        return True

    return _version_key(version) > _version_key(current_version)


def should_make_latest(version: str, latest: dict) -> bool:
    if not is_valid_stable_release_version(version):
        raise ValueError(f"expected a stable release version: {version}")
    tag = latest.get("tag_name", "")
    current = tag.removeprefix("rust-v") if isinstance(tag, str) else ""
    if (
        not isinstance(tag, str)
        or not tag.startswith("rust-v")
        or not is_valid_stable_release_version(current)
        or latest.get("draft") is not False
        or latest.get("prerelease") is not False
    ):
        raise ValueError("Cannot determine the current GitHub latest stable release")
    # An equal version must be able to finish a partially completed publication.
    return version == current or should_update_version(version, current)


_HTTP_STATUS_RE = re.compile(r"^HTTP(?:/[\d.]+)?\s+(\d{3})\b", re.IGNORECASE)


def should_make_latest_from_response(version: str, response: str) -> bool:
    """Decide latest-release eligibility from a raw `gh api --include` response.

    The response contains a status line, headers, and (when present) the
    JSON body of the repository's `/releases/latest` endpoint. Only a 404
    from that endpoint means the repository has no latest stable release:
    that is the genuine first-release condition, including a repository
    whose only published releases are dependency releases such as
    `rusty-v8-v*` (GitHub excludes prereleases from the endpoint, and a
    non-application release occupying the slot equally proves that no
    previous application release exists). Every other non-200 status —
    authentication failures, rate limits, and server errors — is an error
    that must never be mistaken for evidence of a first release.
    """
    if not is_valid_stable_release_version(version):
        raise ValueError(f"expected a stable release version: {version}")
    status = None
    body_start = None
    offset = 0
    for line in response.splitlines(keepends=True):
        if status is None:
            match = _HTTP_STATUS_RE.match(line.strip())
            if match:
                status = int(match.group(1))
            offset += len(line)
            continue
        offset += len(line)
        if not line.strip():
            body_start = offset
            break
    if status is None:
        raise ValueError("No HTTP status in the GitHub latest-release response")

    if status == 404:
        return True
    if status != 200:
        raise ValueError(
            f"GitHub latest-release request failed with status {status}"
        )

    body = response[body_start:] if body_start is not None else ""
    try:
        latest = json.loads(body)
    except json.JSONDecodeError as error:
        raise ValueError("GitHub latest-release response was not valid JSON") from error
    if not isinstance(latest, dict):
        raise ValueError("GitHub latest-release response was not a JSON object")
    tag = latest.get("tag_name")
    if not isinstance(tag, str) or not tag:
        raise ValueError("GitHub latest-release response had no tag_name")
    if not tag.startswith("rust-v"):
        # A dependency release (for example rusty-v8-v*) occupying the
        # latest slot proves no application release has ever been marked
        # latest; the first stable application release may take the slot.
        return True
    return should_make_latest(version, latest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument(
        "--check-github",
        choices=("latest", "latest-response", "canary"),
        help=(
            "Compare with the latest release JSON or canary Cargo.toml on stdin,"
            " or with a raw `gh api --include` latest-release response."
        ),
    )
    args = parser.parse_args()
    if args.check_github is None:
        raise SystemExit(0 if is_valid_release_version(args.version) else 1)
    if args.check_github == "latest":
        update = should_make_latest(args.version, json.load(sys.stdin))
    elif args.check_github == "latest-response":
        update = should_make_latest_from_response(args.version, sys.stdin.read())
    else:
        import tomllib

        try:
            current_version = tomllib.loads(sys.stdin.read())["workspace"]["package"][
                "version"
            ]
        except (tomllib.TOMLDecodeError, KeyError, TypeError):
            current_version = ""
        if not isinstance(current_version, str):
            current_version = ""
        update = should_update_version(args.version, current_version)
    print(str(update).lower())
