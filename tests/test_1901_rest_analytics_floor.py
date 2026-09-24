from pathlib import Path
import database

def test_short_rest_keeps_raw_and_flags_effective_floor():
    assert database.rest_analytics_sample(2) == {"raw_seconds":2,"effective_seconds":60,"adjusted":True,"adjustment_reason":"minimum_effective_rest"}

def test_normal_rest_is_not_adjusted():
    assert database.rest_analytics_sample(95) == {"raw_seconds":95,"effective_seconds":95,"adjusted":False,"adjustment_reason":None}

def test_live_timer_and_storage_are_not_rewritten():
    main=Path("main.py").read_text()
    assert "rest_seconds < 60 THEN 60" in main
    assert "week_rest_data[w][0] += max(60, rest_secs)" in main
    assert "UPDATE workout_sets SET rest_seconds" not in main
