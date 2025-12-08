from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime,timezone

Base = declarative_base()


class IPOApplication(Base):
    __tablename__ = "ipo_applications"

    id = Column(Integer, primary_key=True)
    ipo_name = Column(String(255), nullable=False)
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied_units = Column(Integer, nullable=False)
    status = Column(String(50), default="applied", nullable=False)
    result_date = Column(DateTime, nullable=True)
    result_status = Column(String(50), nullable=True)
    allotted_units = Column(Integer, default=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    def to_dict(self):
        return{
            'id': self.id,
            'ipo_name':self.ipo_name,
            'applied_date': self.applied_date.isoformat() if self.applied_date else None,
            'applied_units': self.applied_units,
            'status': self.status,
            'result_date': self.result_date.isoformat() if self.result_date else None,
            'result_status': self.result_status,
            'allotted_units': self.allotted_units
        }
        
