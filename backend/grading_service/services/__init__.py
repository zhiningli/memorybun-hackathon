"""
Services package for Grading Service.
"""

from services.redis_client import get_redis_client, initialize_redis, close_redis
from services.result_store import result_store
