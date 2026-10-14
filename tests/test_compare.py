from dataclasses import replace
from p6toolkit import compare_snapshots

def test_changes_and_additions(baseline, update):
    diff = compare_snapshots(baseline, update)
    assert diff.added == ("A400",)
    assert diff.removed == ()
    assert any(c.activity_code == "A100" and c.field_name == "total_float_hours"
               and c.before == 20 and c.after == 17 for c in diff.field_changes)
    assert ("A300", "A400", "FS", 0.0) in diff.relationships_added

def test_same_project_required(baseline, update):
    import pytest
    with pytest.raises(ValueError, match="Different project codes"):
        compare_snapshots(baseline, replace(update, project_code="OTHER"))

def test_changed_internal_numeric_ids_not_false_add_remove(baseline, update):
    # Activity identity across versions is task_code, not the numeric P6 task_id.
    replacement = {a.task_id: str(int(a.task_id) + 2000) for a in update.activities}
    activities = tuple(replace(a, task_id=replacement[a.task_id]) for a in update.activities)
    relations = tuple(replace(r, predecessor_id=replacement[r.predecessor_id],
                              successor_id=replacement[r.successor_id]) for r in update.relationships)
    updated = replace(update, activities=activities, relationships=relations)
    diff = compare_snapshots(baseline, updated)
    assert diff.added == ("A400",)
    assert diff.removed == ()

def test_project_code_alias_requires_explicit_confirmation(baseline, update):
    import pytest
    renamed = replace(update, project_code="DEMO-UP01")
    with pytest.raises(ValueError, match="confirm explicitly"):
        compare_snapshots(baseline, renamed)
    diff = compare_snapshots(baseline, renamed, confirm_same_project=True)
    assert diff.added == ("A400",)
    assert any("confirmed manually" in w for w in diff.warnings)
