from enum import Enum

class PythonEnum(Enum):
    @classmethod
    def all(cls) -> list[str]:
        return [e.value for e in cls]


class Airworthyness(PythonEnum):
    Airworthy = "Airworthy"
    Maintenance = "Under Maintenance"
    Retired = "Retired"


class EquipmentGroup(PythonEnum):
    Ground = "Ground"
    """Used for equipment that will stay on the ground."""
    Airborne = "Airborne"
    """Used for equipment that will attach to a drone."""


class LoginEventType(PythonEnum):
    """Represents a user login log event type."""
    Login = "Login"
    Logout = "Logout"


class ThrustDirection(PythonEnum):
    """Represents a thrust direction."""
    Vertical = "Vertical"
    Horizontal = "Horizontal"


class UomType(PythonEnum):
    Count = "Count"
    Weight = "Weight"
    Length = "Length"
    Area = "Area"
    Volume = "Volume"
    Time = "Time"