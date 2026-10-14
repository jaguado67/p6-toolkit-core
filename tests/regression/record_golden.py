"""Record expected results for a real file.

    py tests/regression/record_golden.py tests/regression/data/UP05.xer --data-date 2026-10-01T08:00
    py tests/regression/record_golden.py "tests/regression/data/QTS CDR1-DC7 260930DD.xlsx"

Writes <file>.golden.json with "validated_against_p6": false. Check every number against P6
(activity count, relationship count by type, open ends, constraints...) and only then set it to
true. Files in tests/regression/data are git-ignored: client schedules never enter the repository.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.regression.metrics import metrics_for  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("file", type=Path)
    p.add_argument("--data-date", help="Data Date confirmed in P6, ISO format (XER only)")
    p.add_argument("--force", action="store_true", help="Overwrite an existing golden file")
    a = p.parse_args()
    target = a.file.with_name(a.file.name + ".golden.json")
    if target.exists() and not a.force:
        p.error(f"{target.name} exists; use --force to overwrite (this resets validation)")
    golden = {"source": a.file.name, "data_date": a.data_date, "validated_against_p6": False,
              "metrics": metrics_for(a.file, a.data_date)}
    target.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {target}. Review the numbers against P6, then set validated_against_p6 to true.")


if __name__ == "__main__":
    main()
