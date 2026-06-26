
import jsonschema
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Placeholder for schema definitions for each endpoint
# In a real implementation, these would be more detailed JSON schemas.
ENDPOINT_SCHEMAS = {
    "/api/code/analyze": {
        "type": "object",
        "properties": {
            "source_code": {"type": "string"},
            "language": {"type": "string"}
        },
        "required": ["source_code", "language"]
    },
    "/api/security/scan-project": {
        "type": "object",
        "properties": {
            "project_id": {"type": "string"}
        },
        "required": ["project_id"]
    },
    "/api/payments/create-subscription": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string", "enum": ["free", "pro", "enterprise"]},
            "payment_method_id": {"type": "string"}
        },
        "required": ["plan_id", "payment_method_id"]
    }
}

class ValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # This is a simplified dispatch. A real implementation would have more robust routing.
        endpoint = request.url.path
        if endpoint in ENDPOINT_SCHEMAS:
            try:
                # Validate request size (conceptual)
                await self.validate_request_size(request, max_size_mb=10) # Default size, should be tier-dependent

                if request.method in ["POST", "PUT", "PATCH"]:
                    # Get JSON body and validate against schema
                    json_body = await request.json()
                    await self.validate_json_schema(json_body, ENDPOINT_SCHEMAS[endpoint])

                    # Sanitize inputs (conceptual)
                    sanitized_body = await self.sanitize_string_inputs(json_body)
                    # A real implementation would need to replace the request body with the sanitized version.

                # File upload validation would be handled differently, likely in the endpoint itself.

            except HTTPException as e:
                return e
            except Exception as e:
                return HTTPException(status_code=400, detail=f"Invalid request: {e}")

        response = await call_next(request)
        return response

    async def validate_request_size(self, request: Request, max_size_mb: int):
        """Validates that the request body size is within the allowed limit."""
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"Request size exceeds limit of {max_size_mb}MB.")
        print(f"Request size for {request.url.path} is within limits.")
        return True

    async def validate_json_schema(self, json_data: dict, schema: dict):
        """Validates a JSON object against a given JSON schema."""
        try:
            jsonschema.validate(instance=json_data, schema=schema)
            print(f"JSON schema validation passed for data: {json_data}")
            return True
        except jsonschema.exceptions.ValidationError as e:
            raise HTTPException(status_code=422, detail=f"Schema validation failed: {e.message}")

    async def sanitize_string_inputs(self, request_data: dict) -> dict:
        """
        Conceptual sanitization. A real implementation would use a library
        like bleach for HTML or handle SQL/XSS prevention more robustly.
        """
        # This is a placeholder for actual sanitization logic.
        print(f"Sanitizing data: {request_data}")
        return request_data

    async def validate_file_upload(self, file_data, allowed_types: list, max_size_mb: int):
        """Validates a file upload based on type and size."""
        # This would be used within an endpoint that handles file uploads.
        if file_data.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {allowed_types}")

        if file_data.size > max_size_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File size exceeds limit of {max_size_mb}MB.")

        print(f"File upload {file_data.filename} validated successfully.")
        return True
