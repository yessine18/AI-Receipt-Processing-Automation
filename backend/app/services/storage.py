"""
Storage service for managing receipt images
Supports MinIO, AWS S3, and Local File Storage
"""
import io
import logging
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.services.local_storage import LocalStorageService

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.client = None
        self.bucket = None
    
    async def initialize(self):
        """Initialize storage client"""
        if self.storage_type == "local":
            await self._initialize_local()
        elif self.storage_type == "minio":
            await self._initialize_minio()
        elif self.storage_type == "s3":
            await self._initialize_s3()
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    async def _initialize_local(self):
        """Initialize local file storage"""
        try:
            self.client = LocalStorageService(settings.UPLOAD_DIR)
            await self.client.initialize()
            logger.info("Local storage initialized")
        except Exception as e:
            logger.error(f"Local storage initialization error: {e}")
            raise
    
    async def _initialize_minio(self):
        """Initialize MinIO client"""
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            self.bucket = settings.MINIO_BUCKET
            
            # Create bucket if it doesn't exist
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
            
            logger.info("MinIO storage initialized")
        except S3Error as e:
            logger.error(f"MinIO initialization error: {e}")
            raise
    
    async def _initialize_s3(self):
        """Initialize AWS S3 client"""
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket = settings.S3_BUCKET
            logger.info("AWS S3 storage initialized")
        except ClientError as e:
            logger.error(f"S3 initialization error: {e}")
            raise
    
    async def upload_file(
        self, 
        file_data: BinaryIO, 
        object_name: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict] = None
    ) -> str:
        """Upload file to storage"""
        try:
            if self.storage_type == "local":
                return await self.client.upload_file(file_data, object_name, content_type, metadata)
            elif self.storage_type == "minio":
                return await self._upload_to_minio(file_data, object_name, content_type, metadata)
            elif self.storage_type == "s3":
                return await self._upload_to_s3(file_data, object_name, content_type, metadata)
        except Exception as e:
            logger.error(f"File upload error: {e}")
            raise
    
    async def _upload_to_minio(
        self, 
        file_data: BinaryIO, 
        object_name: str,
        content_type: str,
        metadata: Optional[dict]
    ) -> str:
        """Upload to MinIO"""
        # Get file size
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning
        
        self.client.put_object(
            self.bucket,
            object_name,
            file_data,
            file_size,
            content_type=content_type,
            metadata=metadata or {}
        )
        
        # Generate URL
        url = f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}/{self.bucket}/{object_name}"
        logger.info(f"Uploaded to MinIO: {object_name}")
        return url
    
    async def _upload_to_s3(
        self, 
        file_data: BinaryIO, 
        object_name: str,
        content_type: str,
        metadata: Optional[dict]
    ) -> str:
        """Upload to AWS S3"""
        extra_args = {
            'ContentType': content_type,
        }
        if metadata:
            extra_args['Metadata'] = metadata
        
        self.client.upload_fileobj(
            file_data,
            self.bucket,
            object_name,
            ExtraArgs=extra_args
        )
        
        url = f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{object_name}"
        logger.info(f"Uploaded to S3: {object_name}")
        return url
    
    async def download_file(self, object_name: str) -> bytes:
        """Download file from storage"""
        try:
            if self.storage_type == "local":
                return await self.client.download_file(object_name)
            elif self.storage_type == "minio":
                return await self._download_from_minio(object_name)
            elif self.storage_type == "s3":
                return await self._download_from_s3(object_name)
        except Exception as e:
            logger.error(f"File download error: {e}")
            raise
    
    async def _download_from_minio(self, object_name: str) -> bytes:
        """Download from MinIO"""
        response = self.client.get_object(self.bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    
    async def _download_from_s3(self, object_name: str) -> bytes:
        """Download from AWS S3"""
        buffer = io.BytesIO()
        self.client.download_fileobj(self.bucket, object_name, buffer)
        buffer.seek(0)
        return buffer.read()
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete file from storage"""
        try:
            if self.storage_type == "local":
                return await self.client.delete_file(object_name)
            elif self.storage_type == "minio":
                self.client.remove_object(self.bucket, object_name)
            elif self.storage_type == "s3":
                self.client.delete_object(Bucket=self.bucket, Key=object_name)
            
            logger.info(f"Deleted from storage: {object_name}")
            return True
        except Exception as e:
            logger.error(f"File deletion error: {e}")
            return False
    
    async def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """Generate presigned URL for temporary access"""
        try:
            if self.storage_type == "local":
                return await self.client.get_presigned_url(object_name, expires)
            elif self.storage_type == "minio":
                from datetime import timedelta
                url = self.client.presigned_get_object(
                    self.bucket, 
                    object_name,
                    expires=timedelta(seconds=expires)
                )
            elif self.storage_type == "s3":
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': object_name},
                    ExpiresIn=expires
                )
            
            return url
        except Exception as e:
            logger.error(f"Presigned URL generation error: {e}")
            raise


# Global storage service instance
storage_service = StorageService()
