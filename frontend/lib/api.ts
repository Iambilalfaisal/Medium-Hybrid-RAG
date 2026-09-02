import type {
  ChatMessage,
  ChatSSEEvent,
  EvalRunResult,
  FilterOptions,
  FilterParams,
  IngestionRunStarted,
  IngestionStats,
  IngestionStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export function getIngestionStatus() {
  return getJSON<IngestionStatus>("/ingestion/status");
}

export function getIngestionStats() {
  return getJSON<IngestionStats>("/ingestion/stats");
}

export async function startIngestion(forceRescrape: boolean): Promise<IngestionRunStarted> {
  const res = await fetch(`${API_BASE}/ingestion/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ force_rescrape: forceRescrape }),
  });
  if (!res.ok) throw new Error(`ingestion/run failed: ${res.status}`);
  return res.json();
}

export function getFilterOptions() {
  return getJSON<FilterOptions>("/filters/options");
}

export function getEvalResults() {
  return getJSON<EvalRunResult[]>("/eval/results");
}

export async function triggerEvalRun(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/eval/run`, { method: "POST" });
  if (!res.ok) throw new Error(`eval/run failed: ${res.status}`);
  return res.json();
}

/**
 * SSE consumer for POST /chat. Native EventSource only supports GET, so the
 * text/event-stream body is parsed manually off a fetch() ReadableStream instead.
 */
async function* streamChat(
  messages: ChatMessage[],
  filters: FilterParams | null,
  topK: number,
  signal?: AbortSignal,
): AsyncGenerator<ChatSSEEvent> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, filters, top_k: topK }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`chat failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let eventName = "message";
      let dataLine = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLine = line.slice(5).trim();
      }
      if (!dataLine) continue;
      yield { event: eventName, data: JSON.parse(dataLine) } as ChatSSEEvent;
    }
  }
}

/**
 * Wraps streamChat with reconnect-with-backoff: a network blip mid-stream restarts
 * the FULL request (no server-side session for true resume in v1) up to maxRetries
 * times before surfacing an error event. onReconnecting lets the UI show a
 * "Reconnecting..." state between attempts.
 */
export async function* streamChatWithReconnect(
  messages: ChatMessage[],
  filters: FilterParams | null,
  topK: number,
  onReconnecting?: (attempt: number) => void,
): AsyncGenerator<ChatSSEEvent> {
  const maxRetries = 2;
  let attempt = 0;

  while (true) {
    try {
      for await (const event of streamChat(messages, filters, topK)) {
        yield event;
        if (event.event === "done" || event.event === "abstain") return;
      }
      return;
    } catch {
      attempt += 1;
      if (attempt > maxRetries) {
        yield { event: "error", data: { message: `Connection lost after ${maxRetries} retries.` } };
        return;
      }
      onReconnecting?.(attempt);
      await new Promise((resolve) => setTimeout(resolve, 500 * 2 ** attempt));
    }
  }
}
