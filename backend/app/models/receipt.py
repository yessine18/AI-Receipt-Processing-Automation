"""
Receipt model
"""
from sqlalchemy import Column, String, DateTime, Numeric, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Receipt(Base):
    __tablename__ = "receipts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Processing status
    processing_status = Column(String(20), default="pending", nullable=False)
    # Status values: pending, processing, done, error
    
    # Storage
    storage_url = Column(Text, nullable=True)
    storage_key = Column(String, nullable=True)
    
    # Receipt data
    vendor = Column(Text, nullable=True)
    date = Column(Date, nullable=True)
    total_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=True)
    tax_amount = Column(Numeric(10, 2), nullable=True)
    subtotal_amount = Column(Numeric(10, 2), nullable=True)
    category = Column(Text, nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    # Raw data
    line_items = Column(JSONB, nullable=True)
    ocr_text = Column(Text, nullable=True)
    
    # Metadata
    checksum = Column(String, unique=True, nullable=True)
    model_version = Column(String(50), nullable=True)
    confidence = Column(JSONB, nullable=True)
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Original filename
    original_filename = Column(String, nullable=True)
    file_size = Column(Numeric, nullable=True)
    mime_type = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="receipts")
