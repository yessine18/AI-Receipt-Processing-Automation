"""
Local file storage service (for development without Docker/MinIO)
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)


class LocalStorageService:
    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
    
    async def initialize(self):
        """Initialize local storage - create upload directory"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage initialized: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize local storage: {e}")
            raise
    
    async def upload_file(
        self, 
        file_data: BinaryIO, 
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """Save file locally"""
        try:
            file_path = self.upload_dir / object_name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)
            
            logger.info(f"File saved: {file_path}")
            return str(file_path)
        except Exception as e:
            logger.error(f"File upload error: {e}")
            raise
    
    async def download_file(self, object_name: str) -> bytes:
        """Read file from local storage"""
        try:
            file_path = self.upload_dir / object_name
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"File download error: {e}")
            raise
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete file from local storage"""
        try:
            file_path = self.upload_dir / object_name
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"File deletion error: {e}")
            return False
    
    async def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """Return local file path (no presigned URL for local storage)"""
        file_path = self.upload_dir / object_name
        return str(file_path)
