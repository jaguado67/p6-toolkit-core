import pytest
from p6toolkit import parse_xer_bytes, parse_xer_file, build_snapshot
from p6toolkit.xer import XERParseError
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "BL_DEMO.xer"

def test_parse_tables_and_sha256():
    doc = parse_xer_file(EXAMPLE)
    assert doc.rows("PROJECT")[0]["proj_short_name"] == "DEMO"
    assert len(doc.rows("TASK")) == 3
    assert len(doc.rows("TASKPRED")) == 2
    assert len(doc.sha256) == 64
    assert doc.encoding == "utf-8-sig"

def test_snapshot_activity_and_relation_ids(baseline):
    assert baseline.by_code()["A200"].task_id == "101"
    assert baseline.relationships[0].predecessor_id == "100"
    assert baseline.relationships[0].kind == "FS"
    assert baseline.by_code()["A100"].total_float_hours == 20

def test_invalid_xer_is_not_silently_accepted():
    with pytest.raises(XERParseError):
        parse_xer_bytes(b"not-a-xer")
    malformed = b"ERMHDR\t26\n%T\tTASK\n%F\ttask_id\ttask_code\n%R\t100\n%E\n"
    with pytest.raises(XERParseError, match="expects 2 fields"):
        parse_xer_bytes(malformed)

def test_cp1252_and_multi_project():
    text = ("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\tproj_name\n"
            "%R\t1\tPROJ1\tConstrucción\n%R\t2\tPROJ2\tProyecto\n"
            "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\t\n"
            "%R\t1\t1\tA1\t\n%R\t2\t2\tB1\t\n%E\n")
    # The terminal delimiter creates a fourth field with an empty header. Fix it for test fixture.
    text = text.replace("task_code\t\n", "task_code\n").replace("A1\t\n", "A1\n").replace("B1\t\n", "B1\n")
    doc = parse_xer_bytes(text.encode("cp1252"))
    assert doc.encoding == "cp1252"
    with pytest.raises(ValueError, match="several projects"):
        build_snapshot(doc)
    assert build_snapshot(doc, "1").project_name == "Construcción"
