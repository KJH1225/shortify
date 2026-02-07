"""SQLAlchemy ORM models"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from infrastructure.database import Base
from models.schemas import ProcessingStatus


def generate_uuid():
    """Generate UUID string for primary keys"""
    return str(uuid.uuid4())


class Video(Base):
    """Video table"""
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)

    # Source information (JSON-like storage)
    source_type = Column(String(20), nullable=False)  # "file" or "youtube"
    source_url = Column(String(512), nullable=True)
    source_filename = Column(String(255), nullable=True)

    duration = Column(Float, nullable=True)
    status = Column(SQLEnum(ProcessingStatus), nullable=False, default=ProcessingStatus.PENDING)
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

    id = Column(String(36), primary_key=True, default=generate_uuid)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    thumbnail_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="highlights")

    def __repr__(self):
        return f"<Highlight(id={self.id}, video_id={self.video_id}, title={self.title})>"
