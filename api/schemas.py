from pydantic import BaseModel

class PromptRequest(BaseModel):
    prompt: str
    use_shatru: bool = False
    session_id: str = "demo_session_001"

class ExecutionResponse(BaseModel):
    status: str
    output: str | None = None
    armor_iq_status: str
    armor_claw_status: str | None = None
    latency_ms: float