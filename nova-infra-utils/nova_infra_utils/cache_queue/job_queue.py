import os

from celery import Celery
from celery.result import AsyncResult

# Get the broker URL from environment variables, default to Redis
BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Initialize the Celery app
celery_app = Celery(
    "nova_jobs",
    broker=BROKER_URL,
    backend=BACKEND_URL
)

# Define Celery tasks
@celery_app.task(name="tasks.analyze_large_codebase")
def analyze_large_codebase(project_data: dict, user_id: str) -> dict:
    """
    A Celery task to perform code analysis on a large codebase.
    This is a placeholder for the actual analysis logic.
    """
    print(f"Starting analysis for project data: {project_data.get('name')} by user {user_id}")
    # Simulate a long-running task
    import time
    time.sleep(60) # Sleeps for 1 minute
    result = {"status": "complete", "lines_analyzed": 100000}
    print(f"Analysis complete for project: {project_data.get('name')}")
    return result

@celery_app.task(name="tasks.batch_security_scan")
def batch_security_scan(project_ids: list, user_id: str) -> dict:
    """
    A Celery task to perform security scans on multiple projects.
    """
    print(f"Starting batch security scan for {len(project_ids)} projects by user {user_id}")
    results = {}
    for project_id in project_ids:
        # Simulate scanning each project
        import time
        time.sleep(10)
        results[project_id] = {"status": "complete", "vulnerabilities_found": 2}
    print("Batch security scan complete.")
    return results

@celery_app.task(name="tasks.send_email_batch")
def send_email_batch(email_jobs: list) -> dict:
    """
    A Celery task to send a batch of emails.
    """
    print(f"Starting to send a batch of {len(email_jobs)} emails.")
    # In a real app, this would integrate with the EmailService
    # from email_service import EmailService
    # email_service = EmailService(...)
    count = 0
    for job in email_jobs:
        # email_service._send_email(job['to'], job['subject'], job['body'])
        count += 1
    print(f"Sent {count} emails.")
    return {"emails_sent": count}


class JobQueue:
    def __init__(self, broker_url: str = None):
        """
        Initializes the job queue service.
        Connects to the existing Celery app.
        """
        self.celery_app = celery_app
        print("Job queue service initialized.")

    async def queue_analysis_job(self, project_data: dict, user_id: str) -> str:
        """
        Queues a large code analysis job.
        Returns the ID of the queued job.
        """
        task = analyze_large_codebase.delay(project_data, user_id)
        print(f"Queued analysis job with ID: {task.id}")
        return task.id

    async def queue_batch_scan_job(self, project_ids: list, user_id: str) -> str:
        """
        Queues a batch security scan job.
        Returns the ID of the queued job.
        """
        task = batch_security_scan.delay(project_ids, user_id)
        print(f"Queued batch scan job with ID: {task.id}")
        return task.id

    async def get_job_status(self, job_id: str) -> dict:
        """
        Retrieves the status and result of a Celery job.
        """
        task_result = AsyncResult(job_id, app=self.celery_app)
        response = {
            "job_id": job_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None
        }
        print(f"Fetching status for job {job_id}: {response['status']}")
        return response
