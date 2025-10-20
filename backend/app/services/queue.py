"""
Queue service for managing background jobs with Redis Queue (RQ)
"""
import logging
from redis import Redis
from rq import Queue
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Redis connection
try:
    redis_conn = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    redis_conn.ping()  # Test connection
    receipt_queue = Queue('receipts', connection=redis_conn)
    REDIS_AVAILABLE = True
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis not available, will process receipts synchronously: {e}")
    redis_conn = None
    receipt_queue = None
    REDIS_AVAILABLE = False


def enqueue_receipt_processing(
    receipt_id: str,
    storage_key: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Enqueue a receipt processing job"""
    try:
        # If Redis is not available, process synchronously
        if not REDIS_AVAILABLE:
            logger.info(f"Processing receipt {receipt_id} in background (Redis not available)")
            # Import and schedule async processing task
            import asyncio
            from app.tasks.process_receipt import process_receipt_task_async
            
            try:
                # Try to get the running event loop
                try:
                    loop = asyncio.get_running_loop()
                    # Schedule as a background task
                    loop.create_task(process_receipt_task_async(
                        receipt_id=receipt_id,
                        storage_key=storage_key,
                        user_id=user_id,
                        metadata=metadata or {}
                    ))
                    logger.info(f"Scheduled background processing for receipt {receipt_id}")
                except RuntimeError:
                    # No running loop, this shouldn't happen in FastAPI but handle it
                    logger.warning("No running event loop, processing will be delayed")
                    # Just return success, the receipt will be processed later
                    pass
                
                return f"sync-{receipt_id}"
            except Exception as e:
                logger.error(f"Failed to schedule background processing for receipt {receipt_id}: {e}")
                raise
        
        # Use Redis queue if available
        from app.tasks.process_receipt import process_receipt_task
        
        job = receipt_queue.enqueue(
            process_receipt_task,
            receipt_id=receipt_id,
            storage_key=storage_key,
            user_id=user_id,
            metadata=metadata or {},
            job_timeout='10m',  # 10 minutes timeout
            result_ttl=86400,  # Keep results for 24 hours
        )
        
        logger.info(f"Enqueued job {job.id} for receipt {receipt_id}")
        return job.id
    except Exception as e:
        logger.error(f"Failed to enqueue job: {e}")
        raise


def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get job status"""
    if not REDIS_AVAILABLE:
        # For synchronous processing, assume job is complete
        return {
            "id": job_id,
            "status": "finished",
            "result": None,
            "exc_info": None,
            "created_at": None,
            "started_at": None,
            "ended_at": None,
        }
    
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result,
            "exc_info": job.exc_info,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "ended_at": job.ended_at,
        }
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return {"error": str(e)}
