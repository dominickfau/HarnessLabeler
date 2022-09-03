from enum import Enum

class PythonEnum(Enum):
    @classmethod
    def all(cls) -> list[str]:
        return [e.value for e in cls]


class LoginEventType(PythonEnum):
    """Represents a user login log event type."""
    Login = "Login"
    Logout = "Logout"