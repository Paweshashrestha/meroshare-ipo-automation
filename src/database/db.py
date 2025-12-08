from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.database.models import Base, IPOApplication
from src.config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, config: Config):
        self.config = config
        db_config = config.get_database()

        if db_config.get("type") == "postgresql":
            db_url = f"postgresql://{db_config.get('user')}:{db_config.get('password')}@{db_config.get('host')}:{db_config.get('port', 5432)}/{db_config.get('database')}"
        else:
            db_url = f"sqlite:///{db_config.get('path', 'ipo_applications.db')}"

        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def add_application(
        self, ipo_name: str, applied_units: int, status: str = "applied"
    ) -> IPOApplication:
        session = self.get_session()
        try:
            app = IPOApplication(
                ipo_name=ipo_name, applied_units=applied_units, status=status
            )
            session.add(app)
            session.commit()
            session.refresh(app)
            return app
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding application: {e}")
            raise
        finally:
            session.close()

    def update_application_result(
        self, ipo_name: str, result_status: str, allotted_units: int = 0
    ):
        session = self.get_session()
        try:
            app = (
                session.query(IPOApplication)
                .filter_by(ipo_name=ipo_name)
                .order_by(IPOApplication.applied_date.desc())
                .first()
            )
            if app:
                app.result_status = result_status
                app.allotted_units = allotted_units
                app.result_date = datetime.utcnow()
                app.status = "completed"
                session.commit()
            return app
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating result: {e}")
            raise
        finally:
            session.close()

    def get_pending_results(self):
        session = self.get_session()
        try:
            return (
                session.query(IPOApplication)
                .filter(
                    IPOApplication.status == "applied",
                    IPOApplication.result_status.is_(None),
                )
                .all()
            )
        finally:
            session.close()
