# nova-ecosystem-terraform/services/cost_reporting_function/main.py
import os
from datetime import datetime, time, timedelta, timezone

from google.cloud import bigquery, pubsub_v1


def daily_cost_report(event, context):
    """A Cloud Function to fetch daily cost data and publish it to a Pub/Sub topic."""

    billing_account_id = os.environ.get('BILLING_ACCOUNT_ID')
    project_id = os.environ.get('GCP_PROJECT')
    topic_name = os.environ.get('TOPIC_NAME')
    billing_export_table = os.environ.get('BILLING_EXPORT_TABLE')

    if not all([billing_account_id, project_id, topic_name, billing_export_table]):
        raise ValueError("Missing required environment variables.")

    client = bigquery.Client()

    # Calculate the start and end of the previous day in UTC.
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    start_of_yesterday = datetime.combine(yesterday.date(), time.min).replace(tzinfo=timezone.utc)
    end_of_yesterday = datetime.combine(yesterday.date(), time.max).replace(tzinfo=timezone.utc)

    query = f"""
        SELECT SUM(cost)
        FROM `{billing_export_table}`
        WHERE usage_start_time >= '{start_of_yesterday}'
        AND usage_end_time <= '{end_of_yesterday}'
    """

    query_job = client.query(query)
    results = query_job.result()

    total_cost = 0
    for row in results:
        total_cost = row[0] or 0

    cost_data = f"Daily cost for {billing_account_id}: £{total_cost:.2f}"

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    message_data = cost_data.encode("utf-8")
    future = publisher.publish(topic_path, data=message_data)

    print(f"Published message to {topic_path}: {future.result()}")
