from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, PeriodicExportingMetricReader

from src.core.config import settings

def init_telemetry(metric_reader=None):
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)
    
    if metric_reader is None:
        metric_reader = InMemoryMetricReader()
    
    meter_provider = MeterProvider(metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    return tracer_provider, meter_provider, metric_reader


def init_production_telemetry():
    if not settings.OTEL_ENABLED:
        return init_telemetry()

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    tracer_provider = TracerProvider(resource=resource)
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore[import-not-found]
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces")
            )
        )
    trace.set_tracer_provider(tracer_provider)

    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter  # type: ignore[import-not-found]
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/metrics")
        )
    else:
        metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    return tracer_provider, meter_provider, metric_reader

meter = metrics.get_meter("archon.metrics")
tracer = trace.get_tracer("archon.tracer")

parse_duration = meter.create_histogram(
    name="archon_parse_duration_seconds",
    description="Duration of parsing operations",
    unit="s",
)

resolver_duration = meter.create_histogram(
    name="archon_resolver_duration_seconds",
    description="Duration of resolver operations",
    unit="s",
)

retrieval_latency = meter.create_histogram(
    name="archon_retrieval_latency_seconds",
    description="Duration of retrieval operations",
    unit="s",
)

agent_execution_latency = meter.create_histogram(
    name="archon_agent_execution_latency_seconds",
    description="Duration of agent execution",
    unit="s",
)

# Global state for observable gauges
_accuracy_ratio = 0.0
_nodes_total = 0

def _get_accuracy_ratio(options):
    yield metrics.Observation(_accuracy_ratio)

def _get_nodes_total(options):
    yield metrics.Observation(_nodes_total)

resolver_accuracy_ratio = meter.create_observable_gauge(
    name="archon_resolver_accuracy_ratio",
    callbacks=[_get_accuracy_ratio],
    description="Accuracy ratio of the symbol resolver",
)

knowledge_graph_nodes_total = meter.create_observable_gauge(
    name="archon_knowledge_graph_nodes_total",
    callbacks=[_get_nodes_total],
    description="Total nodes in the knowledge graph",
)

def set_resolver_accuracy(value: float):
    global _accuracy_ratio
    _accuracy_ratio = value

def set_knowledge_graph_nodes(value: int):
    global _nodes_total
    _nodes_total = value
