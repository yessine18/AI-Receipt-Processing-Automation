"""
Background task for processing receipts
"""
import logging
import hashlib
import asyncio
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.receipt import Receipt
from app.services.storage import storage_service
from app.services.ocr import ocr_service
from app.services.gemini import gemini_service

logger = logging.getLogger(__name__)


async def process_receipt_task_async(receipt_id: str, storage_key: str, user_id: str, metadata: dict):
    """
    Async version of receipt processing task for synchronous execution
    
    Steps:
    1. Download image from storage
    2. Calculate checksum for duplicate detection
    3. Preprocess image
    4. Run OCR
    5. Extract structured data with Gemini
    6. Validate and normalize data
    7. Update database
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Processing receipt {receipt_id} (async)")
        
        # Get receipt from database
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise ValueError(f"Receipt {receipt_id} not found")
        
        # Update status to processing
        receipt.processing_status = "processing"
        db.commit()
        
        # Download image from storage (async call)
        logger.info(f"Downloading image from storage: {storage_key}")
        image_data = await storage_service.download_file(storage_key)
        
        # Calculate checksum for duplicate detection
        checksum = hashlib.sha256(image_data).hexdigest()
        
        # Check for duplicates
        existing = db.query(Receipt).filter(
            Receipt.checksum == checksum,
            Receipt.id != receipt_id
        ).first()
        
        if existing:
            logger.warning(f"Duplicate receipt detected: {checksum}")
            receipt.processing_status = "error"
            receipt.error_message = f"Duplicate of receipt {existing.id}"
            db.commit()
            return {"status": "duplicate", "duplicate_of": str(existing.id)}
        
        receipt.checksum = checksum
        
        # Run OCR
        logger.info("Running OCR...")
        ocr_result = ocr_service.extract_text(image_data)
        receipt.ocr_text = ocr_result["text"]
        
        # Extract structured data with Gemini
        logger.info("Extracting data with Gemini...")
        try:
            extracted_data = gemini_service.extract_hybrid(image_data, ocr_result["text"])
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            extracted_data = gemini_service.extract_from_text(ocr_result["text"])
        
        # Normalize and validate data
        logger.info("Normalizing data...")
        normalized_data = normalize_receipt_data(extracted_data)
        
        # Update receipt with extracted data
        receipt.vendor = normalized_data.get("vendor")
        receipt.date = normalized_data.get("date")
        receipt.total_amount = normalized_data.get("total_amount")
        receipt.currency = normalized_data.get("currency", "USD")
        receipt.tax_amount = normalized_data.get("tax_amount")
        receipt.subtotal_amount = normalized_data.get("subtotal_amount")
        receipt.category = normalized_data.get("category")
        receipt.payment_method = normalized_data.get("payment_method")
        receipt.line_items = normalized_data.get("line_items")
        receipt.confidence = normalized_data.get("confidence_scores")
        receipt.model_version = f"gemini-{gemini_service.model_name}"
        receipt.processing_status = "done"
        receipt.processed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Receipt {receipt_id} processed successfully")
        
        return {
            "status": "success",
            "receipt_id": receipt_id,
            "vendor": receipt.vendor,
            "total": float(receipt.total_amount) if receipt.total_amount else None
        }
    
    except Exception as e:
        logger.error(f"Receipt processing error: {e}", exc_info=True)
        
        try:
            receipt.processing_status = "error"
            receipt.error_message = str(e)
            receipt.processed_at = datetime.utcnow()
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update receipt error status: {db_error}")
        
        raise
    
    finally:
        db.close()


def process_receipt_task(receipt_id: str, storage_key: str, user_id: str, metadata: dict):
    """
    Main receipt processing task
    
    Steps:
    1. Download image from storage
    2. Calculate checksum for duplicate detection
    3. Preprocess image
    4. Run OCR
    5. Extract structured data with Gemini
    6. Validate and normalize data
    7. Update database
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Processing receipt {receipt_id}")
        
        # Get receipt from database
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not receipt:
            raise ValueError(f"Receipt {receipt_id} not found")
        
        # Update status to processing
        receipt.processing_status = "processing"
        db.commit()
        
        # Download image from storage (async call)
        logger.info(f"Downloading image from storage: {storage_key}")
        image_data = asyncio.run(storage_service.download_file(storage_key))
        
        # Calculate checksum for duplicate detection
        checksum = hashlib.sha256(image_data).hexdigest()
        
        # Check for duplicates
        existing = db.query(Receipt).filter(
            Receipt.checksum == checksum,
            Receipt.id != receipt_id
        ).first()
        
        if existing:
            logger.warning(f"Duplicate receipt detected: {checksum}")
            receipt.processing_status = "error"
            receipt.error_message = f"Duplicate of receipt {existing.id}"
            # Don't set checksum to avoid unique constraint violation
            db.commit()
            return {"status": "duplicate", "duplicate_of": str(existing.id)}
        
        receipt.checksum = checksum
        
        # Run OCR
        logger.info("Running OCR...")
        ocr_result = ocr_service.extract_text(image_data)
        receipt.ocr_text = ocr_result["text"]
        
        # Extract structured data with Gemini
        logger.info("Extracting data with Gemini...")
        try:
            # Use hybrid approach for best results
            extracted_data = gemini_service.extract_hybrid(image_data, ocr_result["text"])
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            # Fallback to OCR-only
            extracted_data = gemini_service.extract_from_text(ocr_result["text"])
        
        # Normalize and validate data
        logger.info("Normalizing data...")
        normalized_data = normalize_receipt_data(extracted_data)
        
        # Update receipt with extracted data
        receipt.vendor = normalized_data.get("vendor")
        receipt.date = normalized_data.get("date")
        receipt.total_amount = normalized_data.get("total_amount")
        receipt.currency = normalized_data.get("currency", "USD")
        receipt.tax_amount = normalized_data.get("tax_amount")
        receipt.subtotal_amount = normalized_data.get("subtotal_amount")
        receipt.category = normalized_data.get("category")
        receipt.payment_method = normalized_data.get("payment_method")
        receipt.line_items = normalized_data.get("line_items")
        receipt.confidence = normalized_data.get("confidence_scores")
        receipt.model_version = f"gemini-{gemini_service.model_name}"
        receipt.processing_status = "done"
        receipt.processed_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Receipt {receipt_id} processed successfully")
        
        return {
            "status": "success",
            "receipt_id": receipt_id,
            "vendor": receipt.vendor,
            "total": float(receipt.total_amount) if receipt.total_amount else None
        }
    
    except Exception as e:
        logger.error(f"Receipt processing error: {e}", exc_info=True)
        
        # Update receipt with error
        try:
            receipt.processing_status = "error"
            receipt.error_message = str(e)
            receipt.processed_at = datetime.utcnow()
            db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update receipt error status: {db_error}")
        
        raise
    
    finally:
        db.close()


def normalize_receipt_data(data: dict) -> dict:
    """
    Normalize and validate extracted receipt data
    """
    from dateutil import parser
    
    normalized = {}
    
    # Vendor
    if data.get("vendor"):
        normalized["vendor"] = str(data["vendor"]).strip()
    
    # Date
    if data.get("date"):
        try:
            if isinstance(data["date"], str):
                # Parse date string
                date_obj = parser.parse(data["date"])
                normalized["date"] = date_obj.date()
            else:
                normalized["date"] = data["date"]
        except Exception as e:
            logger.warning(f"Failed to parse date: {e}")
    
    # Amounts
    for field in ["total_amount", "tax_amount", "subtotal_amount"]:
        if data.get(field) is not None:
            try:
                normalized[field] = Decimal(str(data[field]))
            except Exception as e:
                logger.warning(f"Failed to parse {field}: {e}")
    
    # Currency
    if data.get("currency"):
        currency = str(data["currency"]).upper()
        # Validate ISO 4217 currency code (basic check)
        if len(currency) == 3 and currency.isalpha():
            normalized["currency"] = currency
        else:
            normalized["currency"] = "USD"  # Default
    
    # Category
    if data.get("category"):
        normalized["category"] = str(data["category"]).strip().lower()
    
    # Payment method
    if data.get("payment_method"):
        normalized["payment_method"] = str(data["payment_method"]).strip().lower()
    
    # Line items
    if data.get("line_items"):
        normalized["line_items"] = data["line_items"]
    
    # Confidence scores
    if data.get("confidence_scores"):
        normalized["confidence_scores"] = data["confidence_scores"]
    
    return normalized
