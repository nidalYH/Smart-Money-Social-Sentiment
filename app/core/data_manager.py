"""
Data management and caching module
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import AsyncSessionLocal, check_db_connection

logger = logging.getLogger(__name__)


class DataManager:
    """Centralized data management with caching and database operations"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        
    async def initialize(self):
        """Initialize data manager with Redis connection"""
        try:
            # Try to connect to Redis, but don't fail if it's not available
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("Data manager initialized with Redis successfully")
        except Exception as e:
            logger.warning(f"Redis not available, running without cache: {e}")
            self.redis_client = None
            self.is_connected = False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    @asynccontextmanager
    async def get_db_session(self):
        """Get database session with proper cleanup"""
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def check_health(self) -> Dict[str, bool]:
        """Check health of database and Redis connections"""
        db_healthy = await check_db_connection()
        redis_healthy = False
        
        if self.redis_client:
            try:
                await self.redis_client.ping()
                redis_healthy = True
            except Exception:
                redis_healthy = False
        
        return {
            "database": db_healthy,
            "redis": redis_healthy,
            "overall": db_healthy and redis_healthy
        }
    
    # Redis caching methods
    async def cache_data(self, key: str, data: Any, ttl: int = None) -> bool:
        """Cache data in Redis"""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            if ttl is None:
                ttl = settings.cache_ttl
            
            # Serialize data
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data, default=str)
            else:
                serialized_data = str(data)
            
            await self.redis_client.setex(key, ttl, serialized_data)
            return True
            
        except Exception as e:
            logger.error(f"Error caching data for key {key}: {e}")
            return False
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data from Redis"""
        if not self.is_connected or not self.redis_client:
            return None
        
        try:
            data = await self.redis_client.get(key)
            if data:
                # Try to deserialize as JSON first, fallback to string
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data.decode('utf-8')
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data for key {key}: {e}")
            return None
    
    async def delete_cached_data(self, key: str) -> bool:
        """Delete cached data from Redis"""
        if not self.is_connected or not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cached data for key {key}: {e}")
            return False
    
    async def cache_with_pattern(self, pattern: str, data: Any, ttl: int = None) -> str:
        """Cache data with timestamp pattern"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = f"{pattern}:{timestamp}"
        await self.cache_data(key, data, ttl)
        return key
    
    async def get_latest_cached_data(self, pattern: str) -> Optional[Any]:
        """Get latest cached data by pattern"""
        if not self.is_connected or not self.redis_client:
            return None
        
        try:
            # Get all keys matching pattern
            keys = await self.redis_client.keys(f"{pattern}:*")
            if not keys:
                return None
            
            # Sort by timestamp (newest first)
            keys.sort(reverse=True)
            
            # Get the latest data
            data = await self.redis_client.get(keys[0])
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data.decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest cached data for pattern {pattern}: {e}")
            return None
    
    # Rate limiting
    async def check_rate_limit(self, key: str, limit: int, window: int = 3600) -> bool:
        """Check if rate limit is exceeded"""
        if not self.is_connected or not self.redis_client:
            return True  # Allow if Redis is down
        
        try:
            current_time = int(datetime.utcnow().timestamp())
            window_start = current_time - window
            
            # Remove old entries
            await self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            count = await self.redis_client.zcard(key)
            
            if count >= limit:
                return False  # Rate limit exceeded
            
            # Add current request
            await self.redis_client.zadd(key, {str(current_time): current_time})
            await self.redis_client.expire(key, window)
            
            return True  # Within rate limit
            
        except Exception as e:
            logger.error(f"Error checking rate limit for key {key}: {e}")
            return True  # Allow on error
    
    # Data validation and cleaning
    def validate_token_address(self, address: str) -> bool:
        """Validate Ethereum token address format"""
        if not address:
            return False
        
        # Basic Ethereum address validation
        if not address.startswith("0x"):
            return False
        
        if len(address) != 42:
            return False
        
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    def clean_token_symbol(self, symbol: str) -> str:
        """Clean and normalize token symbol"""
        if not symbol:
            return "UNKNOWN"
        
        # Remove whitespace and convert to uppercase
        cleaned = symbol.strip().upper()
        
        # Remove invalid characters
        cleaned = ''.join(c for c in cleaned if c.isalnum())
        
        return cleaned[:20]  # Limit length
    
    def validate_price_data(self, data: Dict) -> bool:
        """Validate price data structure"""
        required_fields = ["price_usd", "timestamp"]
        
        for field in required_fields:
            if field not in data:
                return False
        
        try:
            float(data["price_usd"])
            datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
            return True
        except (ValueError, TypeError):
            return False
    
    # Batch operations
    async def batch_insert(self, model_class, data_list: List[Dict]) -> bool:
        """Batch insert data into database"""
        try:
            async with self.get_db_session() as session:
                objects = [model_class(**data) for data in data_list]
                session.add_all(objects)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            return False
    
    async def batch_update(self, model_class, updates: List[Dict], filter_field: str) -> bool:
        """Batch update records in database"""
        try:
            async with self.get_db_session() as session:
                for update_data in updates:
                    filter_value = update_data.pop(filter_field)
                    stmt = update(model_class).where(
                        getattr(model_class, filter_field) == filter_value
                    ).values(**update_data)
                    await session.execute(stmt)
                
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            return False
    
    # Data aggregation
    async def get_aggregated_data(self, model_class, 
                                group_by: str, 
                                agg_fields: Dict[str, str],
                                filters: Dict = None,
                                limit: int = 1000) -> List[Dict]:
        """Get aggregated data from database"""
        try:
            async with self.get_db_session() as session:
                # Build query
                stmt = select(model_class)
                
                # Apply filters
                if filters:
                    for field, value in filters.items():
                        if hasattr(model_class, field):
                            stmt = stmt.where(getattr(model_class, field) == value)
                
                # Execute query
                result = await session.execute(stmt.limit(limit))
                records = result.scalars().all()
                
                # Group and aggregate data
                grouped_data = {}
                for record in records:
                    group_key = getattr(record, group_by)
                    if group_key not in grouped_data:
                        grouped_data[group_key] = {}
                    
                    # Apply aggregations
                    for field, agg_type in agg_fields.items():
                        if hasattr(record, field):
                            value = getattr(record, field)
                            agg_key = f"{field}_{agg_type}"
                            
                            if agg_key not in grouped_data[group_key]:
                                if agg_type == "sum":
                                    grouped_data[group_key][agg_key] = 0
                                elif agg_type == "avg":
                                    grouped_data[group_key][agg_key] = []
                                elif agg_type == "count":
                                    grouped_data[group_key][agg_key] = 0
                                elif agg_type == "max":
                                    grouped_data[group_key][agg_key] = float('-inf')
                                elif agg_type == "min":
                                    grouped_data[group_key][agg_key] = float('inf')
                            
                            # Apply aggregation
                            if agg_type == "sum":
                                grouped_data[group_key][agg_key] += float(value or 0)
                            elif agg_type == "avg":
                                grouped_data[group_key][agg_key].append(float(value or 0))
                            elif agg_type == "count":
                                grouped_data[group_key][agg_key] += 1
                            elif agg_type == "max":
                                grouped_data[group_key][agg_key] = max(
                                    grouped_data[group_key][agg_key], float(value or 0)
                                )
                            elif agg_type == "min":
                                grouped_data[group_key][agg_key] = min(
                                    grouped_data[group_key][agg_key], float(value or 0)
                                )
                
                # Finalize averages
                for group_key in grouped_data:
                    for agg_key, agg_type in agg_fields.items():
                        if agg_type == "avg":
                            values = grouped_data[group_key][f"{agg_key}_avg"]
                            if values:
                                grouped_data[group_key][f"{agg_key}_avg"] = sum(values) / len(values)
                            else:
                                grouped_data[group_key][f"{agg_key}_avg"] = 0
                
                # Convert to list
                result_list = []
                for group_key, data in grouped_data.items():
                    result_list.append({
                        group_by: group_key,
                        **data
                    })
                
                return result_list
                
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return []
    
    # Data export
    async def export_data(self, model_class, filters: Dict = None, 
                         limit: int = 10000) -> List[Dict]:
        """Export data to dictionary format"""
        try:
            async with self.get_db_session() as session:
                stmt = select(model_class)
                
                # Apply filters
                if filters:
                    for field, value in filters.items():
                        if hasattr(model_class, field):
                            stmt = stmt.where(getattr(model_class, field) == value)
                
                result = await session.execute(stmt.limit(limit))
                records = result.scalars().all()
                
                # Convert to dictionaries
                return [self._model_to_dict(record) for record in records]
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return []
    
    def _model_to_dict(self, model_instance) -> Dict:
        """Convert SQLAlchemy model to dictionary"""
        result = {}
        for column in model_instance.__table__.columns:
            value = getattr(model_instance, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result
    
    # Performance monitoring
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for data operations"""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "redis_connected": self.is_connected,
            "cache_hit_rate": 0.0,
            "avg_response_time": 0.0,
            "total_operations": 0,
            "error_rate": 0.0
        }
        
        if self.redis_client and self.is_connected:
            try:
                info = await self.redis_client.info()
                metrics.update({
                    "redis_memory_usage": info.get("used_memory_human", "0B"),
                    "redis_connected_clients": info.get("connected_clients", 0),
                    "redis_total_commands_processed": info.get("total_commands_processed", 0),
                })
            except Exception as e:
                logger.error(f"Error getting Redis info: {e}")
        
        return metrics


