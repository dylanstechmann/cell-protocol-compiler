"""Compile a library protocol to JSON, including the markdown checklist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from protocolcompiler.compile import compile_protocol
from protocolcompiler.constraints import export_constraints
from protocolcompiler.library import LIBRARY
from protocolcompiler.schema import ProtocolError
from protocolcompiler.result import ResultRecordError, validate_result_record
from protocolcompiler.source_review import STATUS_INCONSISTENT, STATUS_STALE, audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Compile a published cell-culture checklist")
    parser.add_argument("protocol", choices=[*sorted(LIBRARY), "validate-result", "source-audit"])
    parser.add_argument("--compiled-protocol", help="compiled protocol JSON for validate-result")
    parser.add_argument("--result", help="source-linked result record JSON for validate-result")
    parser.add_argument("--out", help="new validation receipt JSON path for validate-result")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--markdown", action="store_true", help="print the checklist instead of JSON")
    group.add_argument("--json", action="store_true", help="print compiled protocol as JSON (default)")
    group.add_argument("--constraints", action="store_true",
                       help="print the versioned planner constraint export instead of the compiled checklist")
    args = parser.parse_args(argv)
    if args.protocol == "source-audit":
        # Recorded disagreements are a known, documented state (exit 0). A stale or inconsistent
        # ledger means an encoded parameter changed without its source being revisited (exit 1).
        report = audit()
        json.dump(report, sys.stdout, indent=2, allow_nan=False)
        sys.stdout.write("\n")
        return 1 if report["status"] in (STATUS_STALE, STATUS_INCONSISTENT) else 0
    if args.protocol == "validate-result":
        if not args.compiled_protocol or not args.result or not args.out:
            parser.error("validate-result requires --compiled-protocol, --result and --out")
        try:
            result = validate_result_record(args.compiled_protocol, args.result)
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, allow_nan=False)
                handle.write("\n")
        except (ResultRecordError, OSError) as exc:
            parser.error(str(exc))
        json.dump(result, sys.stdout, indent=2, allow_nan=False)
        sys.stdout.write("\n")
        return 0
    try:
        protocol = LIBRARY[args.protocol]()
        if args.constraints:
            json.dump(export_constraints(protocol), sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
        compiled = compile_protocol(protocol)
    except ProtocolError as exc:
        parser.error(str(exc))
    if args.markdown:
        sys.stdout.write(compiled["checklist_markdown"])
        return 0
    json.dump({k: v for k, v in compiled.items() if k != "checklist_markdown"}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
