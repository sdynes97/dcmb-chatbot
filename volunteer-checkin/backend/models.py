from dataclasses import dataclass


@dataclass
class Volunteer:
    """A person who appears on the kiosk name list."""
    id: str
    name: str

    PARTITION_KEY = "roster"

    def to_table_entity(self) -> dict:
        return {"PartitionKey": self.PARTITION_KEY, "RowKey": self.id, "name": self.name}

    @classmethod
    def from_table_entity(cls, entity: dict) -> "Volunteer":
        return cls(id=entity["RowKey"], name=entity.get("name", ""))

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@dataclass
class Activity:
    """Something a volunteer checks in to, e.g. 'Concessions' or 'Pit Crew'."""
    id: str
    name: str

    PARTITION_KEY = "activity"

    def to_table_entity(self) -> dict:
        return {"PartitionKey": self.PARTITION_KEY, "RowKey": self.id, "name": self.name}

    @classmethod
    def from_table_entity(cls, entity: dict) -> "Activity":
        return cls(id=entity["RowKey"], name=entity.get("name", ""))

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}


@dataclass
class CheckIn:
    """One kiosk check-in. Date/time are stored in the kiosk's local timezone."""
    row_key: str
    check_in_date: str     # YYYY-MM-DD (local)
    check_in_time: str     # HH:MM:SS (local)
    checked_in_at_utc: str  # ISO datetime, UTC
    volunteer_name: str
    activity: str
    volunteer_id: str = ""  # Empty for walk-ins not on the roster

    PARTITION_KEY = "checkin"

    CSV_FIELDS = ["date", "time", "name", "activity", "walk_in", "checked_in_at_utc"]

    def to_table_entity(self) -> dict:
        return {
            "PartitionKey": self.PARTITION_KEY,
            "RowKey": self.row_key,
            "check_in_date": self.check_in_date,
            "check_in_time": self.check_in_time,
            "checked_in_at_utc": self.checked_in_at_utc,
            "volunteer_name": self.volunteer_name,
            "volunteer_id": self.volunteer_id,
            "activity": self.activity,
        }

    @classmethod
    def from_table_entity(cls, entity: dict) -> "CheckIn":
        return cls(
            row_key=entity["RowKey"],
            check_in_date=entity.get("check_in_date", ""),
            check_in_time=entity.get("check_in_time", ""),
            checked_in_at_utc=entity.get("checked_in_at_utc", ""),
            volunteer_name=entity.get("volunteer_name", ""),
            activity=entity.get("activity", ""),
            volunteer_id=entity.get("volunteer_id", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.row_key,
            "date": self.check_in_date,
            "time": self.check_in_time,
            "checked_in_at_utc": self.checked_in_at_utc,
            "name": self.volunteer_name,
            "activity": self.activity,
            "walk_in": not self.volunteer_id,
        }

    def to_csv_row(self) -> dict:
        d = self.to_dict()
        d["walk_in"] = "yes" if d["walk_in"] else ""
        return {k: d[k] for k in self.CSV_FIELDS}
