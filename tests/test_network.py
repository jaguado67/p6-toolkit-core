from dataclasses import replace
from p6toolkit import inspect_network
from p6toolkit.snapshot import Relationship

def test_linear_network(baseline):
    report = inspect_network(baseline)
    assert report.start_activities == ("A100",)
    assert report.finish_activities == ("A300",)
    assert len(report.weak_components) == 1
    assert report.cyclic_sccs == ()

def test_mixed_relationship_cycle_is_reported_as_structural(baseline):
    edge = Relationship("3", "102", "100", "SS", 0.0, {})
    changed = replace(baseline, relationships=baseline.relationships + (edge,))
    report = inspect_network(changed)
    assert report.cyclic_sccs == (("A100", "A200", "A300"),)
    assert any("temporal feasibility" in x for x in report.warnings)

def test_isolated_activity_is_visible(baseline):
    changed = replace(baseline, relationships=())
    report = inspect_network(changed)
    assert len(report.weak_components) == 3
    assert report.isolated_activities == ("A100", "A200", "A300")

def test_external_successor_not_silently_lost():
    from p6toolkit import parse_xer_bytes, build_snapshot
    text = ("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\n"
            "%R\t1\tMAIN\n%R\t2\tOTHER\n"
            "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\n"
            "%R\t1\t1\tA1\n%R\t2\t2\tB1\n"
            "%T\tTASKPRED\n%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\n"
            "%R\t9\t2\t1\tPR_FS\n%E\n")
    snap = build_snapshot(parse_xer_bytes(text.encode()), "1")
    assert len(snap.external_links) == 1
    assert snap.relationships == ()
