from datetime import datetime, timedelta, time
from typing import Optional, Tuple
from ..models import Zone, ScheduleRule

class TimeUtils:
    @staticmethod
    def parse_time(time_str: str) -> time:
        """Parse HH:MM string to time object. Handles '24:00' as special case."""
        if time_str == "24:00":
            return time(23, 59, 59)
        return datetime.strptime(time_str, "%H:%M").time()

    @staticmethod
    def get_rule_for_day(zone: Zone, date: datetime) -> Optional[ScheduleRule]:
        """Get the schedule rule for a specific date (day of week)."""
        day_of_week = date.weekday() # 0=Mon, 6=Sun
        for rule in zone.rules:
            if day_of_week in rule.days:
                return rule
        return None

    @staticmethod
    def get_end_time_for_all_day(zone: Zone, date: datetime, offset_minutes: int = 0) -> str:
        """
        Calculate end time for 'all day' parking on a given date.
        Use offset=0 by default (user requested removal of offset).
        Special case: 24:00 becomes 23:59 to avoid invalid time errors.
        Returns HH:MM string.
        """
        rule = TimeUtils.get_rule_for_day(zone, date)
        if not rule:
            # If no rule (free parking?), maybe just return end of day or current time?
            # User implies paid parking times. If outside, maybe error or default.
            return "23:59"

        end_str = rule.end_time
        
        # Handle 24:00 special case logic
        if end_str == "24:00":
             # Force to 23:59 as 24:00 invalid
             # Apply offset if provided, but default is 0 now
             if offset_minutes == 0:
                 return "23:59"
             
             # If someone really wants an offset from 24:00 (e.g. 23:00)
             dt = datetime.combine(date.date(), time(0, 0)) + timedelta(days=1)
             final_dt = dt - timedelta(minutes=offset_minutes)
             # If minute is 0, return HH:MM
             # If user wanted 23:59 specifically for 24:00 with 0 offset, that is covered.
             return final_dt.strftime("%H:%M")
        
        # Parse standard time
        t = datetime.strptime(end_str, "%H:%M").time()
        dt = datetime.combine(date.date(), t)
        final_dt = dt - timedelta(minutes=offset_minutes)
        return final_dt.strftime("%H:%M")

    @staticmethod
    def is_within_paid_hours(zone: Zone, dt: datetime) -> bool:
        """Check if a specific datetime is within paid parking hours."""
        rule = TimeUtils.get_rule_for_day(zone, dt)
        if not rule:
            return False
            
        start = TimeUtils.parse_time(rule.start_time)
        # Handle 24:00 for end time
        if rule.end_time == "24:00":
            end = time(23, 59, 59)
        else:
            end = TimeUtils.parse_time(rule.end_time)
            
        current = dt.time()
        return start <= current <= end
