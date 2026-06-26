# Nova LLM Router

A multi-vendor LLM routing library built for resilience, token-budgeting, and automatic failover. 

Derived from the **Nova Ecosystem**, this package abstracts away the complexities of calling multiple LLM providers (Anthropic, OpenAI, Google) by providing a unified, context-aware interface.

## Features

- **Multi-Provider Unified Interface**: Seamlessly route completions to the correct provider SDK based on the model name.
- **Automatic Cross-Provider Failover**: If a provider experiences an outage, rate limits (429), or internal errors (500), the router can automatically fall back to an available alternative model to ensure your pipelines never break.
- **Context-Aware Token Budgeting**: Apply strict execution budgets using `contextvars`. A runaway self-correction loop will be caught and terminated before causing unexpected billing spikes.
- **Google Secret Manager Integration**: Securely load and manage API keys dynamically at runtime.

## Installation

```bash
pip install nova-llm-router
```

## Quick Start

```python
import asyncio
from nova_llm_router.llm_router import complete_async, set_budget
from nova_llm_router.model_config_utils import get_endpoint_manager

async def main():
    # 1. Initialize the Endpoint Manager (loads keys securely)
    secret_manager = await get_endpoint_manager(project_id="my-gcp-project")

    # 2. Set a token budget for this specific execution context
    budget = set_budget(cap=5000)

    # 3. Call the router (it automatically detects the provider for 'gpt-4o')
    response = await complete_async(
        secret_manager=secret_manager,
        model_name="gpt-4o",
        system_prompt="You are a helpful assistant.",
        user_prompt="Explain quantum computing in one sentence."
    )
    
    print("Response:", response)
    print("Tokens Used:", budget.used)

if __name__ == "__main__":
    asyncio.run(main())
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

*Note: This open-source SDK represents the LLM orchestration foundation of the Nova Ecosystem. The proprietary autonomous orchestration and Four C's self-regulating engines remain closed-source and patent-pending under DNA Entertainment Ltd.*
