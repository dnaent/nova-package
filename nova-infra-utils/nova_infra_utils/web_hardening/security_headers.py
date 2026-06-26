from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware


class SecurityHeaders:
    def __init__(self, environment="production"):
        """
        Initializes the security headers configuration.
        environment (str): The runtime environment, e.g., "production", "development".
        """
        self.environment = environment

    def get_cors_config(self) -> dict:
        """Returns a CORS configuration dictionary based on the environment."""
        if self.environment == "production":
            # Restrictive policy for production
            return {
                "allow_origins": ["https://your-production-domain.com"],
                "allow_credentials": True,
                "allow_methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["Authorization", "Content-Type"],
            }
        else:
            # More permissive policy for development
            return {
                "allow_origins": ["*"],
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }

    def get_security_headers(self) -> dict:
        """Returns a dictionary of important security headers."""
        return {
            # Prevents clickjacking
            "X-Frame-Options": "DENY",
            # Prevents MIME-sniffing
            "X-Content-Type-Options": "nosniff",
            # Enables XSS filtering in older browsers
            "X-XSS-Protection": "1; mode=block",
            # Enforces HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Content Security Policy (CSP) - this is a restrictive example
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; object-src 'none';"
        }

    def validate_request_origin(self, request: Request):
        """Validates the request's Origin or Referer header."""
        # This is a conceptual check. In a real app, you'd have a more robust
        # list of allowed origins.
        origin = request.headers.get("origin")
        if self.environment == "production" and origin not in self.get_cors_config()["allow_origins"]:
            raise HTTPException(status_code=403, detail="Invalid request origin.")
        print(f"Request origin validated: {origin}")
        return True

def configure_security_middleware(app: FastAPI, environment: str = "production"):
    """
    Applies all security-related middleware to the FastAPI app.
    """
    security = SecurityHeaders(environment)

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        **security.get_cors_config()
    )

    # 2. Middleware to add security headers to every response
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        headers = security.get_security_headers()
        for key, value in headers.items():
            response.headers[key] = value
        return response

    # 3. Middleware for API versioning header (conceptual)
    @app.middleware("http")
    async def add_api_version_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-API-Version"] = "1.0.0"
        return response

    print("Security middleware configured.")
