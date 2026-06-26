import json
from unittest.mock import MagicMock, patch

import pytest

# Attempt to import AgentSDK relative to how tests might be run or package installed
# This might need adjustment based on final test execution setup
from agent_sdk import AgentSDK  # Assuming agent_sdk is installable/discoverable

# Placeholder for GOOGLE_CLOUD_PROJECT if not set in environment for tests
MOCK_PROJECT_ID = "test-gcp-project"

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", MOCK_PROJECT_ID)
    monkeypatch.setenv("BQ_LOG_DATASET", "test_log_dataset")
    monkeypatch.setenv("BQ_LOG_TABLE", "test_log_table")
    monkeypatch.setenv("GCP_REGION", "test-region")

@pytest.fixture
def sdk(mock_env):
    """Provides an AgentSDK instance with mocked GCP clients."""
    with patch('nova_agent_sdk.firestore.Client') as mock_firestore, \
         patch('nova_agent_sdk.bigquery.Client') as mock_bigquery, \
         patch('nova_agent_sdk.pubsub_v1.PublisherClient') as mock_publisher, \
         patch('nova_agent_sdk.storage.Client') as mock_storage, \
         patch('nova_agent_sdk.secretmanager.SecretManagerServiceClient') as mock_secret_manager, \
         patch('nova_agent_sdk.vertexai.init') as mock_vertex_init, \
         patch('nova_agent_sdk.GenerativeModel') as mock_generative_model: # If SDK uses GenerativeModel directly

        # Make mock instances available if needed
        mock_firestore_instance = mock_firestore.return_value
        mock_bigquery_instance = mock_bigquery.return_value
        mock_publisher_instance = mock_publisher.return_value
        mock_storage_instance = mock_storage.return_value
        mock_secret_manager_instance = mock_secret_manager.return_value

        sdk_instance = AgentSDK(agent_name="TestSDKAgent", project_id=MOCK_PROJECT_ID)
        # Attach mocks to instance for easier access in tests if needed, though usually interacted via methods
        sdk_instance.db = mock_firestore_instance
        sdk_instance.bq_client = mock_bigquery_instance
        sdk_instance.publisher = mock_publisher_instance
        sdk_instance.storage_client = mock_storage_instance
        sdk_instance.secret_client = mock_secret_manager_instance
        # sdk_instance.model = mock_generative_model.return_value # If applicable

        return sdk_instance

def test_sdk_initialization_with_project_id(mock_env):
    sdk_instance = AgentSDK(agent_name="TestAgentInit", project_id="explicit-project-id")
    assert sdk_instance.agent_name == "TestAgentInit"
    assert sdk_instance.project_id == "explicit-project-id"
    assert sdk_instance.logger is not None

def test_sdk_initialization_with_env_var(mock_env, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project-id")
    sdk_instance = AgentSDK(agent_name="TestAgentEnv")
    assert sdk_instance.project_id == "env-project-id"

def test_sdk_initialization_missing_project_id(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT environment variable not set"):
        AgentSDK(agent_name="TestAgentFail")

def test_get_secret_success(sdk: AgentSDK):
    mock_secret_payload = MagicMock()
    mock_secret_payload.data = "supersecretvalue".encode("UTF-8")
    sdk.secret_client.access_secret_version.return_value.payload = mock_secret_payload

    secret_val = sdk.get_secret("my-secret")
    assert secret_val == "supersecretvalue"
    sdk.secret_client.access_secret_version.assert_called_once_with(
        request={"name": f"projects/{MOCK_PROJECT_ID}/secrets/my-secret/versions/latest"}
    )

# TODO: Add test_get_secret_not_found, test_get_secret_other_exception

def test_log_activity_success(sdk: AgentSDK):
    sdk.bq_client.insert_rows_json.return_value = [] # Simulate success (no errors)
    metadata = {"key": "value"}
    result = sdk.log_activity(
        action="Test Action",
        details="Test details",
        blueprint_id="bp-123",
        task_id="task-456",
        metadata=metadata
    )
    assert result is True
    sdk.bq_client.insert_rows_json.assert_called_once()
    args, _ = sdk.bq_client.insert_rows_json.call_args
    table_id, rows = args
    assert table_id == f"{MOCK_PROJECT_ID}.test_log_dataset.test_log_table"
    assert len(rows) == 1
    row = rows[0]
    assert row["agent_name"] == "TestSDKAgent"
    assert row["action"] == "Test Action"
    assert row["details"] == "Test details"
    assert row["blueprint_id"] == "bp-123"
    assert row["task_id"] == "task-456"
    assert json.loads(row["metadata"]) == metadata
    assert "timestamp" in row

# TODO: Add test_log_activity_bq_failure_retries

def test_publish_message_success(sdk: AgentSDK):
    mock_future = MagicMock()
    mock_future.result.return_value = "mock-message-id"
    sdk.publisher.publish.return_value = mock_future
    sdk.publisher.topic_path.return_value = f"projects/{MOCK_PROJECT_ID}/topics/test-topic"

    topic_name = "test-topic"
    message_data = {"data_key": "data_value"}
    message_id = sdk._publish_message(topic_name, message_data)

    assert message_id == "mock-message-id"
    sdk.publisher.topic_path.assert_called_once_with(MOCK_PROJECT_ID, topic_name)
    sdk.publisher.publish.assert_called_once_with(
        f"projects/{MOCK_PROJECT_ID}/topics/test-topic",
        json.dumps(message_data).encode("utf-8")
    )

# TODO: Add test_publish_message_timeout, test_publish_message_generic_exception
# TODO: Add tests for schema-specific publishers like publish_global_command etc.

def test_store_object_success(sdk: AgentSDK):
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    sdk.storage_client.bucket.return_value = mock_bucket

    bucket_name = "test-bucket"
    object_name = "test-object.txt"
    data = "hello world"

    gcs_path = sdk.store_object(bucket_name, object_name, data, content_type="text/plain")

    assert gcs_path == f"gs://{bucket_name}/{object_name}"
    sdk.storage_client.bucket.assert_called_once_with(bucket_name)
    mock_bucket.blob.assert_called_once_with(object_name)
    mock_blob.upload_from_string.assert_called_once_with(data, content_type="text/plain")

# TODO: Add test_store_object_bytes, test_store_object_not_found, test_store_object_error

def test_read_object_success(sdk: AgentSDK):
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_text.return_value = "file content"
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    sdk.storage_client.bucket.return_value = mock_bucket

    content = sdk.read_object("test-bucket", "test-file.txt")
    assert content == "file content"

# TODO: Add test_read_object_as_bytes, test_read_object_not_found, test_read_object_error

def test_check_and_mark_processed(sdk: AgentSDK):
    mock_doc_ref = MagicMock()
    mock_doc_snapshot = MagicMock()

    # Case 1: Message not processed before
    mock_doc_snapshot.exists = False
    mock_doc_ref.get.return_value = mock_doc_snapshot
    sdk.db.collection.return_value.document.return_value = mock_doc_ref

    message_id_new = "new-msg-1"
    assert sdk.check_and_mark_processed(message_id_new) is False
    sdk.db.collection.assert_called_with("processed_message_ids")
    sdk.db.collection().document.assert_called_with(message_id_new)
    mock_doc_ref.set.assert_called_once() # Check it was marked

    # Case 2: Message already processed
    mock_doc_snapshot.exists = True
    mock_doc_ref.reset_mock() # Reset mocks for the next call scenario
    mock_doc_ref.get.return_value = mock_doc_snapshot
    mock_doc_ref.set.reset_mock()


    message_id_exists = "existing-msg-1"
    sdk.db.collection.return_value.document.return_value = mock_doc_ref # Ensure it's set for this call too
    assert sdk.check_and_mark_processed(message_id_exists) is True
    mock_doc_ref.set.assert_not_called() # Should not be called if already exists

# TODO: Add test_check_and_mark_processed_firestore_error

def test_publish_metric(sdk: AgentSDK):
    # Mock the internal _publish_message which publish_metric calls
    with patch.object(sdk, '_publish_message', return_value="metric-msg-id") as mock_internal_publish:
        metric_data = {
            "agent_name": "TestAgent",
            "service_name": "test_service",
            "action_type": "test_action_type",
            "action_name": "test_action_name",
            "duration_ms": 100,
            "status": "success"
        }
        sdk.publish_metric(metric_data, topic_name="custom-metrics-topic")

        mock_internal_publish.assert_called_once()
        args, _ = mock_internal_publish.call_args
        topic_arg, data_arg = args
        assert topic_arg == "custom-metrics-topic"
        assert data_arg["metric_id"] is not None
        assert data_arg["timestamp"] is not None
        assert data_arg["action_name"] == "test_action_name"

# TODO: Add test_publish_metric_missing_required_fields
