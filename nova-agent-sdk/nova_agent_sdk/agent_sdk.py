from __future__ import annotations
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import vertexai
from google.api_core import exceptions as google_exceptions
from google.api_core import retry
from google.cloud import bigquery, firestore, pubsub_v1, secretmanager, storage

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"message": "%(message)s", "severity": "%(levelname)s", "timestamp": "%(asctime)s", "agent": "%(name)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)

class AgentLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['agent_name'] = self.extra['agent_name']
        return msg, kwargs

class AgentSDK:
    """
    A common SDK for Nova Ecosystem agents to interact with GCP services.
    Includes enhanced logging, error handling, and retry logic.
    """
    def __init__(self, agent_name, project_id=None):
        """
        Initializes the agent SDK.

        Args:
            agent_name (str): The name of the agent using the SDK.
            project_id (str, optional): GCP Project ID. If None, it must be set via
                                         the GOOGLE_CLOUD_PROJECT environment variable.

        Raises:
            ValueError: If project_id is not provided and GOOGLE_CLOUD_PROJECT environment variable is not set.
        """
        self.agent_name = agent_name
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')

        # Create a logger adapter for this agent instance first
        # This ensures all log messages from this SDK instance will have agent_name
        base_logger = logging.getLogger(__name__)
        self.logger = AgentLogAdapter(base_logger, {'agent_name': self.agent_name})

        if not self.project_id:
            err_msg = "GOOGLE_CLOUD_PROJECT environment variable not set and no project_id provided. AgentSDK cannot determine the GCP project."
            # Now self.logger is available and will correctly format the message
            self.logger.critical(err_msg)
            raise ValueError(err_msg)

        self.logger.info(f"SDK Initializing for agent '{self.agent_name}' in project '{self.project_id}'")

        # Check if running in local emulator mode
        self.use_emulators = os.environ.get('USE_LOCAL_EMULATORS', 'false').lower() == 'true'
        self.disable_gcp_auth = os.environ.get('DISABLE_GCP_AUTH', 'false').lower() == 'true'

        if self.use_emulators or self.disable_gcp_auth:
            self.logger.info("Running in LOCAL EMULATOR MODE - skipping real GCP client initialization")
            self.db = None
            self.bq_client = None
            self.publisher = None
            self.storage_client = None
            self.secret_client = None
            self.logger.info("Local emulator mode enabled - GCP clients set to None")
        else:
            try:
                self.db = firestore.Client(project=self.project_id)
                self.bq_client = bigquery.Client(project=self.project_id)
                self.publisher = pubsub_v1.PublisherClient()
                self.storage_client = storage.Client(project=self.project_id)
                self.secret_client = secretmanager.SecretManagerServiceClient()
                self.init_vertex_ai()
                self.logger.info("GCP clients (Firestore, BQ, PubSub, Storage, SecretManager, VertexAI) initialized successfully.")
            except Exception as e:
                self.logger.error(f"Failed to initialize one or more GCP clients: {e}", exc_info=True)
                raise

    def init_vertex_ai(self):
        """Initializes the Vertex AI client."""
        region = os.environ.get('GCP_REGION', 'us-central1')
        try:
            vertexai.init(project=self.project_id, location=region)
            self.logger.info(f"Vertex AI initialized for project {self.project_id} in region {region}.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Vertex AI for project {self.project_id} in region {region}: {e}", exc_info=True)
            raise

    @retry.Retry(predicate=retry.if_exception_type(google_exceptions.DeadlineExceeded, google_exceptions.ServiceUnavailable))
    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """
        Gets a secret value from Google Secret Manager with retry logic.

        Args:
            secret_id (str): The ID of the secret.
            version (str, optional): The secret version. Defaults to "latest".

        Returns:
            str: The decoded secret value.

        Raises:
            google.api_core.exceptions.NotFound: If the secret or version doesn't exist.
            Exception: For other access errors, re-raised after logging.
        """
        self.logger.info(f"Attempting to access secret: {secret_id}, version: {version}")
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            self.logger.info(f"Successfully accessed secret: {secret_id}")
            return secret_value
        except google_exceptions.NotFound as e:
            self.logger.error(f"Secret or version not found: {secret_id}/{version}. Error: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving secret {secret_id}: {e}", exc_info=True)
            raise

    def log_activity(self, action: str, details: str, blueprint_version: str = "N/A", blueprint_id: str = "N/A", task_id: str = "N/A", metadata: dict = None) -> bool:
        """
        Logs agent activity details to standard logs and BigQuery with retries.

        Args:
            action (str): A short description of the action performed.
            details (str): More detailed information about the activity or result.
            blueprint_version (str, optional): Version of the blueprint being processed. Defaults to "N/A".
            blueprint_id (str, optional): ID of the blueprint. Defaults to "N/A".
            task_id (str, optional): ID of the specific task. Defaults to "N/A".
            metadata (dict, optional): Additional structured data to log. Defaults to None.

        Returns:
            bool: True if logging to BigQuery was successful (within retries), False otherwise.
        """
        log_message = f"Action: {action}, Blueprint: {blueprint_id}/{blueprint_version}, Task: {task_id}, Details: {details}"
        if metadata:
            log_message += f", Metadata: {json.dumps(metadata)}"
        self.logger.info(log_message)

        table_id = f"{self.project_id}.{os.getenv('BQ_LOG_DATASET', 'nova_agent_logs')}.{os.getenv('BQ_LOG_TABLE', 'agent_activity_logs')}"
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_name": self.agent_name,
            "action": str(action),
            "blueprint_id": str(blueprint_id),
            "blueprint_version": str(blueprint_version),
            "task_id": str(task_id),
            "details": str(details),
            "metadata": json.dumps(metadata) if metadata is not None else None
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Telemetry resilience: tolerate row fields not yet in the table schema
                # rather than failing the whole insert (prevents silent loss of all
                # activity logs if the logged row drifts ahead of the table schema).
                errors = self.bq_client.insert_rows_json(table_id, [row], ignore_unknown_values=True)
                if not errors:
                    self.logger.debug(f"Successfully logged to BigQuery table {table_id} for action: {action}")
                    return True
                error_details = "; ".join([f"Index {e['index']}: {str(e['errors'])}" for e in errors])
                self.logger.warning(f"BigQuery insert errors for {action} (Attempt {attempt + 1}/{max_retries}): {error_details}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (2 ** attempt))
            except Exception as e:
                self.logger.error(f"Exception logging {action} to BigQuery (Attempt {attempt + 1}/{max_retries}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    time.sleep(1 * (2 ** attempt))
        self.logger.error(f"Failed to log {action} to BigQuery table {table_id} after {max_retries} attempts.")
        return False

    def _publish_message(self, topic_name: str, message_data: dict) -> str:
        """
        Publishes a JSON message to a specified Pub/Sub topic.

        Args:
            topic_name (str): The name of the Pub/Sub topic.
            message_data (dict): The dictionary data to publish as JSON.

        Returns:
            str: The message ID of the published message.

        Raises:
            TimeoutError: If the publish confirmation times out.
            Exception: For other Pub/Sub publishing errors, re-raised after logging.
        """
        self.logger.info(f"Publishing message to topic: {topic_name}")
        try:
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            message_bytes = json.dumps(message_data).encode("utf-8")
            future = self.publisher.publish(topic_path, message_bytes)
            message_id = future.result(timeout=60)
            self.logger.info(f"Successfully published message {message_id} to topic {topic_name}")
            return message_id
        except TimeoutError as e:
             self.logger.error(f"Timeout publishing message to topic {topic_name}: {e}", exc_info=True)
             raise
        except Exception as e:
            self.logger.error(f"Error publishing message to topic {topic_name}: {e}", exc_info=True)
            raise

    # --------------------------------------------------------------------------
    # Schema-Specific Publisher Methods
    # --------------------------------------------------------------------------

    def publish_global_command(self, blueprint_id: str, prompt: str, user_id: str = "N/A") -> str:
        """Publishes a new blueprint command conforming to the nova_global_command_schema."""
        topic_name = "nova-global-command"

        # Handle Avro union type ["null", "string"] for user_id
        # If user_id is provided, it must be wrapped in {"string": value} for Avro JSON encoding
        formatted_user_id = None
        if user_id:
            formatted_user_id = {"string": str(user_id)}

        message_data = {
            "blueprint_id": str(blueprint_id),
            "prompt": str(prompt),
            "user_id": formatted_user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return self._publish_message(topic_name, message_data)

    def publish_architect_task(self, blueprint_id: str, task_type: str, payload: dict) -> str:
        """Publishes a deferred task for the Architect agent conforming to the architect_agent_task_schema."""
        topic_name = "architect-agent-topic"
        message_data = {
            "task_id": str(uuid.uuid4()),
            "blueprint_id": str(blueprint_id),
            "task_type": str(task_type),
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return self._publish_message(topic_name, message_data)

    def publish_firestore_update(self, update_type: str, document_path: str, payload: dict) -> str:
        """Publishes a Firestore update request conforming to the nova_firestore_update_schema."""
        topic_name = "nova-firestore-updates"
        message_data = {
            "update_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "update_type": str(update_type),
            "document_path": str(document_path),
            "payload": payload
        }
        return self._publish_message(topic_name, message_data)

    def publish_blueprint_status_update(self, blueprint_id: str, status: str, message: str, additional_details: dict = None) -> str:
        """Publishes a blueprint status update, typically for Firestore consumption."""
        # This message can be consumed by a generic firestore_updater function
        # or a more specific blueprint_status_updater.
        topic_name = "nova-firestore-updates" # Or a dedicated "nova-blueprint-status" topic
        message_data = {
            "update_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "update_type": "blueprint_status", # Specific type for routing
            "blueprint_id": str(blueprint_id),
            "status": str(status),
            "message": str(message),
            "details": additional_details if additional_details is not None else {}
        }
        # This uses the internal _publish_message, which is fine within the SDK
        return self._publish_message(topic_name, message_data)

    def publish_overseer_advisory(self, severity: str, source_agent: str, message: str, target_agent: str = "N/A", details: dict = None) -> str:
        """Publishes an advisory from the Overseer conforming to the nova_overseer_advisory_schema."""
        topic_name = "nova-overseer-advisory"
        message_data = {
            "advisory_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": str(severity),
            "source_agent": str(source_agent),
            "target_agent": str(target_agent),
            "message": str(message),
            "details": details if details is not None else {}
        }
        return self._publish_message(topic_name, message_data)

    def publish_status_request(self, target_service: str = "all") -> str:
        """Publishes a status request conforming to the nova_status_request_schema."""
        topic_name = "nova-status-request"
        message_data = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_service": str(target_service)
        }
        return self._publish_message(topic_name, message_data)

    def publish_message(self, topic_name: str, message_data: dict) -> str:
        """
        Publishes a JSON message to a specified Pub/Sub topic.
        This is a generic method; prefer using schema-specific publishers where possible.
        """
        self.logger.warning(f"Using generic publish_message for topic {topic_name}. Consider creating a schema-specific method in the SDK.")
        return self._publish_message(topic_name, message_data)

    @retry.Retry(predicate=retry.if_exception_type(google_exceptions.ServiceUnavailable, google_exceptions.TooManyRequests))
    def store_object(self, bucket_name: str, object_name: str, data: str | bytes, content_type: str = "text/plain") -> str:
        """
        Stores data (string or bytes) in a Google Cloud Storage object with retry logic.

        Args:
            bucket_name (str): The name of the GCS bucket.
            object_name (str): The desired name of the object within the bucket.
            data (str | bytes): The string or bytes data to store.
            content_type (str, optional): The content type of the data. Defaults to "text/plain".

        Returns:
            str: The gsutil URI of the stored object (e.g., "gs://bucket_name/object_name").

        Raises:
            google.api_core.exceptions.NotFound: If the bucket doesn't exist.
            Exception: For other storage errors, re-raised after logging.
        """
        self.logger.info(f"Storing object gs://{bucket_name}/{object_name}")
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            if isinstance(data, bytes):
                blob.upload_from_string(data, content_type=content_type)
            else:
                blob.upload_from_string(str(data), content_type=content_type)
            gcs_path = f"gs://{bucket_name}/{object_name}"
            self.logger.info(f"Successfully stored object at {gcs_path}")
            return gcs_path
        except google_exceptions.NotFound as e:
            self.logger.error(f"Bucket not found: {bucket_name}. Error: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Error storing object {object_name} in {bucket_name}: {e}", exc_info=True)
            raise

    @retry.Retry(predicate=retry.if_exception_type(google_exceptions.ServiceUnavailable, google_exceptions.TooManyRequests))
    def read_object(self, bucket_name: str, object_name: str, as_bytes: bool = False) -> str | bytes:
        """
        Reads data from a Google Cloud Storage object with retry logic.

        Args:
            bucket_name (str): The name of the GCS bucket.
            object_name (str): The name of the object within the bucket.
            as_bytes (bool, optional): If True, returns the content as bytes.
                                       Otherwise, returns as text (UTF-8 decoded). Defaults to False.

        Returns:
            str | bytes: The content of the object as a string or bytes.

        Raises:
            google.api_core.exceptions.NotFound: If the bucket or object doesn't exist.
            Exception: For other storage errors, re-raised after logging.
        """
        gcs_path = f"gs://{bucket_name}/{object_name}"
        self.logger.info(f"Reading object from {gcs_path}")
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            if not blob.exists():
                 self.logger.error(f"Object not found: {gcs_path}")
                 raise google_exceptions.NotFound(f"Object not found: {gcs_path}")

            data_content = blob.download_as_bytes() if as_bytes else blob.download_as_text()
            self.logger.info(f"Successfully read object from {gcs_path}")
            return data_content
        except google_exceptions.NotFound as e:
             self.logger.error(f"Bucket or object not found: {gcs_path}. Error: {e}", exc_info=True)
             raise
        except Exception as e:
            self.logger.error(f"Error reading object {object_name} from {bucket_name}: {e}", exc_info=True)
            raise

    def check_and_mark_processed(self, message_id: str, collection_name: str = "processed_message_ids", ttl_seconds: int = 24 * 60 * 60) -> bool:
        """
        Checks if a message ID has been processed and marks it as processed in Firestore.
        This provides robust idempotency for Pub/Sub message handling.
        A TTL policy on the 'timestamp' field in the Firestore collection is recommended for cleanup.

        Args:
            message_id (str): The unique ID of the message (e.g., from Pub/Sub).
            collection_name (str, optional): The Firestore collection to store message IDs.
                                             Defaults to "processed_message_ids".
            ttl_seconds (int, optional): Informational TTL for the marker document. Actual TTL
                                         should be configured via Firestore console. Defaults to 86400 (24 hours).

        Returns:
            bool: True if the message was already processed (document exists),
                  False if it was not processed before (document was created by this call).
                  Returns False on error during check (to err on the side of reprocessing).
        """
        if not message_id:
            self.logger.warning("Message ID is empty, cannot perform idempotency check.")
            return False

        doc_ref = self.db.collection(collection_name).document(message_id)
        try:
            doc = doc_ref.get()
            if doc.exists:
                self.logger.info(f"Message ID {message_id} already processed (found in Firestore collection {collection_name}).")
                return True
            else:
                doc_ref.set({
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                    "agent_marked_by": self.agent_name,
                    "ttl_info_seconds": ttl_seconds
                })
                self.logger.info(f"Message ID {message_id} marked as processed in Firestore collection {collection_name}.")
                return False
        except Exception as e:
            self.logger.error(f"Error during Firestore idempotency check for message ID {message_id}: {e}", exc_info=True)
            return False

    def publish_metric(self, metric_data: dict, topic_name: str = "nova-ecosystem-metrics"):
        """
        Publishes a standardized metric to a specified Pub/Sub topic, conforming to nova_metric_schema.
        Defaults to 'nova-ecosystem-metrics' but can be used for other topics with the same schema like 'nova-agent-topic'.

        Args:
            metric_data (dict): A dictionary containing metric information.
                                It should ideally conform to a defined metric schema.
                                Key fields like 'metric_id' and 'timestamp' will be added/overwritten.
            topic_name (str): The name of the topic to publish to.
                                Expected fields include: "agent_name", "service_name", "action_type",
                                "action_name", "duration_ms", "status".
                                Optional: "blueprint_id", "task_id", "error_details", "metadata".
        """
        required_fields = ["agent_name", "service_name", "action_type", "action_name", "duration_ms", "status"]
        for field in required_fields:
            if field not in metric_data:
                self.logger.error(f"Metric data missing required field: '{field}'. Metric not published. Data: {metric_data}")
                return

        if "agent_name" not in metric_data or not metric_data["agent_name"]:
            metric_data["agent_name"] = self.agent_name

        metric_data["metric_id"] = str(uuid.uuid4())
        metric_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        try:
            self._publish_message(topic_name, metric_data)
            self.logger.debug(f"Metric published successfully to {topic_name}: ID {metric_data.get('metric_id')}, Action {metric_data.get('action_name')}")
        except Exception as e:
            self.logger.error(f"Error during metric publication for metric_id {metric_data.get('metric_id')}: {e}", exc_info=True)

# Example of how to use the SDK:
# if __name__ == '__main__':
#     # This is illustrative. In a real agent, GOOGLE_CLOUD_PROJECT would be set in the environment.
#     # os.environ["GOOGLE_CLOUD_PROJECT"] = "your-gcp-project-id" # Set for local testing if not set globally
#     try:
#         sdk = AgentSDK(agent_name="TestAgent")
#         sdk.logger.info("TestAgent SDK initialized and logger is working.")
#         # sdk.log_activity("TestRun", "SDK initialized successfully.", blueprint_id="bp-test-001")
#         # secret_val = sdk.get_secret("my-test-secret") # Replace with a real secret ID
#         # print(f"Secret value: {secret_val}")
#         # sdk.publish_message("my-test-topic", {"message": "Hello from SDK test"}) # Replace with a real topic
#     except ValueError as ve:
#         print(f"SDK Initialization Error: {ve}")
#     except Exception as ex:
#         print(f"An unexpected error occurred: {ex}")
