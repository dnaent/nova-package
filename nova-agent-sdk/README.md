# Nova Agent SDK

A robust, enterprise-grade Python SDK for building autonomous, event-driven AI agent systems. 

Derived from the backend infrastructure of the **Nova Ecosystem**, this SDK provides essential abstractions for:
- **Event-Driven Messaging**: Seamless wrapper around Google Cloud Pub/Sub for agent communication.
- **Structured Telemetry & Logging**: Standardized agent activity logs and metrics schemas.
- **Secure Configuration Management**: Native integration with Google Cloud Secret Manager for API keys and sensitive settings.

## Installation

```bash
pip install nova-agent-sdk
```

## Quick Start

```python
from nova_agent_sdk import AgentSDK
import asyncio

async def main():
    # Initialize the SDK for a specific agent role
    sdk = AgentSDK(agent_name="analysis-agent")

    # Fetch a secure secret
    api_key = await sdk.get_secret("my-api-key")

    # Publish an event to the message bus
    await sdk.publish_message(
        topic_name="my-topic",
        message_data={"task": "analyze_data", "payload": "..."}
    )

    # Log structured activity
    sdk.log_activity("task_completed", "Analysis successfully finished.")

if __name__ == "__main__":
    asyncio.run(main())
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

*Note: This open-source SDK represents the communication and telemetry foundation of the Nova Ecosystem. The proprietary autonomous orchestration and Four C's self-regulating engines remain closed-source and patent-pending under DNA Entertainment Ltd.*
