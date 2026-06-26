import json
from datetime import datetime


# This is a placeholder for the AgentSDK, replace with actual import
class AgentSDK:
    def __init__(self):
        print("Initializing mock AgentSDK for audit logging")

    def log_to_firestore(self, collection: str, data: dict):
        # In a real implementation, this would write to Firestore.
        print(f"AUDIT LOG ({collection}): {json.dumps(data)}")

class AuditLogger:
    def __init__(self, sdk: AgentSDK):
        """
        Initializes the audit logger.
        sdk (AgentSDK): The agent SDK for interacting with backend services like Firestore.
        """
        self.sdk = sdk

    async def log_api_access(self, user_id: str, endpoint: str, method: str, status_code: int, response_time_ms: float):
        """Logs an API access event."""
        log_entry = {
            "event_type": "api_access",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
        }
        self.sdk.log_to_firestore("audit_api_access", log_entry)

    async def log_payment_event(self, user_id: str, event_type: str, amount: float, status: str, transaction_id: str = None):
        """Logs a payment-related event."""
        log_entry = {
            "event_type": "payment",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "payment_event": event_type, # e.g., "subscription_created", "payment_failed"
            "amount": amount,
            "status": status,
            "transaction_id": transaction_id,
        }
        self.sdk.log_to_firestore("audit_payment_events", log_entry)

    async def log_security_event(self, user_id: str, event_type: str, severity: str, details: str):
        """Logs a security-related event."""
        log_entry = {
            "event_type": "security",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "security_event": event_type, # e.g., "malware_detected", "xss_attempt"
            "severity": severity,
            "details": details,
        }
        self.sdk.log_to_firestore("audit_security_events", log_entry)

    async def log_auth_failure(self, ip_address: str, attempted_user_id: str, failure_reason: str):
        """Logs a failed authentication attempt."""
        log_entry = {
            "event_type": "authentication_failure",
            "timestamp": datetime.utcnow().isoformat(),
            "ip_address": ip_address,
            "attempted_user_id": attempted_user_id,
            "failure_reason": failure_reason, # e.g., "invalid_password", "expired_token"
        }
        self.sdk.log_to_firestore("audit_auth_failures", log_entry)

    async def log_data_access(self, user_id: str, data_type: str, action: str, resource_id: str):
        """Logs an event related to data access."""
        log_entry = {
            "event_type": "data_access",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data_type": data_type, # e.g., "project", "billing_info"
            "action": action, # e.g., "read", "update", "delete"
            "resource_id": resource_id,
        }
        self.sdk.log_to_firestore("audit_data_access", log_entry)
