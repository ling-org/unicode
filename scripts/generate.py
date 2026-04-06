# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

"""Generate Cangjie lookup tables for unicode-case and unicode-width.

Usage:
    uv run generate.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import gen_case
import gen_width
from common import get_cache_dir


def main():
    output_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

    print(f"Cache directory: {get_cache_dir()}")
    gen_case.generate(output_dir)
    gen_width.generate(output_dir)
    print("\nDone.")


if __name__ == "__main__":
    main()
