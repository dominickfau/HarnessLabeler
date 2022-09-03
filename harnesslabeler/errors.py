class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class LoadDefaultDataError(Error):
    """Raised if an issue occurs when creating default data."""

class MissingRequiredSoftwareError(Error):
    """Raised when a missing software package is missing or not found."""
    pass

class SetLabelFileError(Error):
    """Raised when a set label file is missing or not found."""
    pass

class ScheduledTaskExistsError(Error):
    """Raised when a scheduled task already exists."""
    pass

class BatteryNotAssignedError(Error):
    """Raised when a battery is not assigned to a drone."""
    pass

class DocumentExistsError(Error):
    """Raised when a document already exists."""
    pass

class CrewMemberExistsError(Error):
    """Raised when a crew member already exists."""
    pass

class NoCrewMembersError(Error):
    """Raised when no crew members are assigned to a drone."""
    pass

class MissingRequiredRoleError(Error):
    """Raised when a user is missing a required role."""
    pass

class FlightAlreadyStartedError(Error):
    """Raised when a flight is already started."""
    pass

class RoleNotAssignedError(Error):
    """Raised when a role is not assigned to a user."""
    pass

class RoleRemovalError(Error):
    """Raised when a role can not be removed from a user."""
    pass

class BatteryRemoveError(Error):
    """Raised when a battery can not be removed from a drone."""
    pass

class ImageExistsError(Error):
    """Raised when an image already exists."""
    pass

class DeleteBatteryError(Error):
    """Raised when a battery can not be deleted from the database."""
    pass

class DeleteEquipmentError(Error):
    """Raised when an equipment can not be deleted from the database."""
    pass

class DeleteDroneError(Error):
    """Raised when a drone can not be deleted from the database."""
    pass

class UomConversionError(Error):
    pass