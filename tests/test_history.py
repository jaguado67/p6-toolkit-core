from p6toolkit import build_float_history

def test_hourly_float_trend_no_universal_day_conversion(baseline, update):
    obs = build_float_history([baseline, update], "A100")
    assert [x.total_float_hours for x in obs] == [20, 17]
    assert obs[0].delta_hours is None
    assert obs[1].delta_hours == -3

def test_missing_activity_is_not_inferred(baseline, update):
    obs = build_float_history([baseline, update], "A400")
    assert obs[0].total_float_hours is None
    assert obs[1].delta_hours is None
