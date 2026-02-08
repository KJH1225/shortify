"""SQLAlchemy ORM models"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from infrastructure.database import Base
from models.schemas import ProcessingStatus


class Video(Base):
    """Video table"""
    __tablename__ = "videos"

    id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)

    # Source information (JSON-like storage)
    source_type = Column(String(20), nullable=False)  # "file" or "youtube"
    source_url = Column(String(512), nullable=True)
    source_filename = Column(String(255), nullable=True)

    duration = Column(Float, nullable=True)
    status = Column(
        SQLEnum(ProcessingStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ProcessingStatus.IDLE,
    )
    progress = Column(Integer, default=0)
    message = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    highlights = relationship("Highlight", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, title={self.title}, status={self.status})>"


class Highlight(Base):
    """Highlight table"""
    __tablename__ = "highlights"

    id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
    video_id = Column(MySQLInteger(unsigned=True), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    score = Column(Float, nullable=False)
    thumbnail_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="highlights")

    def __repr__(self):
        return f"<Highlight(id={self.id}, video_id={self.video_id}, title={self.title})>"
