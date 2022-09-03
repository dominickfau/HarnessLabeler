from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import declared_attr, relationship
from .config import *


class NoteMixin:
    """Note mixin. Adds note_id to model."""

    @declared_attr
    def note_id(self) -> Column:
        return Column(Integer, ForeignKey('note.id'))
    
    @declared_attr
    def note(self):
        return relationship("Note", foreign_keys=[self.note_id])
    
    @property
    def has_note(self) -> bool:
        """Returns True if there is a note."""
        return (self.note_id != None)


class AuditMixin:
    """Audit mixin. Adds date_created, date_modified, created_by_user, and modified_by_user columns to the model."""

    @declared_attr
    def date_created(self) -> Column:
        return Column(DateTime, nullable=False, default=datetime.now) # type: datetime
    
    @declared_attr
    def date_modified(self) -> Column:
        return Column(DateTime, nullable=False, default=datetime.now) # type: datetime
    
    @declared_attr
    def modified_by_user_id(self) -> Column:
        return Column(Integer, ForeignKey("user.id"))
    
    @declared_attr
    def modified_by_user(self):
        return relationship("User", foreign_keys=[self.modified_by_user_id])
    
    @declared_attr
    def created_by_user_id(self) -> Column:
        return Column(Integer, ForeignKey("user.id"))
    
    @declared_attr
    def created_by_user(self):
        return relationship("User", foreign_keys=[self.created_by_user_id])

    @property
    def date_created_str(self) -> str:
        return self.date_created.strftime(DATETIME_FORMAT)

    @property
    def date_modified_str(self) -> str:
        return self.date_modified.strftime(DATETIME_FORMAT)