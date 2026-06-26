"""
Setup script for Nova Agent SDK
"""
from setuptools import setup

setup(
    name="nova-agent-sdk",
    version="0.1.0",
    description="Shared SDK for Nova Ecosystem agents to interact with GCP services",
    py_modules=["agent_sdk", "environment"],
    install_requires=[
        "google-cloud-firestore",
        "google-cloud-pubsub",
        "google-cloud-secret-manager",
        "google-cloud-aiplatform",
        "google-cloud-bigquery"
    ],
    python_requires=">=3.9",
)
