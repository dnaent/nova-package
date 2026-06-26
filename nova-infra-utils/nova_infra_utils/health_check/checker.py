"""
Health Check Service - Nova Ecosystem
Provides health monitoring and status checks for all Nova Ecosystem services.
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from flask import Flask, jsonify, request

try:
    from agent_sdk import AgentSDK
except ImportError:
    AgentSDK = None


# Initialize Flask app
app = Flask(__name__)

# Initialize AgentSDK
try:
    sdk = AgentSDK("health_check")
    logger = sdk.logger
except Exception as e:
    # Fallback logging if SDK fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize AgentSDK: {e}")
    sdk = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "health_check",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

@app.route('/', methods=['POST'])
def handle_health_request():
    """Handle Pub/Sub health check requests"""
    try:
        # Verify this is a Pub/Sub push request
        envelope = request.get_json()
        if not envelope:
            logger.warning("No JSON payload received")
            return 'Bad Request: no Pub/Sub message', 400

        # Extract the Pub/Sub message
        if 'message' not in envelope:
            logger.warning("No message field in payload")
            return 'Bad Request: no message field', 400

        pubsub_message = envelope['message']

        # Check for message ID for idempotency
        message_id = pubsub_message.get('messageId', '')
        if sdk and message_id:
            if sdk.check_and_mark_processed(message_id, "health_check_processed"):
                logger.info(f"Message {message_id} already processed, skipping")
                return 'OK', 200

        # Decode message data
        import base64
        if 'data' in pubsub_message:
            message_data = json.loads(base64.b64decode(pubsub_message['data']).decode('utf-8'))
        else:
            logger.error("No data field in Pub/Sub message")
            return 'Bad Request: no data in message', 400

        # Extract request details
        target_service = message_data.get('target_service', 'all')
        request_id = message_data.get('request_id', str(uuid.uuid4()))

        logger.info(f"Processing health check request: request_id={request_id}, target={target_service}")

        # Perform health checks
        health_results = perform_health_checks(target_service)

        # Log results
        if sdk:
            sdk.log_activity(
                action="health_check_performed",
                details=f"Checked {len(health_results)} services",
                metadata={
                    "request_id": request_id,
                    "target_service": target_service,
                    "results": health_results
                }
            )

        # Publish results to metrics topic
        if sdk:
            for service_name, result in health_results.items():
                sdk.publish_metric({
                    "agent_name": "health_check",
                    "service_name": "health_check",
                    "action_type": "monitoring",
                    "action_name": "service_health_check",
                    "duration_ms": result.get("response_time_ms", 0),
                    "status": "success" if result["healthy"] else "error",
                    "metadata": {
                        "target_service": service_name,
                        "request_id": request_id,
                        "health_status": result["status"]
                    }
                })

        return 'OK', 200

    except Exception as e:
        logger.error(f"Error processing health check request: {e}", exc_info=True)
        return f'Internal Server Error: {str(e)}', 500

@app.route('/status', methods=['GET'])
def get_system_status():
    """Get current system status - HTTP endpoint"""
    try:
        health_results = perform_health_checks("all")

        overall_healthy = all(result["healthy"] for result in health_results.values())

        return jsonify({
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": health_results
        }), 200 if overall_healthy else 503

    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        return jsonify({
            "overall_status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

def perform_health_checks(target_service: str) -> Dict[str, Dict[str, Any]]:
    """
    Perform health checks on Nova Ecosystem services.
    """
    # Define service endpoints (these would be actual Cloud Run URLs after deployment)
    services = {
        "agent_orchestrator": os.environ.get("AGENT_ORCHESTRATOR_URL", ""),
        "nova_agent": os.environ.get("NOVA_AGENT_URL", ""),
        "blueprint_distributor": os.environ.get("BLUEPRINT_DISTRIBUTOR_URL", ""),
        "dashboard": os.environ.get("DASHBOARD_URL", ""),
        "terraform_runner": os.environ.get("TERRAFORM_RUNNER_URL", ""),
        "firestore_updater": os.environ.get("FIRESTORE_UPDATER_URL", "")
    }

    results = {}

    # Filter services based on target
    if target_service != "all" and target_service in services:
        services = {target_service: services[target_service]}

    for service_name, service_url in services.items():
        if not service_url:
            results[service_name] = {
                "healthy": False,
                "status": "URL not configured",
                "response_time_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            continue

        try:
            start_time = datetime.now()

            # Make health check request
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{service_url}/health")

            end_time = datetime.now()
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)

            results[service_name] = {
                "healthy": response.status_code == 200,
                "status": f"HTTP {response.status_code}",
                "response_time_ms": response_time_ms,
                "timestamp": end_time.isoformat(),
                "details": response.json() if response.status_code == 200 else None
            }

        except httpx.TimeoutException:
            results[service_name] = {
                "healthy": False,
                "status": "Timeout",
                "response_time_ms": 10000,  # Timeout duration
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            results[service_name] = {
                "healthy": False,
                "status": f"Error: {str(e)}",
                "response_time_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    return results

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
