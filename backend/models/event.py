from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ScheduleEvent:
    partition_key: str  # season year e.g. "2025"
    row_key: str        # e.g. "2025-09-06_football-lincoln"
    event_type: str     # football_game | competition | parade | rehearsal | concert
    event_name: str
    event_date: str     # ISO date "YYYY-MM-DD"
    call_time: str      # "HH:MM" 24h
    performance_time: str
    estimated_return: str
    location_name: str
    location_address: str
    drop_off_location: str
    is_away: bool = False
    notes: str = ""

    def to_table_entity(self) -> dict:
        return {
            "PartitionKey": self.partition_key,
            "RowKey": self.row_key,
            "event_type": self.event_type,
            "event_name": self.event_name,
            "event_date": self.event_date,
            "call_time": self.call_time,
            "performance_time": self.performance_time,
            "estimated_return": self.estimated_return,
            "location_name": self.location_name,
            "location_address": self.location_address,
            "drop_off_location": self.drop_off_location,
            "is_away": self.is_away,
            "notes": self.notes,
        }

    @classmethod
    def from_table_entity(cls, entity: dict) -> "ScheduleEvent":
        return cls(
            partition_key=entity["PartitionKey"],
            row_key=entity["RowKey"],
            event_type=entity.get("event_type", ""),
            event_name=entity.get("event_name", ""),
            event_date=entity.get("event_date", ""),
            call_time=entity.get("call_time", ""),
            performance_time=entity.get("performance_time", ""),
            estimated_return=entity.get("estimated_return", ""),
            location_name=entity.get("location_name", ""),
            location_address=entity.get("location_address", ""),
            drop_off_location=entity.get("drop_off_location", ""),
            is_away=entity.get("is_away", False),
            notes=entity.get("notes", ""),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_readable_text(self) -> str:
        away = " (Away)" if self.is_away else ""
        lines = [
            f"Event: {self.event_name}{away}",
            f"Date: {self.event_date}",
            f"Call Time: {self.call_time}",
            f"Performance: {self.performance_time}",
            f"Location: {self.location_name}",
        ]
        if self.location_address:
            lines.append(f"Address: {self.location_address}")
        lines.append(f"Est. Return: {self.estimated_return}")
        lines.append(f"Drop-off: {self.drop_off_location}")
        if self.notes:
            lines.append(f"Notes: {self.notes}")
        return "\n".join(lines)
