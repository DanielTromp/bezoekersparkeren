import pytest
from datetime import datetime
from bezoekersparkeren.models import Zone, ScheduleRule
from bezoekersparkeren.utils.time_utils import TimeUtils

@pytest.fixture
def filmwijk_zone():
    return Zone(
        name="Filmwijk",
        code="36044",
        hourly_rate=0.25,
        max_daily_rate=1.00,
        rules=[
            ScheduleRule(days=[0, 1, 2], start_time="09:00", end_time="22:00"), # Mon-Wed
            ScheduleRule(days=[3, 4, 5], start_time="09:00", end_time="24:00"), # Thu-Sat
            ScheduleRule(days=[6], start_time="12:00", end_time="17:00")        # Sun
        ]
    )

def test_filmwijk_schedules(filmwijk_zone):
    # Monday (0)
    mon = datetime(2025, 12, 15) # Mon
    rule = TimeUtils.get_rule_for_day(filmwijk_zone, mon)
    assert rule.start_time == "09:00"
    assert rule.end_time == "22:00"

    # Thursday (3)
    thu = datetime(2025, 12, 18) # Thu
    rule = TimeUtils.get_rule_for_day(filmwijk_zone, thu)
    assert rule.start_time == "09:00"
    assert rule.end_time == "24:00"
    
    # Sunday (6)
    sun = datetime(2025, 12, 21) # Sun
    rule = TimeUtils.get_rule_for_day(filmwijk_zone, sun)
    assert rule.start_time == "12:00"
    assert rule.end_time == "17:00"

def test_all_day_offset(filmwijk_zone):
    # Test 24:00 -> 23:59 (default 0 offset, strict mapping)
    thu = datetime(2025, 12, 18) # Thu end 24:00
    end_time = TimeUtils.get_end_time_for_all_day(filmwijk_zone, thu)
    assert end_time == "23:59"
    
    # Test 22:00 -> 22:00 (default 0 offset)
    mon = datetime(2025, 12, 15) # Mon end 22:00
    end_time = TimeUtils.get_end_time_for_all_day(filmwijk_zone, mon)
    assert end_time == "22:00"
    
    # Test custom offset still works (e.g. 60 min)
    # 22:00 -> 21:00
    end_time_offset = TimeUtils.get_end_time_for_all_day(filmwijk_zone, mon, offset_minutes=60)
    assert end_time_offset == "21:00"
    
    # Test custom offset on 24:00 
    # Logic in code: if offset != 0, it applies standard subtraction logic 
    # (assuming 24:00 is next day 00:00).
    # 24:00 - 60min = 23:00
    end_time_offset_24 = TimeUtils.get_end_time_for_all_day(filmwijk_zone, thu, offset_minutes=60)
    assert end_time_offset_24 == "23:00"
