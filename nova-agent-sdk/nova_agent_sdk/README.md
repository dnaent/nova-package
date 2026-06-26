# Centralized Agent SDK

This package provides a centralized SDK for Nova Ecosystem agents to interact with Google Cloud Platform (GCP) services.

It includes common functionalities for:
- Secret Management
- Firestore database operations
- Pub/Sub messaging
- Vertex AI client initialization
- BigQuery logging
- Cloud Storage operations

## Installation

This package is intended to be installed as a local dependency within the Nova Ecosystem services.

## Usage

```python
from agent_sdk import AgentSDK

# Initialize the SDK
sdk = AgentSDK(agent_name="MyAgent")

# Use SDK methods
sdk.publish_message("my-topic", {"data": "hello"})
secret = sdk.get_secret("my-secret")
# ... and so on.
```
# Nova Ecosystem Agent SDK

A common SDK for Nova Ecosystem agents to interact with Google Cloud Platform services. This SDK provides consistent interfaces for all Nova agents, including enhanced logging, error handling, and retry logic.

## Features

- Unified logging across all agents (structured logging for Cloud Logging)
- Secret management with Google Secret Manager
- Activity logging to both Cloud Logging and BigQuery
- Pub/Sub message publishing
- Cloud Storage object storage and retrieval
- Built-in retry logic for transient errors

## Usage

### Installation

The Agent SDK is designed to be included in each agent's container. Make sure to copy the `agent_sdk.py` file to your agent's directory before building the container.

### Initialization

```python
from agent_sdk import AgentSDK

# Initialize the SDK with the agent's name
agent = AgentSDK(agent_name="YourAgentName")
```

### Secret Management

```python
# Retrieve a secret
api_key = agent.get_secret("secret-name")
```

### Logging Activity

```python
# Log an action
agent.log_activity(
    action="Task Started",
    details="Processing user request for data analysis",
    blueprint_id="blueprint-123",
    task_id="task-456",
    blueprint_version="1.0"
)
```

### Publishing Messages

```python
# Publish a message to a Pub/Sub topic
agent.publish_message(
    topic_name="your-topic-name",
    message_data={
        "task_id": "task-123",
        "status": "completed",
        "result": "Analysis completed successfully"
    }
)
```

### Storing Objects

```python
# Store data in Cloud Storage
storage_path = agent.store_object(
    bucket_name="your-bucket",
    object_name="results/task-123.txt",
    data="Your result data here",
    content_type="text/plain"
)
```

### Reading Objects

```python
# Read data from Cloud Storage
data = agent.read_object(
    bucket_name="your-bucket",
    object_name="input/task-123.txt"
)
```

## Error Handling

The SDK includes built-in retry logic for transient errors and comprehensive error logging. All methods will raise appropriate exceptions that should be handled by the agent implementation.

## Dependencies

- google-cloud-bigquery
- google-cloud-pubsub
- google-cloud-secretmanager
- google-cloud-storage
- google-api-core