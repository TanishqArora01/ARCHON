import asyncio
import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

from src.observability.telemetry import init_telemetry, set_resolver_accuracy, set_knowledge_graph_nodes
from src.observability.decorators import trace_and_time

reader = InMemoryMetricReader()
init_telemetry(reader)

@pytest.fixture(scope="session", autouse=True)
def setup_telemetry():
    yield reader
    reader.shutdown()

@pytest.mark.asyncio
async def test_trace_and_time_async_success(setup_telemetry):
    # Retrieve the reader from fixture
    reader = setup_telemetry
    
    # Define a dummy function with the decorator
    @trace_and_time("parse_duration", custom_label="test")
    async def dummy_func():
        await asyncio.sleep(0.01)
        return "success"
    
    result = await dummy_func()
    assert result == "success"
    
    # Collect metrics
    metrics_data = reader.get_metrics_data()
    
    # Find the parse_duration metric
    found_metric = None
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == "archon_parse_duration_seconds":
                    found_metric = metric
                    break
    
    assert found_metric is not None
    # Check that it recorded a value and labels
    data_points = list(found_metric.data.data_points)
    assert len(data_points) >= 1
    
    found_point = None
    for pt in data_points:
        if pt.attributes.get("custom_label") == "test":
            found_point = pt
            break
            
    assert found_point is not None
    assert found_point.sum >= 0.01

@pytest.mark.asyncio
async def test_trace_and_time_async_exception(setup_telemetry):
    reader = setup_telemetry
    
    @trace_and_time("parse_duration")
    async def dummy_func_fail():
        raise ValueError("test error")
    
    with pytest.raises(ValueError):
        await dummy_func_fail()
        
    metrics_data = reader.get_metrics_data()
    found_metric = None
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == "archon_parse_duration_seconds":
                    found_metric = metric
                    break
                    
    assert found_metric is not None
    data_points = list(found_metric.data.data_points)
    assert len(data_points) >= 1

def test_gauges(setup_telemetry):
    reader = setup_telemetry
    
    set_resolver_accuracy(0.85)
    set_knowledge_graph_nodes(42)
    
    metrics_data = reader.get_metrics_data()
    
    accuracy_metric = None
    nodes_metric = None
    
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == "archon_resolver_accuracy_ratio":
                    accuracy_metric = metric
                elif metric.name == "archon_knowledge_graph_nodes_total":
                    nodes_metric = metric
                    
    assert accuracy_metric is not None
    assert nodes_metric is not None
    
    accuracy_points = list(accuracy_metric.data.data_points)
    assert accuracy_points[0].value == 0.85
    
    nodes_points = list(nodes_metric.data.data_points)
    assert nodes_points[0].value == 42
