from setuptools import setup, find_packages

setup(
    name="nova-agent-sdk",
    version="1.0.0",
    description="A robust, generic SDK for building AI agents with event-driven messaging, structured logging, and secrets management.",
    author="DNA Entertainment Ltd",
    packages=find_packages(),
    install_requires=[
        "google-cloud-pubsub>=2.19.0",
        "google-cloud-secret-manager>=2.18.0",
        "google-cloud-logging>=3.9.0",
        "google-auth>=2.27.0",
        "pydantic>=2.5.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
