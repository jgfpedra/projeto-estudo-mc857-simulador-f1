"""Redis clients with optional Sentinel discovery; single Redis remains the default."""
import os

import redis
import redis.asyncio as aioredis
from redis.sentinel import Sentinel
from redis.asyncio.sentinel import Sentinel as AsyncSentinel


def _sentinels():
    value = os.environ.get('REDIS_SENTINELS', '')
    if not value:
        return []
    result = []
    for item in value.split(','):
        host, port = item.strip().rsplit(':', 1)
        result.append((host, int(port)))
    return result


def sync_client(url):
    sentinels = _sentinels()
    if not sentinels:
        return redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
    sentinel = Sentinel(sentinels, socket_timeout=2, decode_responses=True)
    return sentinel.master_for(os.environ.get('REDIS_SENTINEL_MASTER', 'mymaster'),
                               socket_timeout=2, socket_connect_timeout=2, decode_responses=True)


def async_client(url):
    sentinels = _sentinels()
    if not sentinels:
        return aioredis.from_url(url, decode_responses=True, socket_connect_timeout=2)
    sentinel = AsyncSentinel(sentinels, socket_timeout=2, decode_responses=True)
    return sentinel.master_for(os.environ.get('REDIS_SENTINEL_MASTER', 'mymaster'),
                               socket_timeout=None, socket_connect_timeout=2, decode_responses=True)
