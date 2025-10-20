"""
Admin API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, datetime
import csv
import io

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.receipt import Receipt
from app.schemas.receipt import ReceiptListResponse

router = APIRouter()


@router.get("/receipts", response_model=ReceiptListResponse)
async def admin_list_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: List all receipts"""
    query = db.query(Receipt)
    
    if status:
        query = query.filter(Receipt.processing_status == status)
    if user_id:
        query = query.filter(Receipt.user_id == user_id)
    
    total = query.count()
    offset = (page - 1) * page_size
    receipts = query.order_by(Receipt.created_at.desc()).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return ReceiptListResponse(
        receipts=receipts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Get system statistics"""
    total_users = db.query(func.count(User.id)).scalar()
    total_receipts = db.query(func.count(Receipt.id)).scalar()
    
    receipts_by_status = db.query(
        Receipt.processing_status,
        func.count(Receipt.id)
    ).group_by(Receipt.processing_status).all()
    
    status_counts = {status: count for status, count in receipts_by_status}
    
    return {
        "total_users": total_users,
        "total_receipts": total_receipts,
        "receipts_by_status": status_counts
    }


@router.get("/export")
async def export_receipts(
    format: str = Query("csv", regex="^(csv|json)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Admin: Export receipts to CSV or JSON"""
    query = db.query(Receipt)
    
    if start_date:
        query = query.filter(Receipt.date >= start_date)
    if end_date:
        query = query.filter(Receipt.date <= end_date)
    
    receipts = query.all()
    
    if format == "csv":
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "ID", "User ID", "Vendor", "Date", "Total Amount", 
            "Currency", "Tax Amount", "Category", "Status", "Created At"
        ])
        
        # Data
        for r in receipts:
            writer.writerow([
                str(r.id), str(r.user_id), r.vendor, r.date,
                r.total_amount, r.currency, r.tax_amount,
                r.category, r.processing_status, r.created_at
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=receipts.csv"}
        )
    
    else:  # JSON
        from fastapi.responses import JSONResponse
        
        data = [{
            "id": str(r.id),
            "user_id": str(r.user_id),
            "vendor": r.vendor,
            "date": str(r.date) if r.date else None,
            "total_amount": float(r.total_amount) if r.total_amount else None,
            "currency": r.currency,
            "tax_amount": float(r.tax_amount) if r.tax_amount else None,
            "category": r.category,
            "status": r.processing_status,
            "created_at": r.created_at.isoformat()
        } for r in receipts]
        
        return JSONResponse(content=data)
