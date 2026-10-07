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
    # Season-long view: projected points per game over the rest of the
    # fantasy season (bye excluded), the player's bye week if still ahead,
    # and whether that bye is this week. None/False when unknown.
    rosPtsPerGame: Optional[float] = None
    byeWeek: Optional[int] = None
    onBye: bool = False

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
            "rosPtsPerGame": self.rosPtsPerGame,
            "byeWeek": self.byeWeek,
            "onBye": self.onBye,
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
            rosPtsPerGame=float(data["rosPtsPerGame"]) if data.get("rosPtsPerGame") is not None else None,
            byeWeek=int(data["byeWeek"]) if isinstance(data.get("byeWeek"), int) else None,
            onBye=bool(data.get("onBye", False)),
        )

    @property
    def valuePts(self) -> float:
        """The weekly value a trade is judged on: rest-of-season points per
        game when known, so a bye (or one soft matchup) this week doesn't
        sink a player's trade value. Falls back to this week's projection."""
        return self.rosPtsPerGame if self.rosPtsPerGame is not None else self.projFantasyPts
