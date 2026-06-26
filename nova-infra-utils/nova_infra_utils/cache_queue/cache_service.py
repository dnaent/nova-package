import json

import redis.asyncio as redis


class CacheService:
    def __init__(self, redis_url: str):
        """
        Initializes the Redis-based caching service.
        redis_url (str): The connection URL for the Redis server.
        """
        # Use from_url to easily connect to Redis
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        print(f"Cache service initialized with Redis at {redis_url}")

    async def get_analysis_result(self, project_id: str, code_hash: str) -> dict | None:
        """
        Retrieves a cached code analysis result.
        Returns the result as a dictionary or None if not found.
        """
        cache_key = f"analysis:{project_id}:{code_hash}"
        print(f"Checking cache for key: {cache_key}")
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            print("Cache hit.")
            return json.loads(cached_result)
        print("Cache miss.")
        return None

    async def store_analysis_result(self, project_id: str, code_hash: str, results: dict, ttl: int = 86400):
        """
        Stores a code analysis result in the cache.
        ttl (int): Time-to-live for the cache entry in seconds. Defaults to 24 hours.
        """
        cache_key = f"analysis:{project_id}:{code_hash}"
        print(f"Storing result in cache with key: {cache_key}, TTL: {ttl}s")
        await self.redis_client.set(cache_key, json.dumps(results), ex=ttl)

    async def get_security_scan(self, project_id: str, scan_hash: str) -> dict | None:
        """
        Retrieves a cached security scan result.
        Returns the result as a dictionary or None if not found.
        """
        cache_key = f"security:{project_id}:{scan_hash}"
        print(f"Checking cache for key: {cache_key}")
        cached_result = await self.redis_client.get(cache_key)
        if cached_result:
            print("Cache hit.")
            return json.loads(cached_result)
        print("Cache miss.")
        return None

    async def store_security_scan(self, project_id: str, scan_hash: str, results: dict, ttl: int = 43200):
        """
        Stores a security scan result in the cache.
        ttl (int): Time-to-live for the cache entry in seconds. Defaults to 12 hours.
        """
        cache_key = f"security:{project_id}:{scan_hash}"
        print(f"Storing result in cache with key: {cache_key}, TTL: {ttl}s")
        await self.redis_client.set(cache_key, json.dumps(results), ex=ttl)

    async def invalidate_project_cache(self, project_id: str):
        """
        Invalidates all cache entries associated with a specific project_id.
        Uses Redis SCAN to find all relevant keys without blocking the server.
        """
        print(f"Invalidating cache for project_id: {project_id}")
        # Invalidate analysis results
        async for key in self.redis_client.scan_iter(f"analysis:{project_id}:*"):
            await self.redis_client.delete(key)
        # Invalidate security scans
        async for key in self.redis_client.scan_iter(f"security:{project_id}:*"):
            await self.redis_client.delete(key)
        print(f"Cache invalidated for project {project_id}.")

    async def close(self):
        """Closes the Redis connection."""
        await self.redis_client.close()
