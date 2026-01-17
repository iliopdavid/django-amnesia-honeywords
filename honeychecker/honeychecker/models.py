from sqlalchemy import Column, Integer, String
from .db import Base

class HoneycheckerRecord(Base):
    __tablename__ = "honeychecker_records"
    user_id = Column(String, primary_key=True)
    real_index = Column(Integer, nullable=False)