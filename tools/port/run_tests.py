"""Run the owner integration converter suite (requires imported DVD data)."""
import sys,unittest
from pathlib import Path
if __name__=='__main__':
 root=Path(__file__).resolve().parents[2]
 suite=unittest.defaultTestLoader.discover(str(root/'tests/port'))
 sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
