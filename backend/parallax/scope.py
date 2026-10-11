"""Vehicle scope: the PM works inside one vehicle (e.g. G60); everything else is context.

Every record falls into exactly one scope by its subjects:
  target        the vehicle itself or a group that contains it (e.g. "5 Series")
  competitor    a competitor vehicle (and no target subject)
  other_models  another BMW model only (e.g. 7 Series)
  brand         no vehicle at all (e.g. My BMW app reviews)
"""

from sqlalchemy import Text, literal
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import Session

from parallax.config import get_settings
from parallax.models import Record
from parallax.themes import target_scope

SCOPES = ("target", "competitor", "other_models", "brand")
SCOPE_LABELS = {"target": "This vehicle", "competitor": "Competitors", "other_models": "Other BMW models",
                "brand": "Brand-wide (no vehicle, e.g. My BMW app)"}


def normalize_vehicle(vehicle: str | None) -> str:
    if not vehicle:
        return get_settings().target_model
    return vehicle if ":" in vehicle else f"bmw:{vehicle.upper()}"


class VehicleScope:
    def __init__(self, session: Session, vehicle: str | None = None):
        self.target_model = normalize_vehicle(vehicle)
        self.bmw_models, self.relevant = target_scope(session, self.target_model)

    def of(self, subjects: list[str] | None) -> str:
        subjects = set(subjects or [])
        if subjects & self.relevant:
            return "target"
        if any(s.startswith("competitor:") for s in subjects):
            return "competitor"
        if subjects & self.bmw_models:
            return "other_models"
        return "brand"

    def target_filter(self):
        """SQL condition: the record names the vehicle or one of its groups (GIN index on subject_ids)."""
        return Record.subject_ids.op("&&")(literal(sorted(self.relevant), type_=PG_ARRAY(Text)))
