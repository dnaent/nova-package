"""
Firestore Updater Service - Nova Ecosystem
Handles Firestore updates via Pub/Sub messages from other services.
Converted from Cloud Functions to Cloud Run for consistency.
"""

import base64
import json
import logging
import os
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from google.api_core import exceptions as google_exceptions
from google.cloud import firestore

try:
    from agent_sdk import AgentSDK
except ImportError:
    # Standalone fallback if SDK is not installed globally
    AgentSDK = None


# Initialize Flask app
app = Flask(__name__)

# Initialize AgentSDK
try:
    sdk = AgentSDK("firestore_updater")
    logger = sdk.logger
except Exception as e:
    # Fallback logging if SDK fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize AgentSDK: {e}")
    sdk = None

# Initialize Firestore client globally
try:
    PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT')
    if not PROJECT_ID:
        logger.warning("GOOGLE_CLOUD_PROJECT env var not set.")
    db = firestore.Client() # Project ID inferred usually
    logger.info("Firestore client initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
    # If client fails, function can't work. Raise to prevent invocation.
    raise

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "firestore_updater",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200

@app.route('/', methods=['POST'])
def handle_firestore_update():
    """
    Main endpoint to process Pub/Sub messages from nova-firestore-updates topic.
    Processes messages to update Firestore documents based on 'update_type'.
    """
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
        message_id = pubsub_message.get('messageId', 'unknown')

        # Check for message ID for idempotency
        if sdk and message_id != 'unknown':
            if sdk.check_and_mark_processed(message_id, "firestore_updater_processed"):
                logger.info(f"Message {message_id} already processed, skipping")
                return 'OK', 200

        # Decode message data
        message_data_encoded = pubsub_message.get('data')
        if not message_data_encoded:
            logger.warning(f"Received event without message data (Msg ID: {message_id})")
            return 'OK', 200  # Acknowledge empty message

        message_data_decoded = base64.b64decode(message_data_encoded).decode("utf-8")
        data = json.loads(message_data_decoded)

        # Changed from data.get("type") to data.get("update_type") to align with AgentSDK.publish_blueprint_status_update
        message_update_type = data.get("update_type")
        legacy_operation = data.get("operation") # Still check for legacy "operation"

        logger.info(f"Received message with update_type: '{message_update_type}', operation: '{legacy_operation}' (Msg ID: {message_id})")

        # Route to appropriate handler based on message type
        effective_handler_key = message_update_type or data.get("type") or legacy_operation

        if effective_handler_key == "task_update":
            handle_task_update(data)
        elif effective_handler_key == "blueprint_status":
            handle_blueprint_update(data)
        elif effective_handler_key == "blueprint_update":
            logger.info(f"Handling specific 'blueprint_update' type (Msg ID: {message_id})")
            handle_blueprint_update(data)
        elif effective_handler_key == "notification":
            handle_notification(data)
        elif effective_handler_key == "log_blueprint":
            logger.info(f"Received legacy operation 'log_blueprint' (Msg ID: {message_id})")
            log_blueprint(data)
        else:
            logger.warning(f"Unknown message update_type or operation received: '{effective_handler_key}' (Msg ID: {message_id})")

        # Log the activity
        if sdk:
            sdk.log_activity(
                action="firestore_update_processed",
                details=f"Processed {effective_handler_key} update",
                metadata={
                    "message_id": message_id,
                    "update_type": effective_handler_key,
                    "data_keys": list(data.keys())
                }
            )

        return 'OK', 200

    except (base64.binascii.Error, UnicodeDecodeError) as e:
        logger.error(f"Error decoding message data (Msg ID: {message_id}): {e}", exc_info=True)
        return "Error decoding message data", 200  # Don't retry bad messages
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding message JSON (Msg ID: {message_id}): {e}", exc_info=True)
        return "Invalid JSON message data", 200  # Don't retry bad messages
    except Exception as e:
        logger.error(f"Unhandled error processing message (Msg ID: {message_id}): {e}", exc_info=True)
        return f'Internal Server Error: {str(e)}', 500

# [All the handler functions remain the same - handle_task_update, handle_blueprint_update, etc.]
def handle_task_update(data):
    """Handles 'task_update' message type."""
    agent_name = data.get("agent")
    task_id = data.get("task_id")
    status = data.get("status")
    blueprint_id = data.get("blueprint_id")
    timestamp_str = data.get("updated_at")
    error = data.get("error")
    result_summary = data.get("result_summary")
    message = data.get("message")

    if not all([agent_name, task_id, status, blueprint_id, timestamp_str]):
        logger.error(f"Missing required fields for handle_task_update: {data}")
        return

    logger.info(f"Updating status for Task {task_id} (Agent: {agent_name}, BP: {blueprint_id}) to {status}")

    try:
        @firestore.transactional
        def update_in_transaction(transaction, task_ref, task_data_update):
            transaction.set(task_ref, task_data_update, merge=True)

        task_ref = db.collection("blueprints").document(blueprint_id).collection("tasks").document(task_id)
        task_data_update = {
            "agent": agent_name,
            "status": status,
            "last_updated": timestamp_str,
        }
        if error:
            task_data_update["error"] = str(error)[:1000]
        if result_summary:
            task_data_update["result_summary"] = str(result_summary)[:2000]
        if message:
            task_data_update["message"] = str(message)[:1000]

        transaction = db.transaction()
        update_in_transaction(transaction, task_ref, task_data_update)
        logger.info(f"Successfully updated Firestore for task {task_id}")

        if status in ["completed", "error", "LIVE"]:
            check_blueprint_completion(blueprint_id)

    except google_exceptions.NotFound:
         logger.error(f"Firestore document not found during update for BP {blueprint_id}, Task {task_id}.")
    except Exception as e:
        logger.error(f"Error updating Firestore for task {task_id}: {e}", exc_info=True)
        raise

def handle_blueprint_update(data):
    """Handles 'blueprint_update' message type."""
    blueprint_id = data.get("blueprint_id")
    status = data.get("status")
    message = data.get("message")
    updated_at = data.get("timestamp")
    additional_details = data.get("details", {})

    live_url = additional_details.get("live_url")
    deployment_log_summary = additional_details.get("deployment_log_summary")
    tasks_dispatched = data.get("tasks_dispatched")
    dispatch_errors = data.get("dispatch_errors")

    if not all([blueprint_id, status, updated_at]):
        logger.error(f"Missing required fields (blueprint_id, status, timestamp) for handle_blueprint_update: {data}")
        return

    logger.info(f"Updating blueprint {blueprint_id} status to {status}, Message: {message}")
    blueprint_ref = db.collection("blueprints").document(blueprint_id)
    update_data = {
        "status": status,
        "last_updated": updated_at
    }
    if message:
        update_data["message"] = str(message)[:2000]

    if live_url:
        update_data["live_url"] = live_url
    if deployment_log_summary:
        update_data["deployment_log_summary"] = str(deployment_log_summary)[:5000]

    if tasks_dispatched is not None:
        update_data["tasks_dispatched"] = tasks_dispatched
    if dispatch_errors is not None:
        update_data["dispatch_errors"] = dispatch_errors

    if status.upper() in ["LIVE", "COMPLETED", "COMPLETED_WITH_ERRORS", "ERROR"]:
        update_data["completed_at"] = updated_at
        if status == "COMPLETED_WITH_ERRORS" or status == "ERROR":
            update_data["has_errors"] = True
        elif status == "LIVE" or status == "COMPLETED":
             update_data["has_errors"] = data.get("has_errors", False)

    try:
        blueprint_ref.set(update_data, merge=True)
        logger.info(f"Successfully updated blueprint {blueprint_id}")
    except Exception as e:
        logger.error(f"Error updating blueprint {blueprint_id} in Firestore: {e}", exc_info=True)
        raise

def handle_notification(data):
    """Handles 'notification' message type."""
    user_id = data.get("user_id")
    blueprint_id = data.get("blueprint_id")
    message = data.get("message")
    level = data.get("level", "info")
    timestamp = data.get("timestamp", datetime.now().isoformat())

    if not all([user_id, message]):
        logger.error(f"Missing required fields (user_id, message) for handle_notification: {data}")
        return

    logger.info(f"Storing notification for user {user_id} (Level: {level})")

    if not isinstance(user_id, str) or len(user_id.strip()) == 0:
        logger.error(f"Invalid user_id for notification: '{user_id}'. Skipping.")
        return

    notification_data = {
        "user_id": user_id,
        "blueprint_id": blueprint_id,
        "message": str(message)[:2000],
        "level": level,
        "timestamp": timestamp,
        "read": False
    }

    try:
        user_notifications_ref = db.collection("users").document(user_id).collection("notifications")
        user_notifications_ref.add(notification_data)
        logger.info(f"Successfully stored notification for user {user_id}")
    except Exception as e:
        logger.error(f"Error storing notification for user {user_id} in Firestore: {e}", exc_info=True)
        raise

def log_blueprint(data):
    """Handles 'log_blueprint' operation."""
    blueprint_id = data.get("blueprint_id")
    version = data.get("version")
    timestamp_str = data.get("timestamp")
    tasks = data.get("tasks", [])
    prompt = data.get("prompt")
    initiator = data.get("initiator", "unknown")

    if not all([blueprint_id, version, timestamp_str, prompt]):
         logger.error(f"Missing required fields for log_blueprint: {data}")
         return

    logger.info(f"Logging blueprint {blueprint_id} (Version: {version}, Initiator: {initiator}) to Firestore")

    try:
        batch = db.batch()
        blueprint_ref = db.collection("blueprints").document(blueprint_id)
        blueprint_doc_data = {
            "version": version,
            "created_at": timestamp_str,
            "status": "SUBMITTED",
            "task_count": len(tasks),
            "prompt": prompt,
            "initiator": initiator,
            "last_updated": timestamp_str,
            "live_url": None,
            "deployment_log_summary": None,
            "has_errors": False,
            "completed_at": None
        }

        batch.set(blueprint_ref, blueprint_doc_data)

        tasks_collection_ref = blueprint_ref.collection("tasks")
        for task_data in tasks:
            task_id = task_data.get("task_id")
            agent_target = task_data.get("agent_target")
            action = task_data.get("action")

            if not all([task_id, agent_target, action]):
                 logger.warning(f"Skipping task with missing fields in blueprint {blueprint_id}: {task_data}")
                 continue

            task_doc_ref = tasks_collection_ref.document(task_id)
            batch.set(task_doc_ref, {
                "agent_target": agent_target,
                "action": action,
                "status": "PENDING",
                "created_at": timestamp_str,
                "last_updated": timestamp_str,
                "details": task_data.get("details", None)
            })

        batch.commit()
        logger.info(f"Successfully logged blueprint {blueprint_id} and {len(tasks)} tasks to Firestore.")

    except Exception as e:
        logger.error(f"Error logging blueprint {blueprint_id} to Firestore: {e}", exc_info=True)
        raise

def check_blueprint_completion(blueprint_id):
    """Checks if all tasks for a blueprint are complete and updates blueprint status."""
    logger.info(f"Checking completion status for blueprint {blueprint_id}")
    try:
        blueprint_ref = db.collection("blueprints").document(blueprint_id)
        tasks_collection_ref = blueprint_ref.collection("tasks")
        tasks_stream = tasks_collection_ref.stream()

        all_tasks_finalized = True
        has_errors = False
        task_count = 0
        task_statuses = []

        for task_doc in tasks_stream:
            task_count += 1
            task_data = task_doc.to_dict()
            task_status = task_data.get("status", "UNKNOWN").upper()
            task_statuses.append(task_status)
            if task_status == "ERROR":
                has_errors = True
            if task_status not in ["COMPLETED", "ERROR", "LIVE"]:
                all_tasks_finalized = False

        if task_count == 0:
            logger.info(f"Blueprint {blueprint_id} has no tasks. Marking as COMPLETED.")
            blueprint_ref.update({
                "status": "COMPLETED",
                "completed_at": firestore.SERVER_TIMESTAMP,
                "message": "Blueprint has no tasks, marked as completed.",
                "has_errors": False,
                "last_updated": firestore.SERVER_TIMESTAMP
            })
            return

        if all_tasks_finalized:
            final_status = "COMPLETED_WITH_ERRORS" if has_errors else "COMPLETED"
            if "LIVE" in task_statuses:
                 final_status = "LIVE"

            logger.info(f"All {task_count} tasks finalized for blueprint {blueprint_id}. Overall status: {final_status}")
            update_payload = {
                "status": final_status,
                "completed_at": firestore.SERVER_TIMESTAMP,
                "has_errors": has_errors,
                "message": f"All tasks finalized. Overall status: {final_status}.",
                "last_updated": firestore.SERVER_TIMESTAMP
            }
            blueprint_ref.update(update_payload)
            logger.info(f"Updated blueprint {blueprint_id} status to {final_status}")
        else:
             finalized_task_count = sum(1 for s in task_statuses if s in ["COMPLETED", "ERROR", "LIVE"])
             logger.info(f"Blueprint {blueprint_id} is still in progress. Total: {task_count}, Finalized: {finalized_task_count}")

    except google_exceptions.NotFound:
         logger.warning(f"Blueprint {blueprint_id} not found during completion check.")
    except Exception as e:
        logger.error(f"Error checking blueprint completion for {blueprint_id}: {e}", exc_info=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
