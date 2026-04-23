import json
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from backend.agents.orchestrator import get_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())

    async def generate():
        try:
            agent = get_agent()
            final_response: str | None = None

            yield _sse({"type": "session", "session_id": session_id})

            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=request.message)]},
                config={"configurable": {"thread_id": session_id}},
                version="v2",
            ):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        token = chunk.content
                        if isinstance(token, str) and token and not getattr(chunk, "tool_call_chunks", None):
                            final_response = (final_response or "") + token
                            yield _sse({"type": "chunk", "content": token})

                elif kind == "on_tool_start":
                    raw_input = event["data"].get("input", {})
                    try:
                        safe_input = json.loads(json.dumps(raw_input, default=str))
                    except Exception:
                        safe_input = str(raw_input)
                    yield _sse({"type": "tool_call", "tool": name, "input": safe_input})

                elif kind == "on_tool_end":
                    output = event["data"].get("output", "")
                    if hasattr(output, "content"):
                        output = output.content
                    yield _sse({"type": "tool_result", "tool": name, "output": str(output)})

                elif kind == "on_chain_end":
                    out = event.get("data", {}).get("output")
                    if isinstance(out, dict) and "messages" in out:
                        for msg in reversed(out["messages"]):
                            content = getattr(msg, "content", "")
                            is_ai = not getattr(msg, "tool_calls", None)
                            if content and is_ai:
                                if not final_response:
                                    final_response = content
                                break

            if final_response:
                yield _sse({"type": "response", "content": final_response})

            yield _sse({"type": "done"})

        except Exception as exc:
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
