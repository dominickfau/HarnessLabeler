from abc import abstractmethod, abstractstaticmethod
import bcrypt
import logging
from typing import List, Optional
from datetime import datetime
from typing import Optional
from sqlalchemy.orm.session import Session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from harnesslabeler.mixins import AuditMixin
from harnesslabeler.database import DBContext, DeclarativeBase, engine, create_engine

from harnesslabeler import errors, enums, config

logger = logging.getLogger("backend")



class Base(DeclarativeBase):
    __abstract__ = True
    # __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)


class Status(Base):
    __abstract__ = True
    __table_args__ = {"sqlite_autoincrement": False}

    name = Column(String(50), nullable=False, unique=True)

    def __repr__(self):
        return f'<{self.__class__.name}(id={self.id}, name="{self.name}")>'
    
    def __str__(self) -> str:
        return self.name
    
    @abstractstaticmethod
    def find_by_id(session: Session, id_: int) -> Optional['Status']:
        pass
    
    @abstractstaticmethod
    def find_by_name(session: Session, name: str) -> Optional['Status']:
        pass


class Type_(Base):
    __abstract__ = True

    name = Column(String(50), nullable=False, unique=True)

    def __repr__(self):
        return f'<{self.__class__.name}(id={self.id}, name="{self.name}")>'
    
    def __str__(self) -> str:
        return self.name
    
    @abstractmethod
    def find_by_id(self, session: Session, id_: int) -> Optional['Type_']:
        pass
    
    @abstractmethod
    def find_by_name(self, session: Session, name: str) -> Optional['Type_']:
        pass


class User(Base):
    __tablename__ = 'user'

    active = Column(Boolean, nullable=False, default=True)
    last_login_date = Column(DateTime) # type: datetime
    first_name = Column(String(15), nullable=False)
    last_name = Column(String(15), nullable=False)
    username = Column(String(256), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False)

    # Relationship

    def __repr__(self) -> str:
        return f"User('{self.username}', '{self.email}')"
    
    def __str__(self) -> str:
        return self.full_name
    
    def to_dict(self) -> dict:
        return  {
            "id": self.id,
            "active": self.active,
            "last_login_date": self.last_login_date_str,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "password_hash": self.password_hash
        }
    
    def on_login(self) -> 'UserLoginLog':
        """Log a login event."""
        logger.info(f"[USER] User '{self}' logged in.")
        self.last_login_date = datetime.now()
        return UserLoginLog.create(event_type=enums.LoginEventType.Login, user=self)
    
    def on_logout(self) -> 'UserLoginLog':
        """Log a logout event."""
        logger.info(f"[USER] User '{self}' logged out.")
        return UserLoginLog.create(event_type=enums.LoginEventType.Logout, user=self)
    
    @property
    def last_login_date_str(self) -> str:
        return self.last_login_date.strftime(config.DATETIME_FORMAT)
    
    @property
    def password(self) -> None:
        """Prevent password from being accessed."""
        raise AttributeError('password is not a readable attribute!')
    
    @property
    def is_superuser(self) -> bool:
        """Check if the user is a superuser."""
        return self.id == 1

    @password.setter
    def password(self, password: str):
        """Hash password on the fly. This allows the plan text password to be used when creating a User instance."""
        self.password_hash = User.generate_password_hash(password)
    
    @property
    def full_name(self) -> str:
        """Return the full name of the user. In the following format: first_name, last_name"""
        return f"{self.first_name}, {self.last_name}"
    
    @property
    def initials(self) -> str:
        """Return the initials of the user."""
        return f"{self.first_name[0].upper()}{self.last_name[0].upper()}"
    
    def check_password(self, password: str) -> bool:
        """Check user password. Returns True if password is correct."""
        return User.verify_password(self.password_hash, password)
    
    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        """Check if password matches the one provided."""
        return bcrypt.checkpw(password.encode(config.ENCODING_STR), password_hash.encode(config.ENCODING_STR))
    
    @staticmethod
    def generate_password_hash(password: str) -> str:
        """Generate a hashed password."""
        return bcrypt.hashpw(password.encode(config.ENCODING_STR), bcrypt.gensalt()).decode(config.ENCODING_STR)


class UserLoginLog(Base):
    """A simple log for tracking who logged in or out and when."""
    __tablename__ = 'user_login'

    event_date = Column(DateTime, nullable=False, default=datetime.now)
    event_type = Column(Enum(enums.LoginEventType))
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)

    # Relationships
    user = relationship('User', foreign_keys=[user_id]) # type: User

    def __repr__(self) -> str:
        return f"<UserLoginLog(id={self.id}, event_date={self.event_date}, event_type={self.event_type}, user={self.user})>"
    
    def __str__(self) -> str:
        return f"{self.event_date} - {self.event_type} - {self.user}"
    
    def to_dict(self) -> dict:
        return  {
            "id": self.id,
            "event_type": self.event_type.name,
            "event_date": self.event_date.strftime(config.DATETIME_FORMAT),
            "user_id": self.user_id
        }

    @staticmethod
    def create(event_type: enums.LoginEventType, user: User) -> 'UserLoginLog':
        """Create a new user login log."""
        log = UserLoginLog(event_type=event_type, user=user)
        return log

    @staticmethod
    def on_login(user: User) -> 'UserLoginLog':
        """Log a login event."""
        return UserLoginLog.create(event_type=enums.LoginEventType.Login, user=user)
    
    @staticmethod
    def on_logout(user: User) -> 'UserLoginLog':
        """Log a logout event."""
        return UserLoginLog.create(event_type=enums.LoginEventType.Logout, user=user)


class BreakoutLabel(Base, AuditMixin):
    """Represents a label for a harness breakout point."""
    __tablename__ = "label"
    __table_args__ = (
        UniqueConstraint("part_number", "value", "sort_index", "rolling_label", name="UC_pn_value_sort_rolling"),
    )

    part_number = Column(String(100), index=True, nullable=False)
    value = Column(String(256), nullable=False)
    sort_index = Column(Integer, nullable=False)
    rolling_label = Column(Boolean, nullable=False, default=False)

    @property
    def type_name(self) -> str:
        return "Rolling" if self.rolling_label else "Breakout"
    
    def __repr__(self) -> str:
        return f'<BreakoutLabel(id={self.id}, part_number="{self.part_number}", value="{self.value}", sort_index={self.sort_index}, rolling_label={self.rolling_label})>'
    
    def to_dict(self) -> dict:
        return  {
            "id": self.id,
            "part_number": self.part_number,
            "value": self.value,
            "sort_index": self.sort_index,
            "rolling_label": self.rolling_label,
            "date_created": self.date_created_str,
            "date_modified": self.date_modified_str,
            "created_by_user_id": self.created_by_user_id,
            "modified_by_user_id": self.modified_by_user_id
        }

    def save(self, session: Session, user: User) -> None:
        """Creates a new BreakoutLabel.

        Args:
            session (Session): The session to use.
            user (User): The user making the change.
        """
        self.date_modified = datetime.now()
        self.modified_by_user_id = user.id
        self.value = self.value.strip()
    
    def delete(self, session: Session, user: User) -> None:
        """Deletes the label and reorders sort_index to be correct.

        Args:
            session (Session): The session to use.
            user (User): The user making the change.
        """
        logger.info(f"Deleting Label '{self}'.")
        breakout_labels = session.query(BreakoutLabel)\
                        .filter(BreakoutLabel.part_number == self.part_number)\
                        .filter(BreakoutLabel.rolling_label == self.rolling_label)\
                        .order_by(BreakoutLabel.sort_index).all() # type: List[BreakoutLabel]
        
        if len(breakout_labels) > 0:
            current_sort_index = 1
            self.sort_index = -1
            session.commit()

            logger.info(f"Reordering sort_index on remaining labels.")
            for breakout_label in breakout_labels:
                logger.debug(f"Updating label '{breakout_label}' sort_index from {breakout_label.sort_index} to {current_sort_index}.")
                if breakout_label.id == self.id:
                    continue
                breakout_label.sort_index = current_sort_index
                breakout_label.save(session, user)
                current_sort_index += 1

        session.delete(self)
        session.commit()

    @staticmethod
    def create(part_number: str, value: str, rolling_label: bool=False) -> 'BreakoutLabel':
        with DBContext() as session:
            breakout_label = session.query(BreakoutLabel).filter(BreakoutLabel.part_number == part_number)\
                                .order_by(BreakoutLabel.sort_index.desc()).first() # type: BreakoutLabel
            if not breakout_label:
                sort_index = 1
            else:
                sort_index = breakout_label.sort_index + 1
            
        return BreakoutLabel(
            part_number=part_number,
            value=value,
            sort_index=sort_index,
            rolling_label=rolling_label
        )



def create_tables():
    logger.info("[SYSTEM] Creating tables...")
    Base.metadata.create_all(engine)


def drop_tables():
    logger.warning("[SYSTEM] Droping tables...")
    Base.metadata.drop_all(engine)


def create_default_data():
    logger.info("[SYSTEM] Creating default data...")
    user = User(
        first_name = "Admin",
        last_name = "User",
        username = "admin",
        password = "admin"
    )

    with DBContext() as session:
        if not session.query(User).filter(User.username == "admin").first():
            session.add(user)
            user.last_login_date = datetime.now()
            session.commit()
            logger.warning(f"[SYSTEM] Created default user '{user}'. Username: 'admin', Password: 'admin'.")


def force_recreate():
    logger.warning("[SYSTEM] Force recreating database. Data loss will occur.")
    if config.DATABASE_URL_WITHOUT_SCHEMA.startswith("mysql"):
        temp_engine = create_engine(config.DATABASE_URL_WITHOUT_SCHEMA)
        temp_engine.execute(config.SCHEMA_CREATE_STATEMENT)
        temp_engine.dispose()

    drop_tables()
    create_database()


def create_database():
    logger.info("[SYSTEM] Creating database...")
    if config.DATABASE_URL_WITHOUT_SCHEMA.startswith("mysql"):
        temp_engine = create_engine(config.DATABASE_URL_WITHOUT_SCHEMA)
        temp_engine.execute(config.SCHEMA_CREATE_STATEMENT)
        temp_engine.dispose()

    create_tables()
    create_default_data()