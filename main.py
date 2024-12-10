import os
import time
import httpx
import numpy as np
import random
import socket
import ping3


from fastapi import FastAPI, Query

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
    OTLPSpanExporter as OTLPSpanExporterHTTP
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


endpoint = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://host.docker.internal:4318/v1/traces"
)

os.environ["OTEL_SERVICE_NAME"] = "api"

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


#Bubblesort implementation
def bubble(randomList):
    with tracer.start_as_current_span("bubble", kind=trace.SpanKind.CLIENT) as child:
        bubbleList = list(randomList)
        n = len(bubbleList)

        for i in range(n):
            for j in range(0, n-i-1):
                if bubbleList[j] < bubbleList[j+1]:
                    bubbleList[j], bubbleList[j+1] = bubbleList[j+1], bubbleList[j]
        return bubbleList

#Mergesort implementation
def mergeSortTracer(randomList):
    with tracer.start_as_current_span("merge",kind=trace.SpanKind.CLIENT) as child:
        returnList = mergeSort(randomList)
        return returnList



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
def selection(randomList):
    with tracer.start_as_current_span("selection", kind=trace.SpanKind.CLIENT) as child:
        selectionList = list(randomList)
        n = len(selectionList)

        for i in range(n):
            smallest_index = i
            for j in range(i+1, n):
                if selectionList[j] < selectionList[smallest_index]:
                    smallest_index = j
            selectionList[i], selectionList[smallest_index] = selectionList[smallest_index], selectionList[i]

        return selectionList 

#Function to call the sort methods and collect the metrics
def sortComparison(size:int):

    with tracer.start_as_current_span("comparison", kind=trace.SpanKind.SERVER) as parent:
        randomList = [random.randint(1,10000) for _ in range(10000)]
        bubbleList = bubble(randomList)
        mergeList = mergeSortTracer(randomList)
        selectionList = selection(randomList)
        

        



@app.get("/sort")
def sort_app():
	with tracer.start_as_current_span("sort",kind=trace.SpanKind.SERVER) as span:
    		sortComparison(10000)
    		return {"message": f"Done sort"}



def connectionTest(host: str) -> float:
    with tracer.start_as_current_span("ping_latency",kind=trace.SpanKind.CLIENT) as span:
        response = ping3.ping(host, timeout=2)
        if response == None:
            return None
        else:
            span.set_attribute("ping",response)
            return response

        


@app.get("/latency")
def latency_app(tentativas: int = Query(10, ge=1), host: str = Query("8.8.8.8")):
    with tracer.start_as_current_span("latency", kind=trace.SpanKind.SERVER) as span:
        latency = 0.0
        span.set_attribute("host", host)
        span.set_attribute("NumberOfTrys", tentativas)
    
        for i in range(tentativas):
            rtt = connectionTest(host)
            if rtt != None:
                latency += rtt 
            else: 
                return {"message": f"Simulated HTTP request to {host} but unable to reach it"}
        
        latency = latency / tentativas

        return {"message": f"Simulated HTTP request to {host} for {tentativas} trys", "latency": latency}
            












"""
#Simulação de Requisições HTTP para Outros Serviços
async def simulate_http_request(url: str, duration: float):
	async with httpx.AsyncClient() as client:
		with tracer.start_as_current_span("http_request") as child:
			child.set_attribute("url", url)
			child.set_attribute("duration", duration)
			response = await client.get(url)
			return response.text

#Calculo de matriz grandes
def matrix_multiplication(size: int):
    	A = np.random.rand(size, size)
    	B = np.random.rand(size, size)
    	with tracer.start_as_current_span("matrix_multiplication") as child:
        	child.set_attribute("size", size)
        	C = np.dot(A, B)  # Multiplicação de matrizes
    	return C

#Simulação de Carga
async def simulate_network_request():
    	async with httpx.AsyncClient() as client:
        	response = await client.get("https://httpbin.org/get") 
        	return response.json()

	


def cpu_load(duration: int):
    with tracer.start_as_current_span("cpu_load") as child:
        sum = 0
        end_time = time.time() + duration
        while time.time() < end_time:
            sum += 1 / 1000
            pass
        child.set_attribute("sum", sum)


def memory_load(size_mb: int, duration: float):
    with tracer.start_as_current_span("memory_load") as child:
        child.set_attribute("memory_size", size_mb)
        data = bytearray(size_mb * 1024 * 1024)
        time.sleep(duration)
        del data


def call_memory_load(size_mb: int, duration: int):
    with tracer.start_as_current_span("call_memory_load") as child:
        memory_load(int(size_mb / 2), duration / 2)
        memory_load(int(size_mb / 2), duration / 2)


#Endpoint para requisições HTTP
@app.get("/http-request")
async def simulate_http_request_endpoint(url: str = "https://google.com", duration: float = 1.5):
	response = await simulate_http_request(url, duration)
	return {"message": f"Simulated HTTP request to {url} for {duration} seconds", "response": response}

#Endpoint para multiplicação de matrizes
@app.get("/matrix-multiplication")
def simulate_matrix_multiplication(size: int = 5000):
	with tracer.start_as_current_span("matrix_mult_call") as span:
			
		initialTime = time.time()
		C = matrix_multiplication(size)
		totalTime = time.time() - initialTime
		span.set_attribute("matrix_mult_call.value", str(totalTime))
		return {"message": f"Performed matrix multiplication for {sizeFunction}x{size} matrices in {totalTime:.2f} seconds."}


#Endpoint para simulação de carga de rede
@app.get("/network-load")
async def simulate_network_load():
	with tracer.start_as_current_span("network_load_call") as span:
    		response = await simulate_network_request()
    		return {"message": "Simulated network load with response", "data": response}



@app.get("/cpu-load")
def simulate_cpu_load(duration: int = 10):
    with tracer.start_as_current_span("cpu_call") as span:
        cpu_load(duration)
        return {"message": f"Simulating CPU load for {duration} seconds"}


@app.get("/memory-load")
def simulate_memory_load(size_mb: int = 100, duration: int = 10):
    with tracer.start_as_current_span("memory_call") as span:
        call_memory_load(size_mb, duration)
        return {
            "message": f"Simulating memory load of {size_mb} MB for {duration} seconds"
        }
"""