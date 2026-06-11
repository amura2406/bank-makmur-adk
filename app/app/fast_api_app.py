# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from pydantic import BaseModel

import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Configure session and memory service URIs
use_in_memory = (
    os.environ.get("USE_IN_MEMORY_SESSION") == "true"
    or os.environ.get("INTEGRATION_TEST") == "TRUE"
    or not os.environ.get("GOOGLE_CLOUD_PROJECT")
)

engine_id = os.environ.get("VERTEX_ENGINE_ID")

if engine_id:
    # Proxy mode to leverage deployed Vertex AI Reasoning Engine / Agent Runtime
    import vertexai
    import uuid
    import json
    import asyncio
    from fastapi import Request
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from typing import Optional, List, Dict, Any

    app = FastAPI(title="app-proxy", description="Proxy for Vertex AI Agent Engine")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _agent_client = None

    def get_agent():
        global _agent_client
        if _agent_client is None:
            location = os.environ.get("GOOGLE_CLOUD_LOCATION") or "asia-southeast1"
            vertexai.init(project=project_id, location=location)
            client = vertexai.Client(project=project_id, location=location)
            _agent_client = client.agent_engines.get(name=engine_id)
        return _agent_client

    class SessionRequest(BaseModel):
        state: Optional[Dict[str, Any]] = None

    @app.post("/apps/app/users/{user_id}/sessions")
    def create_session(user_id: str, req: SessionRequest):
        session_id = str(uuid.uuid4())
        try:
            get_agent().create_session(user_id=user_id, session_id=session_id)
        except Exception as e:
            logger.log_text(f"Proxy create_session warning: {e}", severity="WARNING")
        return {
            "id": session_id,
            "appName": "app",
            "userId": user_id,
            "state": req.state or {},
            "events": [],
        }

    class Part(BaseModel):
        text: str

    class NewMessage(BaseModel):
        role: str
        parts: List[Part]

    class RunRequest(BaseModel):
        app_name: str
        user_id: str
        session_id: str
        new_message: NewMessage
        streaming: bool = True

    @app.post("/run_sse")
    async def run_sse(req: RunRequest):
        async def sse_generator():
            message_text = req.new_message.parts[0].text
            try:
                def run_stream():
                    return list(get_agent().stream_query(
                        message=message_text,
                        user_id=req.user_id,
                        session_id=req.session_id
                    ))
                
                events = await asyncio.to_thread(run_stream)
                for event in events:
                    if hasattr(event, "model_dump"):
                        event_dict = event.model_dump(mode='json')
                    elif isinstance(event, dict):
                        event_dict = event
                    else:
                        event_dict = vars(event)
                    
                    yield f"data: {json.dumps(event_dict)}\n\n"
            except Exception as e:
                logger.log_text(f"Proxy stream_query error: {e}", severity="ERROR")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                
        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    class Feedback(BaseModel):
        score: int
        user_id: str
        session_id: str
        text: str

    @app.post("/feedback")
    def collect_feedback(feedback: Feedback):
        current_agent = get_agent()
        if hasattr(current_agent, "register_feedback"):
            try:
                current_agent.register_feedback(
                    user_id=feedback.user_id,
                    session_id=feedback.session_id,
                    score=feedback.score,
                    text=feedback.text
                )
            except Exception as e:
                logger.log_text(f"Proxy register_feedback warning: {e}", severity="WARNING")
        return {"status": "success"}

else:
    # Original local execution mode
    from google.adk.cli.fast_api import get_fast_api_app

    AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if use_in_memory:
        session_service_uri = "memory://"
        memory_service_uri = "memory://"
    else:
        session_service_uri = os.environ.get("SESSION_SERVICE_URI") or "sqlite:///session.db"
        memory_service_uri = os.environ.get("MEMORY_SERVICE_URI") or "memory://"

    logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
    artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

    app: FastAPI = get_fast_api_app(
        agents_dir=AGENT_DIR,
        web=True,
        artifact_service_uri=artifact_service_uri,
        allow_origins=allow_origins,
        session_service_uri=session_service_uri,
        memory_service_uri=memory_service_uri,
        otel_to_cloud=True,
    )
    app.title = "app"
    app.description = "API for interacting with the Agent app"

    class FeedbackLocal(BaseModel):
        score: int
        user_id: str
        session_id: str
        text: str

    @app.post("/feedback")
    def collect_feedback_local(feedback: FeedbackLocal) -> dict[str, str]:
        """Collect and log feedback."""
        logger.log_struct(feedback.model_dump(), severity="INFO")
        return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

