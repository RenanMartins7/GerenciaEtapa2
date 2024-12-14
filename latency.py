import os
import time
import httpx
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
    SERVICE_NAME: "LATENCY_API"
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

#Instrumentator().instrument(app).expose(app, endpoint="/metrics")

#Prometheus Metrics collectors
"""
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
"""
def connectionTest(host: str, parent_span) -> float:
    with tracer.start_as_current_span("ping_latency",kind=trace.SpanKind.SERVER,context=trace.set_span_in_context(parent_span)) as span:
        response = ping3.ping(host, timeout=2)
        if response == None:
            return None
        else:
            span.set_attribute("ping",response)
            return response

        

"""
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
"""
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
            