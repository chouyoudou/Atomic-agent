"""
Redis客户端兼容性包装器
处理不同版本的aioredis兼容性问题
"""

import asyncio
import json
import logging
from typing import Optional, Any, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端包装器"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.url = url
        self.client = None
        self._connected = False

    async def connect(self):
        """连接到Redis"""
        if self._connected:
            return

        try:
            # 尝试导入aioredis
            try:
                import aioredis

                # 检查aioredis版本
                if hasattr(aioredis, 'from_url'):
                    # aioredis 2.x
                    self.client = await aioredis.from_url(
                        self.url,
                        decode_responses=True,
                        encoding='utf-8'
                    )
                else:
                    # aioredis 1.x (fallback)
                    parsed = urlparse(self.url)
                    self.client = await aioredis.create_redis_pool(
                        (parsed.hostname or 'localhost', parsed.port or 6379),
                        encoding='utf-8'
                    )

                # 测试连接
                await self.ping()
                self._connected = True
                logger.info("Redis连接成功")

            except ImportError:
                logger.warning("aioredis未安装，使用模拟Redis客户端")
                self.client = MockRedisClient()
                self._connected = True

        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            logger.info("使用模拟Redis客户端")
            self.client = MockRedisClient()
            self._connected = True

    async def close(self):
        """关闭连接"""
        if self.client and hasattr(self.client, 'close'):
            if hasattr(self.client, 'wait_closed'):
                self.client.close()
                await self.client.wait_closed()
            else:
                await self.client.close()
        self._connected = False

    async def ping(self):
        """测试连接"""
        if hasattr(self.client, 'ping'):
            return await self.client.ping()
        return True

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET失败: {e}")
            return None

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """设置值"""
        try:
            if ex:
                return await self.client.setex(key, ex, value)
            else:
                return await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET失败: {e}")
            return False

    async def setex(self, key: str, seconds: int, value: str):
        """设置带过期时间的值"""
        try:
            return await self.client.setex(key, seconds, value)
        except Exception as e:
            logger.error(f"Redis SETEX失败: {e}")
            return False

    async def delete(self, key: str):
        """删除键"""
        try:
            return await self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE失败: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            result = await self.client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS失败: {e}")
            return False

    async def keys(self, pattern: str = "*"):
        """获取匹配的键"""
        try:
            return await self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS失败: {e}")
            return []

    async def expire(self, key: str, seconds: int):
        """设置过期时间"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE失败: {e}")
            return False


class MockRedisClient:
    """模拟Redis客户端（用于无Redis环境）"""

    def __init__(self):
        self._data = {}
        self._expires = {}
        logger.info("使用内存模拟Redis客户端")

    async def ping(self):
        return "PONG"

    async def get(self, key: str) -> Optional[str]:
        # 检查是否过期
        if key in self._expires:
            import time
            if time.time() > self._expires[key]:
                del self._data[key]
                del self._expires[key]
                return None

        return self._data.get(key)

    async def set(self, key: str, value: str):
        self._data[key] = value
        return True

    async def setex(self, key: str, seconds: int, value: str):
        self._data[key] = value
        import time
        self._expires[key] = time.time() + seconds
        return True

    async def delete(self, key: str):
        deleted = key in self._data
        self._data.pop(key, None)
        self._expires.pop(key, None)
        return 1 if deleted else 0

    async def exists(self, key: str) -> bool:
        # 检查是否过期
        if key in self._expires:
            import time
            if time.time() > self._expires[key]:
                del self._data[key]
                del self._expires[key]
                return False

        return key in self._data

    async def keys(self, pattern: str = "*"):
        import fnmatch
        import time

        # 清理过期键
        expired_keys = []
        for key, expire_time in self._expires.items():
            if time.time() > expire_time:
                expired_keys.append(key)

        for key in expired_keys:
            self._data.pop(key, None)
            self._expires.pop(key, None)

        # 返回匹配的键
        return [key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)]

    async def expire(self, key: str, seconds: int):
        if key in self._data:
            import time
            self._expires[key] = time.time() + seconds
            return True
        return False

    def close(self):
        pass

    async def wait_closed(self):
        pass


# 创建全局Redis客户端实例
redis_client = None


async def get_redis_client(url: str = "redis://localhost:6379") -> RedisClient:
    """获取Redis客户端实例"""
    global redis_client

    if redis_client is None:
        redis_client = RedisClient(url)
        await redis_client.connect()

    return redis_client


async def close_redis_client():
    """关闭Redis客户端"""
    global redis_client

    if redis_client:
        await redis_client.close()
        redis_client = None