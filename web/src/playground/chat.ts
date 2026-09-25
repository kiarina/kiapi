import { apiFetch, postJson } from "../api";

export type ContentPart =
  | { type: "text"; text: string }
  | { type: "image_url"; image_url: { url: string } }
  | { type: "video_url"; video_url: { url: string } }
  | { type: "input_audio"; input_audio: { data: string; format: string } };

export interface ToolCall {
  id: string;
  type: "function";
  function: { name: string; arguments: string };
}

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string | ContentPart[] | null;
  tool_calls?: ToolCall[];
  tool_call_id?: string;
}

export interface Usage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  prompt_tokens_details?: { cached_tokens?: number };
}

export interface ChatResult {
  text: string;
  toolCalls: ToolCall[];
  finishReason: string | null;
  usage?: Usage;
  seconds: number;
}

export const DEFAULT_CHAT_MODEL = "qwen3.8-27b";

export interface ChatHandlers {
  onText?: (piece: string) => void;
  onToolCalls?: (calls: ToolCall[]) => void;
}

type Body = { model: string; messages: ChatMessage[]; [k: string]: unknown };

// Streams an OpenAI-style chat completion. Tool-call pieces arrive by index and are merged.
export async function streamChat(body: Body, handlers: ChatHandlers, signal?: AbortSignal): Promise<ChatResult> {
  const started = performance.now();
  const res = await apiFetch("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ ...body, stream: true, stream_options: { include_usage: true } }),
    signal,
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  const result: ChatResult = { text: "", toolCalls: [], finishReason: null, seconds: 0 };
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const data = line.startsWith("data:") ? line.slice(5).trim() : "";
      if (!data || data === "[DONE]") continue;
      const chunk = JSON.parse(data);
      if (chunk.error) throw new Error(chunk.error.message ?? String(chunk.error));
      if (chunk.usage) result.usage = chunk.usage;
      const choice = chunk.choices?.[0];
      if (!choice) continue;
      if (choice.finish_reason) result.finishReason = choice.finish_reason;
      const delta = choice.delta ?? {};
      if (typeof delta.content === "string" && delta.content) {
        result.text += delta.content;
        handlers.onText?.(delta.content);
      }
      for (const piece of delta.tool_calls ?? []) {
        const i = piece.index ?? result.toolCalls.length;
        const cur = result.toolCalls[i] ?? { id: "", type: "function", function: { name: "", arguments: "" } };
        result.toolCalls[i] = {
          id: piece.id ?? cur.id,
          type: "function",
          function: {
            name: cur.function.name + (piece.function?.name ?? ""),
            arguments: cur.function.arguments + (piece.function?.arguments ?? ""),
          },
        };
        handlers.onToolCalls?.([...result.toolCalls]);
      }
    }
  }
  result.seconds = (performance.now() - started) / 1000;
  return result;
}

interface Completion {
  choices: { message: { content: string | null; tool_calls?: ToolCall[] | null }; finish_reason: string | null }[];
  usage?: Usage;
  timings?: { total_s?: number };
}

export async function completeChat(body: Body): Promise<ChatResult> {
  const started = performance.now();
  const res = await postJson<Completion>("/v1/chat/completions", { ...body, stream: false });
  const choice = res.choices[0];
  return {
    text: choice?.message.content ?? "",
    toolCalls: choice?.message.tool_calls ?? [],
    finishReason: choice?.finish_reason ?? null,
    usage: res.usage,
    seconds: res.timings?.total_s ?? (performance.now() - started) / 1000,
  };
}

export function fileToDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

export async function attachmentPart(file: File): Promise<ContentPart> {
  const url = await fileToDataUrl(file);
  if (file.type.startsWith("video/")) return { type: "video_url", video_url: { url } };
  if (file.type.startsWith("audio/")) {
    return {
      type: "input_audio",
      input_audio: { data: url.split(",")[1] ?? "", format: file.type.split("/")[1]?.replace("x-", "") || "wav" },
    };
  }
  return { type: "image_url", image_url: { url } };
}
