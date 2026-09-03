"""BLOQUE 58.6x: Movement package \u2014 FlightFormations, BezierCurves, PathFollowing.

Public API:
  - BezierPath       (cubic bezier, position + tangent at t)
  - WaypointPath     (list of waypoints, constant speed)
  - HybridPath       (concatenate bezier + waypoint segments)
  - PathFollower     (stateful, advances t over time)
  - FlightFormation  (V, LINE, DIAMOND, SQUARE, WEDGE, CIRCLE, TRIANGLE, HALF_V, CUSTOM)
  - FormationKind    (enum for the preset names)
  - FormationPathSpec (bridge: formation + path -> ready-to-spawn enemies)

Coordinate convention: 320x480 internal playfield, +x right, +y down.
No numpy/scipy dependency (GDD \u00a70).
"""
from src.movement.bezier import BezierPath, Point
from src.movement.formation import FlightFormation, FormationKind
from src.movement.hybrid import HybridPath
from src.movement.follower import PathFollower
from src.movement.cardioid_path import CardioidPath  # noqa: F401
from src.movement.lemniscate_path import LemniscatePath  # noqa: F401
from src.movement.spec import FormationPathSpec
from src.movement.waypoint import WaypointPath

__all__ = [
    "BezierPath",
    "Point",
    "WaypointPath",
    "HybridPath",
    "PathFollower",
    "FlightFormation",
    "FormationKind",
    "FormationPathSpec",
    "LemniscatePath",
    "CardioidPath",
]
