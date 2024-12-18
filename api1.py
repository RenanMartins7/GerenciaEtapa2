import os
import random
import socket
import time
import httpx
import numpy as np
import ping3


from typing import Iterable
from fastapi import FastAPI, Query, Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import \
    OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter as OTLPSpanExporterHTTP
from opentelemetry.metrics import get_meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

resource = Resource(attributes={SERVICE_NAME: "Api_1"})


os.environ["OTEL_SERVICE_NAME"] = "ap1"


traces_endpoint = os.getenv(
    "TRACES_ENDPOINT", "http://op-otel-collector-1:4321/v1/traces"
)

metrics_endpoint = os.getenv(
    "METRICS_ENDPOINT", "http://op-otel-collector-1:4321/v1/metrics"
)

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporterHTTP(endpoint=traces_endpoint)  # trocar pra env
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)


reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=metrics_endpoint), export_interval_millis=1000
)
meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meterProvider)


# Creates a tracer from the global tracer provider
tracer = trace.get_tracer("api.tracer")


app = FastAPI()


meter = metrics.get_meter("Api_1")
request_count = meter.create_counter(
    "api_1_total_requests", unit="1", description="Number of processed requests"
)

rtt_histogram = meter.create_histogram(
    "api_1_rtt_histogram", unit="float", description="Round-Trip Time (RTT) per host"
)

sort_histogram = meter.create_histogram(
    "api_1_sort_histogram",
    unit="1",
    description="Max size of sort list before reaching timeout",
)

sum_of_n_number_histogram = meter.create_histogram(
    "api_1_sum_of_n_number_histogram",
    unit="float",
    description="Results of the sum of n numbers with 3 methods",
)

pi_histogram = meter.create_histogram(
    "api_1_pi_histogram", unit="float", description="Results of pi calculation"
)


active_requests = meter.create_up_down_counter(
    "api_1_active_requests", unit="1", description="Number of active requests"
)

def observable_gauge_function(options: metrics.CallbackOptions) -> Iterable[metrics.Observation]:
    rtt = ping3.ping("8.8.8.8", timeout=2, size=65000)
    yield metrics.Observation(rtt, {})

gauge_rtt = gauge = meter.create_observable_gauge("api_1_rtt_gauge", [observable_gauge_function])


def connectionTest(host: str, parent_span, size: int) -> float:
    with tracer.start_as_current_span(
        "ping_latency",
        kind=trace.SpanKind.SERVER,
        context=trace.set_span_in_context(parent_span),
    ) as span:
        response = ping3.ping(host, timeout=2, size=size)
        if response == None:
            return None
        else:
            span.set_attribute("ping", response)
            span.set_attribute("payload_size", size)
            return response


@app.get("/latency")
def latency_app(
    tentativas: int = Query(10, ge=1),
    host: str = Query("8.8.8.8"),
    size: int = Query(32, ge=1),
):
    with tracer.start_as_current_span("latency", kind=trace.SpanKind.SERVER) as span:
        request_count.add(1, attributes={"method:": "GET", "endpoint": "/latency"})
        latency = 0.0
        span.set_attribute("host", host)
        span.set_attribute("NumberOfTrys", tentativas)
        span.set_attribute("payload_size", size)

        for i in range(tentativas):
            rtt = connectionTest(host, span, size)
            rtt_histogram.record(rtt, attributes={"host": host})
            if rtt != None:
                latency += rtt
            else:
                return {
                    "message": f"Simulated HTTP request to {host} but unable to reach it"
                }

        latency = latency / tentativas

        return {
            "message": f"Simulated HTTP request to {host} for {tentativas} trys",
            "latency": latency,
        }


# Bubblesort implementation
def bubble(randomList, size: int, parent_span):
    with tracer.start_as_current_span(
        "bubble",
        kind=trace.SpanKind.SERVER,
        context=trace.set_span_in_context(parent_span),
    ) as child:
        bubbleList = list(randomList)
        n = len(bubbleList)

        initial_time = time.time()
        for i in range(n):
            for j in range(0, n - i - 1):
                if bubbleList[j] < bubbleList[j + 1]:
                    bubbleList[j], bubbleList[j + 1] = bubbleList[j + 1], bubbleList[j]

        total_time = time.time() - initial_time
        child.set_attribute("sample_size", size)
        child.set_attribute("total_time", total_time)
        return total_time


# Mergesort implementation
def mergeSortTracer(randomList, size: int, parent_span):
    with tracer.start_as_current_span(
        "merge",
        kind=trace.SpanKind.SERVER,
        context=trace.set_span_in_context(parent_span),
    ) as child:
        initial_time = time.time()

        returnList = mergeSort(randomList)

        total_time = time.time() - initial_time
        child.set_attribute("sample_size", size)
        child.set_attribute("total_time", total_time)

        return total_time


def mergeSort(randomList):
    mergeList = list(randomList)
    n = len(mergeList)

    if len(mergeList) <= 1:
        return mergeList

    middle = int(len(mergeList) / 2)
    left = mergeSort(mergeList[:middle])
    right = mergeSort(mergeList[middle:])

    return merge(left, right)


def merge(left, right):
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i = i + 1
        else:
            result.append(right[j])
            j = j + 1

    result.extend(left[i:])
    result.extend(right[j:])

    return result


# Selectionsort implementation
def selection(randomList, size: int, parent_span):
    with tracer.start_as_current_span(
        "selection",
        kind=trace.SpanKind.SERVER,
        context=trace.set_span_in_context(parent_span),
    ) as child:
        selectionList = list(randomList)
        n = len(selectionList)

        initial_time = time.time()
        for i in range(n):
            smallest_index = i
            for j in range(i + 1, n):
                if selectionList[j] < selectionList[smallest_index]:
                    smallest_index = j
            selectionList[i], selectionList[smallest_index] = (
                selectionList[smallest_index],
                selectionList[i],
            )

        total_time = time.time() - initial_time
        child.set_attribute("sample_size", size)
        child.set_attribute("total_time", total_time)
        return total_time


# Function to call the sort methods and collect the metrics
def sortComparison(size: int, time_out: float, increment: int, parent_span):

    with tracer.start_as_current_span(
        "comparison",
        kind=trace.SpanKind.SERVER,
        context=trace.set_span_in_context(parent_span),
    ) as parent:
        # Gradual testing with the bubble sort method
        current_size = increment
        while current_size <= size:
            randomList = [random.randint(1, current_size) for _ in range(current_size)]
            bubble_time = bubble(randomList, current_size, parent)
            if bubble_time > time_out:
                break
            current_size += increment
        parent.set_attribute("bubble_max_reached_size", current_size)
        parent.set_attribute("bubble_max_reached_time", bubble_time)
        sort_histogram.record(current_size, attributes={"sort_method": "bubble"})
        # Gradual testing with the selection sort method
        current_size = increment
        while current_size <= size:
            randomList = [random.randint(1, current_size) for _ in range(current_size)]
            selection_time = selection(randomList, current_size, parent)
            if selection_time > time_out:
                break
            current_size += increment
        parent.set_attribute("selection_max_reached_size", current_size)
        parent.set_attribute("selection_max_reached_time", selection_time)
        sort_histogram.record(current_size, attributes={"sort_method": "selection"})
        # Gradual testing with the merge sort method
        current_size = increment
        while current_size <= size:
            randomList = [random.randint(1, current_size) for _ in range(current_size)]
            merge_time = mergeSortTracer(randomList, current_size, parent)
            if merge_time > time_out:
                break
            current_size += increment
        parent.set_attribute("merge_max_reached_size", current_size)
        parent.set_attribute("merge_max_reached_time", merge_time)
        sort_histogram.record(current_size, attributes={"sort_method": "merge"})


@app.get("/sort")
def sort_app(
    max_size: int = Query(10000, ge=1),
    time_out: float = Query(2, ge=0.01),
    increment: int = Query(500, ge=1),
):
    request_count.add(1, attributes={"method:": "GET", "endpoint": "/sort"})

    with tracer.start_as_current_span("sort", kind=trace.SpanKind.SERVER) as span:
        sortComparison(max_size, time_out, increment, span)
        return {"message": f"Done sort"}


# calculate pi using the monte carlo method for a given number of seconds
def calculate_pi(seconds: int, parent_span):
    with tracer.start_as_current_span(
        "calculate_pi", context=trace.set_span_in_context(parent_span)
    ) as span:
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
        pi_histogram.record(pi)
        return pi


@app.get("/calculate-pi")
def calculate_pi_endpoint(seconds: float = Query(1, ge=0.0001)):
    with tracer.start_as_current_span("calculate_pi_endpoint") as span:
        pi = calculate_pi(int(seconds), span)
        request_count.add(1, attributes={"method:": "GET", "endpoint": "/calculate-pi"})
        return {"pi": pi}


def method_1(target: int, parent_span):
    with tracer.start_as_current_span(
        "method_1", context=trace.set_span_in_context(parent_span)
    ) as span:
        span.set_attribute("target", target)
        result = sum(range(target + 1))
        span.set_attribute("result", result)
        return result


def method_2(target: int, parent_span):
    with tracer.start_as_current_span(
        "method_2", context=trace.set_span_in_context(parent_span)
    ) as span:
        span.set_attribute("target", target)
        result = target * (target + 1) // 2
        span.set_attribute("result", result)
        return result


def method_3(target: int, parent_span):
    with tracer.start_as_current_span(
        "method_3", context=trace.set_span_in_context(parent_span)
    ) as span:
        span.set_attribute("target", target)
        result = 0
        for i in range(target + 1):
            result += i
        span.set_attribute("result", result)
        return result


@app.get("/sum-of-n-numbers")
def sum_of_n_numbers(target: int = Query(100000000, ge=1)):
    with tracer.start_as_current_span("sum_of_n_numbers") as span:
        result_1 = method_1(target, span)
        sum_of_n_number_histogram.record(result_1, attributes={"method": "method_1"})
        result_2 = method_2(target, span)
        sum_of_n_number_histogram.record(result_2, attributes={"method": "method_2"})
        result_3 = method_3(target, span)
        sum_of_n_number_histogram.record(result_3, attributes={"method": "method_3"})
        request_count.add(
            1, attributes={"method:": "GET", "endpoint": "/sum-of-n-numbers"}
        )
        return {
            "method_1_result": result_1,
            "method_2_result": result_2,
            "method_3_result": result_3,
        }


def create_delete_objects_method_1(count: int, parent_span):
    with tracer.start_as_current_span(
        "create_delete_objects_method_1", context=trace.set_span_in_context(parent_span)
    ) as span:
        span.set_attribute("object_count", count)
        objects = [object() for _ in range(count)]
        span.set_attribute("object_size", objects.__sizeof__())
        del objects
        span.set_attribute("status", "completed")
        return "Method 1 completed"


def create_delete_objects_method_2(count: int, parent_span):
    with tracer.start_as_current_span(
        "create_delete_objects_method_2", context=trace.set_span_in_context(parent_span)
    ) as span:
        span.set_attribute("object_count", count)
        objects = []
        for _ in range(count):
            objects.append(object())
        span.set_attribute("object_size", objects.__sizeof__())
        del objects
        span.set_attribute("status", "completed")
        return "Method 2 completed"


@app.get("/object-creation-deletion")
def test_object_creation_deletion(count: int = Query(1000000, ge=1)):
    with tracer.start_as_current_span("test_object_creation_deletion") as span:
        result_1 = create_delete_objects_method_1(count, span)
        result_2 = create_delete_objects_method_2(count, span)
        request_count.add(
            1, attributes={"method:": "GET", "endpoint": "/object-creation-deletion"}
        )
        return {
            "method_1_result": result_1,
            "method_2_result": result_2,
        }


@app.middleware("http")
async def count_active_requests(request: Request, call_next):
    active_requests.add(1)
    response = await call_next(request)
    active_requests.add(-1)
    return response


"""


    
active_requests = meter.create_gauge(
    "api_1_active_requests",
    unit="1",
    description="Number of active requests"
)

current_active_requests = 0
"""
