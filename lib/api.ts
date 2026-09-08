import { mockChatResponse, mockEvents } from "@/lib/mockData";
import type { ChatResponse, EventFilters, RagledEvent } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const USE_MOCK_DATA = process.env.NEXT_PUBLIC_USE_MOCK_DATA === "true";
const MOCK_DELAY_MS = 550;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function sendChatMessage(message: string, context?: RagledEvent): Promise<ChatResponse> {
  if (USE_MOCK_DATA) {
    await wait(MOCK_DELAY_MS);
    const response = mockChatResponse(message);
    return context
      ? {
          ...response,
          answer: `Contesto evento: ${context.title} (${context.place}, ${context.date}). ${response.answer}`
        }
      : response;
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, context }),
      signal: AbortSignal.timeout(120000)
    });
  } catch {
    throw new Error("Backend non raggiungibile. Avvia ./venv/bin/python api_server.py sulla porta 8000.");
  }

  if (!res.ok) {
    let detail = "Impossibile recuperare la risposta dal backend.";
    try {
      const error = (await res.json()) as { detail?: string };
      if (error.detail) detail = error.detail;
    } catch {
      // Keep the generic message when the backend response is not JSON.
    }
    throw new Error(detail);
  }

  return res.json() as Promise<ChatResponse>;
}

export async function fetchEvents(filters?: Partial<EventFilters>): Promise<RagledEvent[]> {
  if (!API_BASE_URL) {
    await wait(350);
    return mockEvents;
  }

  const params = new URLSearchParams();
  if (filters?.dateFrom) params.set("dateFrom", filters.dateFrom);
  if (filters?.dateTo) params.set("dateTo", filters.dateTo);
  if (filters?.country) params.set("country", filters.country);
  filters?.categories?.forEach((category) => params.append("category", category));

  const res = await fetch(`${API_BASE_URL}/api/events?${params.toString()}`);
  if (!res.ok) {
    throw new Error("Impossibile caricare gli eventi geografici.");
  }

  return res.json() as Promise<RagledEvent[]>;
}
