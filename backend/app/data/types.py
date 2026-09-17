from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerData:
    """Provider-agnostic player representation used throughout the app.

    Any new data provider (e.g. a future Postgres-backed cache) should produce
    this same shape so downstream code (routes, LLM layer) never has to know
    which provider it came from.
    """

    id: str
    name: str
    team: Optional[str]
    position: str
    opponent: Optional[str] = None
    injuryStatus: Optional[str] = None
    projFantasyPts: float = 0.0
    projYards: float = 0.0
    projTDs: float = 0.0
    imageUrl: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "opponent": self.opponent,
            "injuryStatus": self.injuryStatus,
            "projFantasyPts": self.projFantasyPts,
            "projYards": self.projYards,
            "projTDs": self.projTDs,
            "imageUrl": self.imageUrl,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlayerData":
        return PlayerData(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            team=data.get("team"),
            position=data.get("position", ""),
            opponent=data.get("opponent"),
            injuryStatus=data.get("injuryStatus"),
            projFantasyPts=float(data.get("projFantasyPts") or 0),
            projYards=float(data.get("projYards") or 0),
            projTDs=float(data.get("projTDs") or 0),
            imageUrl=data.get("imageUrl", ""),
        )
