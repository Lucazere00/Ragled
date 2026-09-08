from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import RateLimitError
from pydantic import BaseModel, Field

from main import run_pipeline


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict | None = None


class ChatResponse(BaseModel):
    type: Literal["text", "semantic", "structured", "hybrid"]
    answer: str
    chart: dict | None = None
    chart_message: str | None = None


app = FastAPI(title="Ragled API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "Ragled API", "health": "/health", "chat": "/api/chat"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = run_pipeline(request.message.strip())
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Limite Groq raggiunto. Riprova tra qualche minuto o verifica il piano/API key.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Impossibile elaborare la domanda.") from exc

    if isinstance(result, dict):
        chart = result.get("chart")
        if chart:
            chart = {
                "chartType": chart["chart_type"],
                "labels": chart["labels"],
                "series": [{
                    "name": "Fatalities" if "fatalit" in chart["description"].lower() else "Events",
                    "values": chart["values"],
                }],
                "path": chart["path"],
                "description": chart["description"],
                "highlightedLabel": chart.get("highlighted_label"),
            }
        return ChatResponse(
            type=result.get("type", "structured"),
            answer=str(result.get("answer", "")),
            chart=chart,
            chart_message=result.get("chart_message"),
        )

    return ChatResponse(type="text", answer=str(result))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=False)
