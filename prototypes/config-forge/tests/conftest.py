import pathlib
import sys

# config-forge modules import each other top-level (from algebra import ...)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
