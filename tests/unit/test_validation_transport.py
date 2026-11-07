import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/port"))
import source_commands


class ValidationTransportTests(unittest.TestCase):
    def test_file_backed_transport_and_exact_match(self):
        def decoder(args, **kwargs):
            self.assertNotIn("input", kwargs)
            self.assertEqual(kwargs["timeout"], 30)
            self.assertEqual(kwargs["stdin"].read(), "0000000000000000\n")
            kwargs["stderr"].write("0000000000000000\tNop\n")

        with patch.object(source_commands.subprocess, "run", side_effect=decoder):
            source_commands.validate_inventory(
                {"pgcs": [], "decodedCommands": {"0000000000000000": "Nop"}}
            )

    def test_spoofed_description_and_unknown_bits_rejected(self):
        for diagnostic in ["0000000000000000\tOther\n", "WARNING unknown\n", ""]:

            def decoder(args, **kwargs):
                kwargs["stderr"].write(diagnostic)

            with (
                self.subTest(diagnostic=diagnostic),
                patch.object(source_commands.subprocess, "run", side_effect=decoder),
            ):
                with self.assertRaises(ValueError):
                    source_commands.validate_inventory(
                        {"pgcs": [], "decodedCommands": {"0000000000000000": "Nop"}}
                    )
