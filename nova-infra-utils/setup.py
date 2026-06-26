from setuptools import setup, find_packages

setup(
    name="nova-infra-utils",
    version="1.0.0",
    description="Generic infrastructure utilities, security middleware, and helper services from the Nova Ecosystem",
    author="DNA Entertainment Ltd",
    packages=find_packages(),
    install_packages=[
        "redis",
        "bleach",
        "python-magic",
        "jsonschema",
        "google-cloud-bigquery",
        "google-cloud-pubsub",
        "google-cloud-firestore",
        "flask",
        "fastapi",
        "httpx",
        "psutil",
        "celery"
    ],
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
    ]
)
