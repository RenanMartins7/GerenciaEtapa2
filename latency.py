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

os.environ["OTEL_SERVICE_NAME"] = "latencyApi"

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

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#Prometheus Metrics collectors

request_count = Counter(
    "latency_total_requests",
    "Numero total de requisições processadas pela função latency",
    ["method", "endpoint", "status"]
)
request_latency = Histogram(
    "latency_request_duration_seconds",
    "Latencia nas requisicoes",
    ["method","endpoint"]
)

def connectionTest(host: str, parent_span) -> float:
    with tracer.start_as_current_span("ping_latency",kind=trace.SpanKind.SERVER,context=trace.set_span_in_context(parent_span)) as span:
        response = ping3.ping(host, timeout=2)
        if response == None:
            return None
        else:
            span.set_attribute("ping",response)
            return response

        


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
    request_latency.labels(
        method = request.method,
        endpoint = request.url.path
    ).observe(process_time)

    return response

@app.get("/latency")
def latency_app(tentativas: int = Query(10, ge=1), host: str = Query("8.8.8.8")):
    with tracer.start_as_current_span("latency", kind=trace.SpanKind.SERVER) as span:
        latency = 0.0
        span.set_attribute("host", host)
        span.set_attribute("NumberOfTrys", tentativas)
    
        for i in range(tentativas):
            rtt = connectionTest(host, span)
            if rtt != None:
                latency += rtt 
            else: 
                return {"message": f"Simulated HTTP request to {host} but unable to reach it"}
        
        latency = latency / tentativas

        return {"message": f"Simulated HTTP request to {host} for {tentativas} trys", "latency": latency}
            