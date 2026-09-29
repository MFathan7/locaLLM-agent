"""Executable entry point when invoked via python -m locallm."""

import sys
from locallm.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
