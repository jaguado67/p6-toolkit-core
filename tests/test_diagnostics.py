from dataclasses import replace
from p6toolkit import (audit_logic, audit_constraints, summarize_snapshot,
                       dcma_precheck, parse_xer_bytes, build_snapshot)
from p6toolkit.snapshot import Relationship


def test_logic_original_snapshot(baseline):
    info=audit_logic(baseline)
    assert info.relationship_types=={'FS':2}
    assert info.positive_lags==0
    assert info.negative_lags==0
    assert len(info.relationship_rows)==2


def test_logic_detects_leads_lags_and_same_pair(baseline):
    extra=(Relationship('11','100','101','SS',-8.0,{}),
           Relationship('12','101','102','FF',4.0,{}),
           Relationship('13','100','101','FS',0.0,{}))
    changed=replace(baseline,relationships=baseline.relationships+extra)
    info=audit_logic(changed)
    assert info.negative_lags==1
    assert info.positive_lags==1
    assert info.relationship_types['SS']==1
    assert ('A100','A200','FS',0.0) in info.duplicate_identical
    assert ('A100','A200',3) in info.parallel_pair_candidates


def test_constraints_primary_and_secondary():
    raw=("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\n%R\t1\tDEMO\n"
         "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\tcstr_type\tcstr_date\tcstr_type2\tcstr_date2\n"
         "%R\t100\t1\tA100\tCS_MSO\t2026-01-02 08:00\tCS_MFO\t\n%E\n")
    snap=build_snapshot(parse_xer_bytes(raw.encode()))
    report=audit_constraints(snap)
    assert report.activities_with_constraints==1
    assert report.constraint_instances==2
    assert report.by_type=={'CS_MSO':1,'CS_MFO':1}
    assert report.missing_dates==1


def test_constraints_none_not_counted():
    raw=("ERMHDR\t26\n%T\tPROJECT\n%F\tproj_id\tproj_short_name\n%R\t1\tDEMO\n"
         "%T\tTASK\n%F\ttask_id\tproj_id\ttask_code\tcstr_type\n%R\t100\t1\tA100\tCS_NONE\n%E\n")
    snap=build_snapshot(parse_xer_bytes(raw.encode()))
    assert audit_constraints(snap).constraint_instances==0


def test_incomplete_only_for_float_summary(baseline):
    info=summarize_snapshot(baseline)
    assert info['activities']==3
    assert info['remaining_with_float']==2
    assert info['status']['Completed']==1
    assert info['zero_float']==1


def test_dcma_is_explicitly_partial(baseline):
    rows=dcma_precheck(baseline)
    assert len(rows)==14
    assert rows[0]['Coverage']=='Exploratory'
    assert rows[4]['Coverage']=='Inventory'
    assert rows[11]['Coverage']=='Not evaluated'
    assert all('Pass' not in r and 'Fail' not in r for r in rows)
