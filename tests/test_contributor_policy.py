import copy
from io import BytesIO, StringIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.check_contributors import ALLOWED_LOGINS, PolicyError, audit, list_pages, main


MEMBER = {"login": "antotototototo18", "type": "User"}


def make_commit():
    return {
        "sha": "a" * 40,
        "author": MEMBER.copy(),
        "committer": MEMBER.copy(),
        "commit": {
            "author": {"name": "Anthony Rascle", "email": "anthony@example.test"},
            "committer": {"name": "Anthony Rascle", "email": "anthony@example.test"},
            "message": "Update architecture",
        },
    }


class AttributionTests(unittest.TestCase):
    def test_group_members_are_accepted(self):
        for login in ALLOWED_LOGINS:
            with self.subTest(login=login):
                identity = {"login": login.upper(), "type": "User"}
                commit = make_commit()
                commit["author"] = identity
                commit["committer"] = identity
                self.assertEqual(audit([identity], [commit]), [])

    def test_bot_and_outsider_contributors_are_rejected(self):
        for identity in (
            {"login": "copilot", "type": "Bot"},
            {"login": "outsider", "type": "User"},
            {"type": "Anonymous", "email": "unknown@example.test"},
        ):
            with self.subTest(identity=identity):
                self.assertTrue(audit([identity], [make_commit()]))

    def test_pr_author_is_checked_before_contributors_cache_updates(self):
        for identity in (None, {"login": "copilot", "type": "Bot"}):
            commit = make_commit()
            commit["author"] = identity
            self.assertTrue(audit([MEMBER], [commit]))

    def test_agent_cannot_be_committer(self):
        commit = make_commit()
        commit["committer"] = {"login": "github-actions[bot]", "type": "Bot"}
        self.assertTrue(audit([MEMBER], [commit]))

    def test_github_web_committer_is_accepted_for_human_author(self):
        commit = make_commit()
        commit["committer"] = {"login": "web-flow", "type": "User"}
        commit["commit"]["committer"] = {
            "name": "GitHub", "email": "noreply@github.com"
        }
        self.assertEqual(audit([MEMBER], [commit]), [])
        commit["author"] = commit["committer"]
        self.assertTrue(audit([MEMBER], [commit]))

    def test_forged_web_committer_is_rejected(self):
        commit = make_commit()
        commit["committer"] = {"login": "web-flow", "type": "User"}
        self.assertTrue(audit([MEMBER], [commit]))

    def test_agent_signature_under_human_account_is_rejected(self):
        commit = make_commit()
        commit["commit"]["author"]["name"] = "Claude"
        self.assertTrue(audit([MEMBER], [commit]))

    def test_coauthors_must_belong_to_group(self):
        cases = (
            ("Colin <csb123d@users.noreply.github.com>", True),
            ("Colin <123+csb123d@users.noreply.github.com>", True),
            ("Anthony <anthony@example.test>", True),
            ("Claude <noreply@anthropic.com>", False),
            ("Someone <outside@example.test>", False),
            ("Malformed signature", False),
        )
        for signature, accepted in cases:
            with self.subTest(signature=signature):
                commit = make_commit()
                commit["commit"]["message"] += f"\n\nCo-authored-by: {signature}"
                self.assertEqual(not audit([MEMBER], [commit]), accepted)

    def test_history_is_checked_beyond_tip(self):
        bad_commit = copy.deepcopy(make_commit())
        bad_commit["author"] = None
        self.assertTrue(audit([MEMBER], [make_commit(), bad_commit]))

    def test_empty_results_do_not_pass(self):
        self.assertTrue(audit([], [make_commit()]))
        self.assertTrue(audit([MEMBER], []))


class Response(BytesIO):
    status = 200


class ApiTests(unittest.TestCase):
    @patch("scripts.check_contributors.urlopen")
    def test_all_pages_are_read(self, open_url):
        open_url.side_effect = [
            Response(json.dumps([MEMBER] * 100).encode()),
            Response(json.dumps([MEMBER]).encode()),
        ]
        items = list_pages("repos/owner/repo/contributors", "test-token", anon="true")
        self.assertEqual(len(items), 101)
        self.assertIn("page=2", open_url.call_args.args[0].full_url)

    @patch("scripts.check_contributors.urlopen")
    def test_api_errors_do_not_pass(self, open_url):
        open_url.side_effect = HTTPError("url", 403, "Forbidden", {}, None)
        with self.assertRaises(PolicyError):
            list_pages("repos/owner/repo/commits", "test-token")

    @patch("scripts.check_contributors.urlopen")
    def test_unexpected_payload_is_rejected(self, open_url):
        open_url.return_value = Response(b'{"message": "not a list"}')
        with self.assertRaises(PolicyError):
            list_pages("repos/owner/repo/commits", "test-token")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_credentials_do_not_skip_the_policy(self):
        with patch("sys.stderr", new_callable=StringIO):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
