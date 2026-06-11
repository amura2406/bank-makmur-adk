import os
import pytest
import asyncio
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from tests.run_e2e import execute_turn

@pytest.fixture(scope="module")
def otel_exporter():
    provider = trace.get_tracer_provider()
    if not hasattr(provider, "add_span_processor"):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    return exporter

@pytest.mark.anyio
async def test_telemetry_latency_and_spans(otel_exporter):
    """Verify that latency is within limits and trace spans are correctly recorded."""
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    # Clear previously recorded spans
    otel_exporter.clear()
    
    # 1. Trigger a tool call query (balance)
    response = await execute_turn("Can you check my main pocket balance?", [], mode, endpoint)
    
    # Assert performance bounds
    if mode == "mock":
        assert response["ttft_seconds"] <= 0.8, f"TTFT {response['ttft_seconds']}s exceeded 0.8s"
        assert response["latency_seconds"] <= 2.5, f"Latency {response['latency_seconds']}s exceeded 2.5s"
    else:
        assert response["ttft_seconds"] <= 10.0, f"TTFT {response['ttft_seconds']}s exceeded 10.0s"
        assert response["latency_seconds"] <= 20.0, f"Latency {response['latency_seconds']}s exceeded 20.0s"
    
    # Assert spans if in mock mode
    if mode == "mock":
        spans = otel_exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "agent_turn" in span_names, f"Expected 'agent_turn' span in {span_names}"
        assert "tool_call" in span_names, f"Expected 'tool_call' span in {span_names}"
        
        # Verify tool_call has tool_name attribute
        tool_spans = [s for s in spans if s.name == "tool_call"]
        assert len(tool_spans) > 0
        assert tool_spans[0].attributes.get("tool_name") == "get_pocket_balance"

@pytest.mark.anyio
async def test_telemetry_llm_spans(otel_exporter):
    """Verify that LLM-specific calls record llm_call spans."""
    mode = os.getenv("E2E_MODE", "mock")
    endpoint = os.getenv("E2E_ENDPOINT", "http://localhost:8000")
    
    otel_exporter.clear()
    
    # Trigger a query that calls LLM name logic
    response = await execute_turn("What is my name?", [], mode, endpoint)
    
    if mode == "mock":
        assert response["ttft_seconds"] <= 0.8
        assert response["latency_seconds"] <= 2.5
    else:
        assert response["ttft_seconds"] <= 10.0
        assert response["latency_seconds"] <= 20.0
    
    if mode == "mock":
        spans = otel_exporter.get_finished_spans()
        span_names = [s.name for s in spans]
        assert "agent_turn" in span_names, f"Expected 'agent_turn' span in {span_names}"
        assert "llm_call" in span_names, f"Expected 'llm_call' span in {span_names}"
