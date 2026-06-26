import time

import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request


# This is a placeholder for a dependency that would get the current user
# from the auth token.
def get_current_user():
    # In a real app, this would be implemented in auth_middleware.py
    return {"id": "user123", "tier": "professional"}

class RateLimiter:
    # Define rate limits per tier (requests per minute) - Updated to match PRICING_STRATEGY.md
    RATE_LIMITS = {
        "free": (20, 60),        # Free trial: Conservative limits
        "professional": (200, 60), # Professional: 10,000 API calls/month = ~200/minute reasonable rate
        "ultra": (1000, 60),     # Ultra: 50,000 API calls/month = ~1000/minute reasonable rate
        "enterprise": (5000, 60), # Enterprise: Unlimited = high rate limit
        "payment": (5, 60)       # Special case for payment endpoints
    }

    def __init__(self, redis_url: str):
        """
        Initializes the Redis-based rate limiter.
        redis_url (str): The connection URL for the Redis server.
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        print(f"Rate limiter initialized with Redis at {redis_url}")

    async def check_rate_limit(self, user_id: str, endpoint_type: str, tier: str = "free") -> dict:
        """
        Checks if a user has exceeded their rate limit for a given endpoint type.
        Returns a dictionary with rate limit status and headers.
        """
        limit, period = self.RATE_LIMITS.get(tier, self.RATE_LIMITS["free"])
        if endpoint_type == "payment":
            limit, period = self.RATE_LIMITS["payment"]

        current_window = int(time.time() / period)
        key = f"rate_limit:{user_id}:{endpoint_type}:{current_window}"

        current_usage = await self.redis_client.get(key)
        current_usage = int(current_usage) if current_usage else 0

        remaining = limit - current_usage
        reset_time = (current_window + 1) * period
        headers = self.get_rate_limit_headers(limit, remaining, reset_time)

        if current_usage >= limit:
            print(f"Rate limit exceeded for user {user_id} on {endpoint_type} endpoint.")
            raise HTTPException(status_code=429, detail="Too Many Requests", headers=headers)

        print(f"Rate limit check passed for user {user_id}.")
        return headers

    async def increment_usage(self, user_id: str, endpoint_type: str, tier: str = "free"):
        """Increments the usage count for the user."""
        limit, period = self.RATE_LIMITS.get(tier, self.RATE_LIMITS["free"])
        if endpoint_type == "payment":
            limit, period = self.RATE_LIMITS["payment"]

        current_window = int(time.time() / period)
        key = f"rate_limit:{user_id}:{endpoint_type}:{current_window}"

        pipeline = self.redis_client.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, period)
        await pipeline.execute()
        print(f"Incremented usage for user {user_id} on {endpoint_type}.")

    def get_rate_limit_headers(self, limit: int, remaining: int, reset_time: int) -> dict:
        """Returns standard rate limit headers."""
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining - 1)),
            "X-RateLimit-Reset": str(reset_time)
        }

    async def close(self):
        """Closes the Redis connection."""
        await self.redis_client.close()

# Example of how this would be integrated as a FastAPI dependency
async def rate_limit_dependency(request: Request, user: dict = Depends(get_current_user)):
    # In a real app, the redis_url would come from environment configuration
    rate_limiter = RateLimiter(redis_url="redis://localhost:6379")

    endpoint_type = "analysis" # default
    if "/api/payments" in request.url.path:
        endpoint_type = "payment"

    # Check limit and get headers
    headers = await rate_limiter.check_rate_limit(user['id'], endpoint_type, user['tier'])

    # Increment usage *after* the check
    await rate_limiter.increment_usage(user['id'], endpoint_type, user['tier'])

    # A middleware would be required to attach the headers to the outgoing response.
    # This dependency just enforces the limit.
    await rate_limiter.close()
