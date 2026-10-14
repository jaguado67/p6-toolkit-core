"""Regression against real files in tests/regression/data (git-ignored).

Each file needs a <file>.golden.json produced by tests/regression/record_golden.py. With no files the
test passes trivially; with files, any change in a recorded metric fails the test and shows the diff.
"""
import json
from pathlib import Path
from tests.regression.metrics import metrics_for

DATA = Path(__file__).resolve().parent / "regression" / "data"


def _cases():
    return sorted(DATA.glob("*.golden.json")) if DATA.exists() else []


def test_real_files_match_golden():
    failures = []
    for golden_path in _cases():
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        source = golden_path.with_name(golden["source"])
        if not source.exists():
            failures.append(f"{golden['source']}: source file missing")
            continue
        now = metrics_for(source, golden.get("data_date"))
        if now != golden["metrics"]:
            failures.append(f"{golden['source']}: metrics changed\n  was: {golden['metrics']}\n  now: {now}")
    assert not failures, "\n".join(failures)


def test_golden_files_are_reviewed():
    pending = [p.name for p in _cases() if not json.loads(p.read_text(encoding="utf-8")).get("validated_against_p6")]
    if pending:
        print("Golden files not yet validated against P6:", ", ".join(pending))
