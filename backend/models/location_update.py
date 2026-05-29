from dataclasses import dataclass


@dataclass
class ETAUpdate:
    eta_time: str        # ISO datetime string
    message: str         # Free-text from director, e.g. "Leaving Lincoln now"
    updated_at: str      # ISO datetime when this was posted
    event_row_key: str = ""  # Which event this ETA is for

    PARTITION_KEY = "eta"
    ROW_KEY = "current"

    def to_table_entity(self) -> dict:
        return {
            "PartitionKey": self.PARTITION_KEY,
            "RowKey": self.ROW_KEY,
            "eta_time": self.eta_time,
            "message": self.message,
            "updated_at": self.updated_at,
            "event_row_key": self.event_row_key,
        }

    @classmethod
    def from_table_entity(cls, entity: dict) -> "ETAUpdate":
        return cls(
            eta_time=entity.get("eta_time", ""),
            message=entity.get("message", ""),
            updated_at=entity.get("updated_at", ""),
            event_row_key=entity.get("event_row_key", ""),
        )

    def to_dict(self) -> dict:
        return {
            "eta_time": self.eta_time,
            "message": self.message,
            "updated_at": self.updated_at,
            "event_row_key": self.event_row_key,
        }

    def to_readable_text(self) -> str:
        return f"Director update (as of {self.updated_at}): {self.message}"
