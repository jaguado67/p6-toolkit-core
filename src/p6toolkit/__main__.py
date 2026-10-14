"""Command line. Usage:
  python -m p6toolkit inspect <file.xer> [--project-id ID]
  python -m p6toolkit compare <before.xer> <after.xer> [--confirm-same-project]
  python -m p6toolkit hash-password            (prompts twice; prints a hash for .streamlit/secrets.toml)
"""
import argparse
import getpass
import json
from dataclasses import asdict
from pathlib import Path
from .xer import parse_xer_file
from .snapshot import build_snapshot, list_projects
from .network import inspect_network
from .compare import compare_snapshots


def main() -> None:
    p = argparse.ArgumentParser(description="P6 Toolkit Core — XER structural diagnostics")
    sub = p.add_subparsers(dest="command", required=True)
    one = sub.add_parser("inspect", help="Inspect an XER and its network topology")
    one.add_argument("xer", type=Path)
    one.add_argument("--project-id", default=None)
    two = sub.add_parser("compare", help="Compare two XER files of the same project")
    two.add_argument("before", type=Path)
    two.add_argument("after", type=Path)
    two.add_argument("--confirm-same-project", action="store_true",
                     help="Explicit confirmation when baseline and update have different project codes")
    sub.add_parser("hash-password", help="Create a password hash for the app login")
    args = p.parse_args()
    if args.command == "hash-password":
        from .auth import hash_password
        first = getpass.getpass("New password: ")
        if len(first) < 10:
            p.error("Use at least 10 characters")
        if getpass.getpass("Repeat password: ") != first:
            p.error("Passwords do not match")
        print(hash_password(first))
        return
    if args.command == "inspect":
        doc = parse_xer_file(args.xer)
        if args.project_id is None and len(list_projects(doc)) != 1:
            p.error("The file contains several projects; use --project-id")
        snapshot = build_snapshot(doc, args.project_id)
        result = {"project": snapshot.project_code,
                  "date_reference": snapshot.data_date,
                  "date_reference_source": snapshot.date_reference_source,
                  "network": asdict(inspect_network(snapshot))}
    else:
        a = build_snapshot(parse_xer_file(args.before))
        b = build_snapshot(parse_xer_file(args.after))
        result = asdict(compare_snapshots(a, b, confirm_same_project=args.confirm_same_project))
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
