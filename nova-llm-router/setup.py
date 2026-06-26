from setuptools import setup, find_packages

setup(
    name="nova-llm-router",
    version="1.0.0",
    description="A robust, multi-vendor LLM routing library with token budgeting and automatic failover.",
    author="DNA Entertainment Ltd",
    packages=find_packages(),
    install_requires=[
        "google-cloud-secret-manager>=2.18.0",
        "tenacity>=8.2.0",
        "aiohttp>=3.9.0",
        "anthropic>=0.18.0",
        "openai>=1.12.0",
        "google-cloud-aiplatform>=1.42.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
