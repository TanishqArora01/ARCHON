import time
import asyncio
import functools
from opentelemetry.trace import Status, StatusCode
from src.observability.telemetry import tracer

def trace_and_time(metric_name: str, **default_labels):
    """
    Decorator that traces execution and measures duration into an OpenTelemetry histogram.
    `metric_name` should be the variable name of the histogram in `src.observability.telemetry`.
    """
    def decorator(func):
        import src.observability.telemetry as telemetry
        histogram = getattr(telemetry, metric_name, None)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                for k, v in default_labels.items():
                    span.set_attribute(k, v)
                
                labels = dict(default_labels)
                
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    if histogram:
                        histogram.record(duration, labels)
                        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                for k, v in default_labels.items():
                    span.set_attribute(k, v)
                
                labels = dict(default_labels)
                
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
                finally:
                    duration = time.perf_counter() - start_time
                    if histogram:
                        histogram.record(duration, labels)
                        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
