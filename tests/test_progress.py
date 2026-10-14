from datetime import datetime
from p6toolkit import parse_xer_bytes, build_snapshot
from p6toolkit.progress import validate_progress, parse_xer_date

XER = ("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\tlast_recalc_date\n%R\t1\tDEMO\t2026-10-01 08:00\n"
       "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\ttask_name\tstatus_code\ttask_type\tremain_drtn_hr_cnt"
       "\tact_start_date\tact_end_date\tearly_start_date\tearly_end_date\n"
       "%R\t1\t1\tA\tDone\tTK_Complete\tTT_Task\t0\t2026-09-01 08:00\t2026-09-10 17:00\t\t\n"
       "%R\t2\t1\tB\tStarted early\tTK_Active\tTT_Task\t40\t2026-09-05 08:00\t\t2026-10-01 08:00\t2026-10-08 17:00\n"
       "%R\t3\t1\tC\tFuture actual\tTK_Active\tTT_Task\t8\t2026-10-03 08:00\t\t2026-10-03 08:00\t2026-10-05 17:00\n"
       "%R\t4\t1\tD\tStale forecast\tTK_NotStart\tTT_Task\t16\t\t\t2026-09-20 08:00\t2026-09-22 17:00\n"
       "%R\t5\t1\tE\tBad complete\tTK_Complete\tTT_Task\t8\t2026-09-01 08:00\t\t\t\n"
       "%R\t6\t1\tM\tMilestone\tTK_Complete\tTT_Mile\t0\t2026-09-01 08:00\t\t\t\n"
       "%R\t7\t1\tF\tWaiting\tTK_NotStart\tTT_Task\t8\t\t\t2026-10-09 08:00\t2026-10-09 17:00\n"
       "%R\t8\t1\tN\tFinish ms\tTK_Complete\tTT_FinMile\t0\t\t2026-09-02 17:00\t\t\n"
       "%R\t9\t1\tG\tAfter ms\tTK_Complete\tTT_Task\t0\t2026-09-03 08:00\t2026-09-04 17:00\t\t\n"
       "%T\tTASKPRED\n%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n"
       "%R\t1\t2\t1\tPR_FS\t0\n"       # A done 09-10, B started 09-05 -> OOS (before)
       "%R\t2\t7\t2\tPR_FS\t0\n"       # B not finished, F not started -> fine
       "%R\t3\t3\t4\tPR_SS\t0\n"       # D not started, C started -> OOS
       "%R\t4\t3\t7\tPR_FS\t-8\n"      # F not finished, C started, negative lag -> P09
       "%R\t5\t9\t8\tPR_SS\t0\n"       # finish milestone done 09-02, G started 09-03 -> fine
       "%R\t6\t9\t1\tPR_FS\t0\n"       # A done 09-10 17:00, G started 09-03 -> OOS
       "%E\n")


def report():
    return validate_progress(build_snapshot(parse_xer_bytes(XER.encode())), datetime(2026, 10, 1, 8, 0))


def ids(rep, cid):
    return sorted(f.activity_id for f in rep.findings if f.check_id == cid)


def test_dates_parse():
    assert parse_xer_date("2026-10-01 08:00") == datetime(2026, 10, 1, 8, 0)
    assert parse_xer_date("") is None and parse_xer_date("01/10/2026") is None


def test_actuals_after_data_date():
    rep = report()
    assert ids(rep, "P01") == ["C"]
    assert ids(rep, "P02") == []


def test_forecast_before_data_date():
    rep = report()
    assert ids(rep, "P03") == ["D"]
    assert ids(rep, "P04") == ["D"]


def test_status_consistency_and_milestone_exception():
    rep = report()
    assert ids(rep, "P05") == ["E"]       # milestone M with only actual start is valid
    assert ids(rep, "P07") == ["E"]


def test_out_of_sequence_per_type():
    rep = report()
    assert ids(rep, "P08") == ["B", "C", "G"]
    assert ids(rep, "P09") == ["C"]
    checks = {c.check_id: c for c in rep.checks}
    assert checks["P08"].eligible == 5 and checks["P08"].findings == 3


def test_same_day_overlap_is_separated():
    raw = ("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\n%R\t1\tD\n"
           "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\tstatus_code\tact_start_date\tact_end_date\n"
           "%R\t1\t1\tA\tTK_Complete\t2026-09-01 08:00\t2026-09-05 17:00\n"
           "%R\t2\t1\tB\tTK_Active\t2026-09-05 08:00\t\n"
           "%T\tTASKPRED\n%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n%R\t1\t2\t1\tPR_FS\t0\n%E\n")
    rep = validate_progress(build_snapshot(parse_xer_bytes(raw.encode())), datetime(2026, 10, 1))
    assert ids(rep, "P08") == [] and ids(rep, "P10") == ["B"]


def test_data_date_suggestion_never_before_project_start():
    from p6toolkit.progress import suggested_data_date, data_date_candidates
    raw = ("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\tlast_recalc_date\tplan_start_date\n"
           "%R\t1\tD\t2026-01-05 08:00\t2026-02-02 08:00\n%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\n%R\t1\t1\tA\n%E\n")
    snap = build_snapshot(parse_xer_bytes(raw.encode()))
    assert [s for s, _ in data_date_candidates(snap)] == ["PROJECT.last_recalc_date", "PROJECT.plan_start_date"]
    assert suggested_data_date(snap) == datetime(2026, 2, 2, 8, 0)


def test_dcma_09_only_with_confirmed_data_date():
    from p6toolkit import dcma_precheck
    snap = build_snapshot(parse_xer_bytes(XER.encode()))
    assert dcma_precheck(snap)[8]["Observed"] is None
    row = dcma_precheck(snap, datetime(2026, 10, 1, 8, 0))[8]
    assert row["Observed"] == 3          # C (P01) + D (P03) + D (P04)


def test_version_order_problems():
    from p6toolkit.history import check_version_order
    d = datetime
    assert check_version_order([d(2026, 1, 1), d(2026, 2, 1)]) == []
    assert check_version_order([d(2026, 2, 1), d(2026, 1, 1)]) == ["Versions are not in increasing Data Date order"]
    assert check_version_order([d(2026, 1, 1), d(2026, 1, 1)]) == ["Two or more versions share the same Data Date"]
    assert check_version_order([d(2026, 1, 1), None]) == ["Data Date not confirmed for every selected version"]
