"""
Receipt API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
import uuid
import filetype
import hashlib
from datetime import datetime, date
import io

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.receipt import Receipt
from app.schemas.receipt import (
    ReceiptResponse,
    ReceiptUpdate,
    ReceiptUploadResponse,
    ReceiptListResponse
)
from app.services.storage import storage_service
from app.services.queue import enqueue_receipt_processing

router = APIRouter()


@router.post("/upload", response_model=ReceiptUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a receipt image for processing"""
    
    # Validate file size
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Validate file type
    kind = filetype.guess(contents)
    if not kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine file type"
        )
    
    if kind.extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Create receipt record
    receipt = Receipt(
        user_id=current_user.id,
        processing_status="pending",
        original_filename=file.filename,
        file_size=file_size,
        mime_type=kind.mime
    )
    
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    
    try:
        # Generate storage key
        storage_key = f"receipts/{current_user.id}/{receipt.id}.{kind.extension}"
        
        # Upload to storage
        storage_url = await storage_service.upload_file(
            io.BytesIO(contents),
            storage_key,
            content_type=kind.mime,
            metadata={
                "user_id": str(current_user.id),
                "receipt_id": str(receipt.id),
                "original_filename": file.filename
            }
        )
        
        # Update receipt with storage info
        receipt.storage_url = storage_url
        receipt.storage_key = storage_key
        db.commit()
        
        # Enqueue processing job
        job_id = enqueue_receipt_processing(
            receipt_id=str(receipt.id),
            storage_key=storage_key,
            user_id=str(current_user.id),
            metadata={"filename": file.filename}
        )
        
        return ReceiptUploadResponse(
            id=receipt.id,
            message="Receipt uploaded successfully and queued for processing",
            status="pending"
        )
    
    except Exception as e:
        # Cleanup on error
        db.delete(receipt)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload receipt: {str(e)}"
        )


@router.get("", response_model=ReceiptListResponse)
async def list_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    category: Optional[str] = None,
    vendor: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List receipts with filtering and pagination"""
    
    # Base query
    query = db.query(Receipt).filter(Receipt.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Receipt.processing_status == status)
    if category:
        query = query.filter(Receipt.category == category)
    if vendor:
        query = query.filter(Receipt.vendor.ilike(f"%{vendor}%"))
    if start_date:
        query = query.filter(Receipt.date >= start_date)
    if end_date:
        query = query.filter(Receipt.date <= end_date)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    receipts = query.order_by(Receipt.created_at.desc()).offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    # Convert receipts to dict format, then to Pydantic models
    receipts_data = []
    for receipt in receipts:
        receipt_dict = {
            "id": receipt.id,
            "user_id": receipt.user_id,
            "vendor": receipt.vendor,
            "date": receipt.date,
            "total_amount": receipt.total_amount,
            "currency": receipt.currency,
            "tax_amount": receipt.tax_amount,
            "subtotal_amount": receipt.subtotal_amount,
            "category": receipt.category,
            "payment_method": receipt.payment_method,
            "notes": receipt.notes,
            "created_at": receipt.created_at,
            "processed_at": receipt.processed_at,
            "processing_status": receipt.processing_status,
            "storage_url": receipt.storage_url,
            "line_items": receipt.line_items,
            "ocr_text": receipt.ocr_text,
            "checksum": receipt.checksum,
            "model_version": receipt.model_version,
            "confidence": receipt.confidence,
            "original_filename": receipt.original_filename,
            "file_size": receipt.file_size,
            "mime_type": receipt.mime_type,
            "error_message": receipt.error_message
        }
        receipts_data.append(ReceiptResponse(**receipt_dict))
    
    return ReceiptListResponse(
        receipts=receipts_data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get receipt details"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    
    return receipt


@router.put("/{receipt_id}", response_model=ReceiptResponse)
async def update_receipt(
    receipt_id: uuid.UUID,
    receipt_data: ReceiptUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update receipt data"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    
    # Update fields
    update_data = receipt_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(receipt, field, value)
    
    db.commit()
    db.refresh(receipt)
    
    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete receipt"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    
    # Delete from storage
    if receipt.storage_key:
        await storage_service.delete_file(receipt.storage_key)
    
    # Delete from database
    db.delete(receipt)
    db.commit()
    
    return None


@router.post("/{receipt_id}/reprocess", response_model=ReceiptResponse)
async def reprocess_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Reprocess a receipt"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    
    if not receipt.storage_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt has no stored image"
        )
    
    # Reset status
    receipt.processing_status = "pending"
    receipt.error_message = None
    db.commit()
    
    # Enqueue processing job
    enqueue_receipt_processing(
        receipt_id=str(receipt.id),
        storage_key=receipt.storage_key,
        user_id=str(current_user.id),
        metadata={"reprocess": True}
    )
    
    return receipt


@router.get("/{receipt_id}/download")
async def download_receipt(
    receipt_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get presigned URL to download receipt image"""
    receipt = db.query(Receipt).filter(
        Receipt.id == receipt_id,
        Receipt.user_id == current_user.id
    ).first()
    
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    
    if not receipt.storage_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt has no stored image"
        )
    
    # Generate presigned URL (valid for 1 hour)
    url = await storage_service.get_presigned_url(receipt.storage_key, expires=3600)
    
    return {"download_url": url}
