from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime


Base = declarative_base()

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_completed = Column(Boolean, default=False)
    is_todo = Column(Boolean, default=True)


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    type = Column(String, default="string")  # string, int, bool 등
    category = Column(String, nullable=True) # 예: 'alarm', 'ui'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
