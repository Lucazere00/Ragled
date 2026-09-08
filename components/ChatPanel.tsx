"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { CornerDownLeft, Loader2, Send, X } from "lucide-react";
import AnswerRenderer from "@/components/AnswerRenderer";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage, RagledEvent } from "@/lib/types";

type Props = {
  contextEvent?: RagledEvent;
  onContextConsumed?: () => void;
};

const initialMessages: ChatMessage[] = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Ciao, sono Ragled. Fai una domanda sugli eventi, chiedi una timeline o una distribuzione per categoria per vedere anche i grafici inline.",
    createdAt: new Date().toISOString()
  }
];

export default function ChatPanel({ contextEvent, onContextConsumed }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const promptPlaceholder = useMemo(() => {
    if (contextEvent) return `Chiedi di ${contextEvent.title}...`;
    return "Scrivi una domanda, poi premi Enter...";
  }, [contextEvent]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || isTyping) return;

    const context = contextEvent;
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: new Date().toISOString()
    };

    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setError(null);
    setIsTyping(true);
    onContextConsumed?.();

    try {
      const response = await sendChatMessage(text, context);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          response,
          createdAt: new Date().toISOString()
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore inatteso durante la richiesta.");
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="grid h-[calc(100vh-128px)] min-h-[620px] grid-rows-[1fr_auto] overflow-hidden rounded-lg border border-line bg-panel shadow-glow">
      <div className="overflow-y-auto px-4 py-5 sm:px-6">
        <div className="mx-auto flex max-w-4xl flex-col gap-4">
          {messages.map((message) => (
            <article
              key={message.id}
              className={`max-w-[92%] rounded-lg border px-4 py-3 ${
                message.role === "user"
                  ? "ml-auto border-signal/30 bg-signal text-ink"
                  : "mr-auto border-line bg-coal text-slate-100"
              }`}
            >
              <p className="whitespace-pre-wrap text-sm leading-6">{message.content}</p>
              {message.response ? <AnswerRenderer response={message.response} /> : null}
            </article>
          ))}

          {isTyping ? (
            <div className="mr-auto flex items-center gap-2 rounded-lg border border-line bg-coal px-4 py-3 text-sm text-slate-300">
              <Loader2 className="h-4 w-4 animate-spin text-signal" />
              Sta scrivendo...
            </div>
          ) : null}

          {error ? (
            <div className="rounded-lg border border-red-400/30 bg-red-950/40 px-4 py-3 text-sm text-red-100">{error}</div>
          ) : null}
          <div ref={bottomRef} />
        </div>
      </div>

      <form onSubmit={submit} className="border-t border-line bg-coal/80 p-3 sm:p-4">
        <div className="mx-auto max-w-4xl">
          {contextEvent ? (
            <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-amber/40 bg-amber/10 px-3 py-2 text-sm text-amber">
              <span className="min-w-0 truncate">
                Contesto attivo: {contextEvent.title} - {contextEvent.place}
              </span>
              <button type="button" onClick={onContextConsumed} className="rounded-md p-1 hover:bg-white/10" aria-label="Rimuovi contesto">
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : null}
          <div className="flex items-end gap-2">
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void submit();
                }
              }}
              rows={1}
              placeholder={promptPlaceholder}
              className="max-h-40 min-h-12 flex-1 resize-none rounded-lg border border-line bg-panel px-4 py-3 text-sm text-slate-100 outline-none ring-signal/30 placeholder:text-slate-500 focus:ring-4"
            />
            <button
              type="submit"
              disabled={!draft.trim() || isTyping}
              className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-signal text-ink transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Invia messaggio"
              title="Invia"
            >
              {isTyping ? <CornerDownLeft className="h-5 w-5" /> : <Send className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
