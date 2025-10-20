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
redis_conn = Redis.from_url(settings.REDIS_URL)

# Create queue
receipt_queue = Queue('receipts', connection=redis_conn)


def enqueue_receipt_processing(
    receipt_id: str,
    storage_key: str,
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Enqueue a receipt processing job"""
    try:
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
