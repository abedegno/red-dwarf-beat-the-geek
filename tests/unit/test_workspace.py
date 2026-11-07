from pathlib import Path
import tempfile
import unittest
from tools.owner.workspace import workspace_lock


class WorkspaceTests(unittest.TestCase):
    def test_concurrent_operations_fail_and_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with workspace_lock(workspace):
                with self.assertRaisesRegex(ValueError, "already in use"):
                    with workspace_lock(workspace):
                        pass
            with workspace_lock(workspace):
                pass
