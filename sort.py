import os
import time
import numpy as np
import random
import socket
import ping3


from fastapi import FastAPI, Query, Request

from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

resource = Resource(attributes={
    SERVICE_NAME: "SORT_API"
})


os.environ["OTEL_SERVICE_NAME"] = "sortApi"

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporterHTTP(endpoint="http://op-otel-collector-1:4321/v1/traces")  # trocar pra env
)
provider.add_span_processor(processor)  
trace.set_tracer_provider(provider)

reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://op-otel-collector-1:4321/v1/metrics")
)
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)



# Creates a tracer from the global tracer provider
tracer = trace.get_tracer("api.tracer")


app = FastAPI()
# Prometheus exporter
#Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#Prometheus Metrics collectors
"""
request_count = Counter(
    "sort_total_requests",
    "Numero total de requisições processadas pela funcao sort",
    ["method", "endpoint", "status"]
)
request_sort = Histogram(
    "sort_request_duration_seconds",
    "Latencia nas requisicoes",
    ["method","endpoint"]
)
"""






# calculate pi using the monte carlo method for a given number of seconds
def calculate_pi(seconds: int, parent_span):
    with tracer.start_as_current_span("calculate_pi", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("seconds", seconds)
        inside = 0
        total = 0
        start_time = time.time()
        while time.time() - start_time < seconds:
            x = random.random()
            y = random.random()
            if x**2 + y**2 <= 1:
                inside += 1
            total += 1
        pi = 4 * inside / total
        span.set_attribute("inside", inside)
        span.set_attribute("total", total)
        span.set_attribute("pi", pi)
        return pi

@app.get("/calculate-pi")
async def calculate_pi_endpoint(seconds: float = Query(1,ge=0.0001)):
    with tracer.start_as_current_span("calculate_pi_endpoint") as span:
        pi = calculate_pi(seconds, span)
        return {"pi": pi}


def method_1(target: int, parent_span):
    with tracer.start_as_current_span("method_1", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("target", target)
        result = sum(range(target + 1))
        span.set_attribute("result", result)
        return result

def method_2(target: int, parent_span):
    with tracer.start_as_current_span("method_2", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("target", target)
        result = target * (target + 1) // 2
        span.set_attribute("result", result)
        return result

def method_3(target: int, parent_span):
    with tracer.start_as_current_span("method_3", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("target", target)
        result = 0
        for i in range(target + 1):
            result += i
        span.set_attribute("result", result)
        return result

@app.get("/sum-of-n-numbers")
async def sum_of_n_numbers(target: int = Query(100000000, ge=1)):
    with tracer.start_as_current_span("sum_of_n_numbers") as span:
        result_1 = method_1(target, span)
        result_2 = method_2(target, span)
        result_3 = method_3(target, span)
        return {
            "method_1_result": result_1,
            "method_2_result": result_2,
            "method_3_result": result_3
        }

def create_delete_objects_method_1(count: int, parent_span):
    with tracer.start_as_current_span("create_delete_objects_method_1", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("object_count", count)
        objects = [object() for _ in range(count)]
        span.set_attribute("object_size", objects.__sizeof__())
        del objects
        span.set_attribute("status", "completed")
        return "Method 1 completed"

def create_delete_objects_method_2(count: int, parent_span):
    with tracer.start_as_current_span("create_delete_objects_method_2", context=trace.set_span_in_context(parent_span)) as span:
        span.set_attribute("object_count", count)
        objects = []
        for _ in range(count):
            objects.append(object())
        span.set_attribute("object_size", objects.__sizeof__())
        del objects
        span.set_attribute("status", "completed")
        return "Method 2 completed"
    
@app.get("/object-creation-deletion")
async def test_object_creation_deletion(count: int = Query(1000000, ge=1)):
    with tracer.start_as_current_span("test_object_creation_deletion") as span:
        result_1 = create_delete_objects_method_1(count, span)
        result_2 = create_delete_objects_method_2(count, span)
        return {
            "method_1_result": result_1,
            "method_2_result": result_2,
        }