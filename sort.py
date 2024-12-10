import os
import time
import httpx
import numpy as np
import random
import socket
import ping3


from fastapi import FastAPI, Query, Request

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter as OTLPSpanExporterHTTP
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram


endpoint = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://host.docker.internal:4318/v1/traces"
)

os.environ["OTEL_SERVICE_NAME"] = "sortApi"

provider = TracerProvider()
processor = BatchSpanProcessor(
    OTLPSpanExporterHTTP(endpoint=endpoint)  # trocar pra env
)
provider.add_span_processor(processor)

# Sets the global default tracer provider
trace.set_tracer_provider(provider)

# Creates a tracer from the global tracer provider
tracer = trace.get_tracer("api.tracer")


app = FastAPI()
# Prometheus exporter
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#Prometheus Metrics collectors

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



#Bubblesort implementation
def bubble(randomList, size: int, parent_span):
    with tracer.start_as_current_span("bubble", kind=trace.SpanKind.SERVER,context=trace.set_span_in_context(parent_span)) as child:
        bubbleList = list(randomList)
        n = len(bubbleList)

        initial_time = time.time()
        for i in range(n):
            for j in range(0, n-i-1):
                if bubbleList[j] < bubbleList[j+1]:
                    bubbleList[j], bubbleList[j+1] = bubbleList[j+1], bubbleList[j]

        total_time = time.time() - initial_time
        child.set_attribute("sample_size", size)
        child.set_attribute("total_time", total_time)
        return total_time

#Mergesort implementation
def mergeSortTracer(randomList,size: int, parent_span):
    with tracer.start_as_current_span("merge",kind=trace.SpanKind.SERVER, context=trace.set_span_in_context(parent_span)) as child:
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
            i = i+1
        else:
            result.append(right[j])
            j = j+1
    
    result.extend(left[i:])
    result.extend(right[j:])

    return result
#Selectionsort implementation
def selection(randomList, size:int, parent_span):
    with tracer.start_as_current_span("selection", kind=trace.SpanKind.SERVER, context=trace.set_span_in_context(parent_span)) as child:
        selectionList = list(randomList)
        n = len(selectionList)

        initial_time = time.time()
        for i in range(n):
            smallest_index = i
            for j in range(i+1, n):
                if selectionList[j] < selectionList[smallest_index]:
                    smallest_index = j
            selectionList[i], selectionList[smallest_index] = selectionList[smallest_index], selectionList[i]

        total_time = time.time() - initial_time
        child.set_attribute("sample_size", size)
        child.set_attribute("total_time", total_time)
        return total_time

#Function to call the sort methods and collect the metrics
def sortComparison(size:int, time_out: float, increment: int,  parent_span):

    with tracer.start_as_current_span("comparison", kind=trace.SpanKind.SERVER, context=trace.set_span_in_context(parent_span)) as parent:
        #Gradual testing with the bubble sort method
        current_size = increment
        while(current_size <= size):
            randomList = [random.randint(1,current_size) for _ in range(current_size)]
            bubble_time = bubble(randomList, current_size, parent)
            if bubble_time > time_out: break
            current_size += increment
        parent.set_attribute("bubble_max_reached_size", current_size)
        parent.set_attribute("bubble_max_reached_time", bubble_time)
        #Gradual testing with the selection sort method
        current_size = increment
        while(current_size <= size):
            randomList = [random.randint(1,current_size) for _ in range(current_size)]
            selection_time = selection(randomList, current_size, parent)
            if selection_time > time_out: break
            current_size += increment
        parent.set_attribute("selection_max_reached_size", current_size)
        parent.set_attribute("selection_max_reached_time", selection_time)
        #Gradual testing with the merge sort method
        current_size = increment
        while(current_size <= size):
            randomList = [random.randint(1,current_size) for _ in range(current_size)]
            merge_time = mergeSortTracer(randomList, current_size, parent)
            if merge_time > time_out: break
            current_size += increment
        parent.set_attribute("merge_max_reached_size", current_size)
        parent.set_attribute("merge_max_reached_time", merge_time)
                




@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    request_count.labels(
        method = request.method,
        endpoint = request.url.path,
        status = response.status_code
    ).inc()
    request_sort.labels(
        method = request.method,
        endpoint = request.url.path
    ).observe(process_time)

    return response

    

@app.get("/sort")
def sort_app(max_size: int = Query(10000, ge=1), time_out: float = Query(2, ge=0.01), increment: int = Query(500, ge=1)):
	with tracer.start_as_current_span("sort",kind=trace.SpanKind.SERVER) as span:
    		sortComparison(max_size, time_out, increment, span)
    		return {"message": f"Done sort"}