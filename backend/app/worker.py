"""
Worker process for background tasks
"""
import logging
import asyncio
from rq import Worker, Queue, Connection, SimpleWorker
from app.services.queue import redis_conn
from app.services.storage import storage_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WindowsDeathPenalty:
    """Windows-compatible death penalty that doesn't use signals"""
    def __init__(self, timeout, exception, **kwargs):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == '__main__':
    logger.info("Starting receipt processing worker (Windows mode)...")
    
    # Initialize storage service
    logger.info("Initializing storage service...")
    asyncio.run(storage_service.initialize())
    
    with Connection(redis_conn):
        # Use SimpleWorker for Windows compatibility (no forking)
        # Disable timeout mechanism for Windows (no SIGALRM support)
        worker = SimpleWorker(['receipts'], connection=redis_conn)
        worker.death_penalty_class = WindowsDeathPenalty
        worker.work()
