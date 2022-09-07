from __future__ import annotations
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from .config import *

logger = logging.getLogger("backend")


log_started = False
if not log_started:
    logging.getLogger("sqlalchemy.engine").info("=" * 80)
    logging.getLogger("sqlalchemy.pool").info("=" * 80)
    logging.getLogger("sqlalchemy.dialects").info("=" * 80)
    logging.getLogger("sqlalchemy.orm").info("=" * 80)
    log_started = True


engine = create_engine(DATABASE_URL_WITH_SCHEMA, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
DeclarativeBase = declarative_base(bind=engine)


class DBContext:
    """Context manager for talking to the database.
    """
    def __init__(self, dissable_foreign_key_checks: bool=False):
        logger.debug("[DATABASE] Session created.")
        self.db = SessionLocal()
        self.db.expire_on_commit = False
        self.dissable_foreign_key_checks = dissable_foreign_key_checks
        if self.dissable_foreign_key_checks:
            logger.warning("[DATABASE] Dissabling foreign key checks.")
            self.db.execute("SET foreign_key_checks = 0;")

    def __enter__(self) -> Session:
        logger.debug("Starting DB context.")
        return self.db

    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("Exiting DB context.")
        if self.dissable_foreign_key_checks:
            logger.warning("[DATABASE] Reenabling foreign key checks.")
            self.db.execute("SET foreign_key_checks = 1;")
        self.db.close()
        logger.debug("[DATABASE] Session closed.")


def get_session() -> Session:
    """ Returns the current db connection """
    with DBContext() as session:
        yield session