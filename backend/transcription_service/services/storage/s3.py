"""
AWS S3 Storage Provider
"""
import logging
import boto3
import asyncio
from typing import Optional
from botocore.exceptions import ClientError
from .base import StorageProvider

logger = logging.getLogger(__name__)

class S3StorageProvider(StorageProvider):
    """
    Storage provider that uses Amazon S3.
    """
    
    def __init__(self, bucket_name: str, region_name: str, prefix: str = ""):
        """
        Args:
            bucket_name: S3 bucket name
            region_name: AWS region
            prefix: Optional definition to prefix all keys with (e.g. "screenshots/")
        """
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.prefix = prefix.strip("/") + "/" if prefix else ""
        
        # Initialize boto3 client
        # Note: Boto3 will automatically pick up AWS_ACCESS_KEY_ID etc from env vars
        self.s3_client = boto3.client('s3', region_name=region_name)
        
    def _get_full_key(self, key: str) -> str:
        """Prepend prefix to key if set."""
        if self.prefix and not key.startswith(self.prefix):
            return f"{self.prefix}{key}"
        return key

    async def save(self, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Save file to S3."""
        key = self._get_full_key(filename)
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
            
        try:
            # Run blocking boto3 call in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=data,
                    **extra_args
                )
            )
            return key
        except ClientError as e:
            logger.error(f"Failed to save {key} to S3: {e}")
            raise

    async def get(self, key: str) -> bytes:
        """Retrieve file from S3."""
        # Ensure key has the correct prefix
        full_key = self._get_full_key(key)
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.get_object(Bucket=self.bucket_name, Key=full_key)
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {full_key}")
            logger.error(f"Failed to read {full_key} from S3: {e}")
            raise

    async def delete(self, key: str) -> bool:
        """Delete file from S3."""
        full_key = self._get_full_key(key)
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(Bucket=self.bucket_name, Key=full_key)
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {full_key} from S3: {e}")
            return False

    def get_public_url(self, key: str) -> str:
        """
        Get public URL for the file.
        Uses standard S3 URL format: https://{bucket}.s3.{region}.amazonaws.com/{key}
        """
        full_key = self._get_full_key(key)
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{full_key}"

