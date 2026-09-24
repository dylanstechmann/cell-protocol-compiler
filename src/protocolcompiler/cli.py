"""Compile a library protocol to JSON, including the markdown checklist."""

from __future__ import annotations

import argparse
import json
import sys

from protocolcompiler.compile import compile_protocol
from protocolcompiler.library import LIBRARY


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compile a published cell-culture checklist")
    parser.add_argument("protocol", choices=sorted(LIBRARY))
    parser.add_argument("--markdown", action="store_true", help="print the checklist instead of JSON")
    args = parser.parse_args(argv)
    compiled = compile_protocol(LIBRARY[args.protocol]())
    if args.markdown:
        sys.stdout.write(compiled["checklist_markdown"])
        return 0
    json.dump({k: v for k, v in compiled.items() if k != "checklist_markdown"}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
