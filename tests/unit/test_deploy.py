from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.owner.deploy import deploy_cloudflare, deployment_command


class DeployTests(unittest.TestCase):
    def test_arguments_are_separate_and_explicit(self):
        command = deployment_command(Path("/tmp/owner site"), "beat-the-geek")
        self.assertIn(str(Path("/tmp/owner site").resolve()), command)
        self.assertIn("--project-name", command)
        self.assertIn("--branch", command)
        with self.assertRaises(ValueError):
            deployment_command(Path("/tmp/site"), "--bad")

    def test_invalid_site_prevents_upload(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("tools.owner.deploy.subprocess.run") as run,
        ):
            with self.assertRaises((OSError, ValueError)):
                deploy_cloudflare(Path(tmp), "game")
            run.assert_not_called()

    def test_dry_run_does_not_authenticate_or_upload(self):
        with (
            patch(
                "tools.owner.deploy.validate_package",
                return_value={"fileCount": 3, "bytes": 123},
            ),
            patch("tools.owner.deploy.subprocess.run") as run,
        ):
            result = deploy_cloudflare(Path("/tmp/owner site"), "game", dry_run=True)
            self.assertEqual(
                result["command"], deployment_command(Path("/tmp/owner site"), "game")
            )
            run.assert_not_called()

    def test_account_selection_and_failed_upload_are_explicit(self):
        import os, subprocess

        with (
            patch(
                "tools.owner.deploy.validate_package",
                return_value={"fileCount": 3, "bytes": 123},
            ),
            patch.dict(os.environ, {}, clear=True),
            patch("tools.owner.deploy.subprocess.run") as run,
        ):
            with self.assertRaisesRegex(ValueError, "Select your account"):
                deploy_cloudflare(Path("/tmp/site"), "game")
            run.assert_not_called()
        with (
            patch(
                "tools.owner.deploy.validate_package",
                return_value={"fileCount": 3, "bytes": 123},
            ),
            patch("pathlib.Path.is_file", return_value=True),
            patch(
                "tools.owner.deploy.subprocess.run",
                return_value=subprocess.CompletedProcess([], 1),
            ) as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "local package is retained"):
                deploy_cloudflare(Path("/tmp/site"), "game", account_id="a" * 32)
            self.assertEqual(
                run.call_args.kwargs["env"]["CLOUDFLARE_ACCOUNT_ID"], "a" * 32
            )
            self.assertFalse(any("TOKEN" in arg for arg in run.call_args.args[0]))

    def test_deployment_explicitly_bypasses_workers_migration(self):
        self.assertIn("--force", deployment_command(Path("/tmp/site"), "game"))
