"""
Receipt schemas
"""
from pydantic import BaseModel, UUID4, ConfigDict, Field
from datetime import datetime
from datetime import date as date_type
from typing import Optional, List, Dict, Any
from decimal import Decimal


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None


class ReceiptBase(BaseModel):
    vendor: Optional[str] = None
    date: Optional[date_type] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = "USD"
    tax_amount: Optional[Decimal] = None
    subtotal_amount: Optional[Decimal] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    pass


class ReceiptUpdate(ReceiptBase):
    pass


class ReceiptResponse(ReceiptBase):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True, protected_namespaces=())
    
    id: UUID4
    user_id: UUID4
    created_at: datetime
    processed_at: Optional[datetime] = None
    processing_status: str
    storage_url: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    ocr_text: Optional[str] = None
    checksum: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[Dict[str, Any]] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    error_message: Optional[str] = None


class ReceiptUploadResponse(BaseModel):
    id: UUID4
    message: str
    status: str


class ReceiptListResponse(BaseModel):
    receipts: List[ReceiptResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
