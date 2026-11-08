#!/usr/bin/env python3
"""Reference solution: print the sum of the integers in the input file.

Usage: reference_solution.py [input_path]
Defaults to assets/input.txt next to this script.
"""

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    else:
        input_path = Path(__file__).parent / "assets" / "input.txt"
    numbers = [int(token) for token in input_path.read_text(encoding="utf-8").split()]
    print(sum(numbers))


if __name__ == "__main__":
    main()
