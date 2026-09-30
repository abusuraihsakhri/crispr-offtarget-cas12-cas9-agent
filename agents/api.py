"""FastAPI server for the rule-based audit subsystem."""

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from .base import AuditLogger, SecurityException
from .metrics import GLOBAL_METRICS
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="CRISPR Off-Target Agent API",
    description="Research-use deterministic audit utilities",
    version="2.1.0",
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(..., min_length=1, max_length=4000)


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "service": "crispr-offtarget-cas12-cas9-agent",
        "version": "2.1.0",
    }


@app.get("/metrics", response_class=Response)
def metrics():
    return Response(
        content=GLOBAL_METRICS.export_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        return supervisor.process_task(payload).to_dict()
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifier rejected") from exc


@app.post("/api/chat")
def api_chat(request: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(request.query)}
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifier rejected") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process query") from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {
        "audit_trail": AuditLogger.get_trail(),
        "verified": AuditLogger.verify_integrity(),
    }
