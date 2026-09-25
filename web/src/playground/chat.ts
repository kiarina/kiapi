import { apiFetch } from "../api";

export type ContentPart =
  | { type: "text"; text: string }
  | { type: "image_url"; image_url: { url: string } }
  | { type: "video_url"; video_url: { url: string } }
  | { type: "input_audio"; input_audio: { data: string; format: string } };

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string | ContentPart[];
}

export const DEFAULT_CHAT_MODEL = "qwen3.8-27b";

// Streams an OpenAI-style chat completion, calling `onDelta` with each text piece.
export async function streamChat(
  body: { model: string; messages: ChatMessage[]; [k: string]: unknown },
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await apiFetch("/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ ...body, stream: true }),
    signal,
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
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
      const delta = chunk.choices?.[0]?.delta?.content;
      if (typeof delta === "string" && delta) onDelta(delta);
    }
  }
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
