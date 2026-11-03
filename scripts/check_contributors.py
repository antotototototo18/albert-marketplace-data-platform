"""Verify declared GitHub attribution against the group's human accounts."""

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ALLOWED_LOGINS = frozenset(
    login.casefold()
    for login in (
        "antotototototo18",
        "antorabo75",
        "csb123d",
        "lsantus-mines",
        "BenjaminAHS",
    )
)
AGENT_MARKER = re.compile(
    r"\b(codex|claude|copilot|chatgpt|openai|anthropic|cursor|devin|gemini)\b|\[bot\]",
    re.IGNORECASE,
)
COAUTHOR = re.compile(r"co-authored-by:\s*(.*?)\s*<([^<>]+)>\s*", re.IGNORECASE)


class PolicyError(Exception):
    """The attribution policy could not be verified."""


def is_member(identity):
    return (
        isinstance(identity, dict)
        and identity.get("type") == "User"
        and str(identity.get("login", "")).casefold() in ALLOWED_LOGINS
    )


def is_github_committer(identity, git_identity):
    # GitHub signs web-created commits for the human author (including the seed).
    return (
        identity == {"login": "web-flow", "type": "User"}
        and git_identity.get("name") == "GitHub"
        and git_identity.get("email") == "noreply@github.com"
    )


def audit(contributors, commits):
    errors = []
    if not contributors or not commits:
        return ["Contributor and commit lists must both be non-empty."]

    for contributor in contributors:
        if not is_member(contributor):
            errors.append(
                f"Unapproved contributor: {contributor.get('login', 'anonymous')}"
            )

    trusted_emails = set()
    for commit in commits:
        if is_member(commit.get("author")):
            email = commit["commit"]["author"].get("email", "").casefold()
            if email:
                trusted_emails.add(email)

    for commit in commits:
        sha = commit["sha"][:12]
        details = commit["commit"]
        if not is_member(commit.get("author")):
            errors.append(f"{sha}: author is not a linked group account.")

        committer = commit.get("committer") or {}
        committer_identity = {
            "login": committer.get("login"),
            "type": committer.get("type"),
        }
        if not is_member(committer) and not is_github_committer(
            committer_identity, details["committer"]
        ):
            errors.append(f"{sha}: committer is not a group account or GitHub web-flow.")

        for role in ("author", "committer"):
            identity = details[role]
            if AGENT_MARKER.search(
                f"{identity.get('name', '')} {identity.get('email', '')}"
            ):
                errors.append(f"{sha}: agent signature in {role} identity.")

        for line in details["message"].splitlines():
            if not line.strip().casefold().startswith("co-authored-by:"):
                continue
            match = COAUTHOR.fullmatch(line.strip())
            if not match or AGENT_MARKER.search(line):
                errors.append(f"{sha}: invalid or agent co-author signature.")
                continue
            email = match[2].casefold()
            noreply = re.fullmatch(r"(?:\d+\+)?([^@]+)@users\.noreply\.github\.com", email)
            if email not in trusted_emails and not (
                noreply and noreply[1] in ALLOWED_LOGINS
            ):
                errors.append(f"{sha}: co-author email is not linked to the group.")
    return errors


def list_pages(endpoint, token, **query):
    results = []
    page = 1
    while True:
        url = f"https://api.github.com/{endpoint}?" + urlencode(
            {**query, "per_page": 100, "page": page}
        )
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "group-contributor-policy",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise PolicyError(f"GitHub returned HTTP {response.status}.")
                items = json.load(response)
        except HTTPError as error:
            raise PolicyError(f"GitHub returned HTTP {error.code}.") from error
        except (URLError, TimeoutError, ValueError) as error:
            raise PolicyError("Could not read the GitHub API response.") from error
        if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
            raise PolicyError("GitHub returned an unexpected response format.")
        results.extend(items)
        if len(items) < 100:
            return results
        page += 1


def main():
    token = os.environ.get("GH_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("POLICY_REF", "")
    if not token or not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        print("Missing GitHub token or valid repository.", file=sys.stderr)
        return 1
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        print("POLICY_REF must be the full commit SHA being checked.", file=sys.stderr)
        return 1
    try:
        contributors = list_pages(
            f"repos/{repository}/contributors", token, anon="true"
        )
        commits = list_pages(f"repos/{repository}/commits", token, sha=ref)
        errors = audit(contributors, commits)
    except (PolicyError, KeyError, TypeError, AttributeError) as error:
        print(f"Attribution verification failed: {error}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(
        f"Attribution verified: {len(contributors)} contributor(s), "
        f"{len(commits)} commit(s); only group accounts are authors."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
