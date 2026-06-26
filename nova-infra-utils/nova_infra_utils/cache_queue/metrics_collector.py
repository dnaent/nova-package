from datetime import datetime

import psutil  # A cross-platform library for retrieving info on running processes


# Placeholder for AgentSDK
class AgentSDK:
    def __init__(self):
        print("Initializing mock AgentSDK for metrics collection")

    def store_metric(self, metric_data: dict):
        # In a real implementation, this would write to a time-series DB or Firestore
        print(f"METRIC_STORE: {metric_data}")

class MetricsCollector:
    def __init__(self, sdk: AgentSDK):
        """
        Initializes the metrics collection service.
        sdk (AgentSDK): The agent SDK for interacting with backend services.
        """
        self.sdk = sdk
        print("Metrics collector initialized.")

    async def collect_api_metrics(self, endpoint: str, response_time_ms: float, status_code: int, user_id: str):
        """Collects and stores metrics for a single API request."""
        metric_data = {
            "metric_type": "api_latency",
            "timestamp": datetime.utcnow().isoformat(),
            "value": response_time_ms,
            "metadata": {
                "endpoint": endpoint,
                "status_code": status_code,
                "user_id": user_id
            }
        }
        self.sdk.store_metric(metric_data)

    async def collect_resource_metrics(self):
        """Collects and stores current system resource utilization."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()

        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_info.percent,
            "disk_io_read": disk_io.read_bytes,
            "disk_io_write": disk_io.write_bytes
        }

        for name, value in metrics.items():
            metric_data = {
                "metric_type": f"system_resource_{name}",
                "timestamp": datetime.utcnow().isoformat(),
                "value": value,
                "metadata": {"host": psutil.Process().pid} # Example metadata
            }
            self.sdk.store_metric(metric_data)
        print("Collected resource metrics.")

    async def collect_db_metrics(self, query_type: str, execution_time_ms: float, collection: str):
        """Collects and stores metrics for a database query."""
        metric_data = {
            "metric_type": "db_query_latency",
            "timestamp": datetime.utcnow().isoformat(),
            "value": execution_time_ms,
            "metadata": {
                "query_type": query_type, # e.g., "find", "update_one"
                "collection": collection
            }
        }
        self.sdk.store_metric(metric_data)

    async def collect_websocket_metrics(self, connection_count: int, message_rate_per_sec: float):
        """Collects and stores metrics for WebSocket connections."""
        timestamp = datetime.utcnow().isoformat()
        self.sdk.store_metric({
            "metric_type": "websocket_connections",
            "timestamp": timestamp,
            "value": connection_count,
            "metadata": {}
        })
        self.sdk.store_metric({
            "metric_type": "websocket_message_rate",
            "timestamp": timestamp,
            "value": message_rate_per_sec,
            "metadata": {}
        })
        print("Collected WebSocket metrics.")

    async def aggregate_hourly_metrics(self):
        """
        A background job to aggregate raw metrics into hourly summaries.
        This is a conceptual placeholder.
        """
        # In a real implementation, this would query the raw metrics from the last hour,
        # calculate aggregates (avg, max, min, p95, etc.), and store them in an
        # aggregate collection.
        print("Running hourly metric aggregation job...")
        # 1. Get last hour's raw metrics
        # 2. Calculate aggregates
        # 3. Store in 'performance_aggregates' collection
        print("Hourly aggregation complete.")

# Example of middleware integration in FastAPI
# @app.middleware("http")
# async def metrics_middleware(request: Request, call_next):
#     start_time = time.time()
#     response = await call_next(request)
#     response_time_ms = (time.time() - start_time) * 1000
#
#     # Assuming user_id is attached to request state by auth middleware
#     user_id = request.state.user.get("id") if hasattr(request, "state") and hasattr(request.state, "user") else "anonymous"
#
#     collector = MetricsCollector(sdk=AgentSDK())
#     await collector.collect_api_metrics(
#         endpoint=request.url.path,
#         response_time_ms=response_time_ms,
#         status_code=response.status_code,
#         user_id=user_id
#     )
#     return response
