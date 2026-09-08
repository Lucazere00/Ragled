"use client";

import { FormEvent, useState } from "react";
import { Database, Search, Send } from "lucide-react";
import AnswerRenderer from "@/components/AnswerRenderer";
import { sendChatMessage } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

export default function SearchAnswerCard() {
  const [draft, setDraft] = useState("");
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);

  const submit = async (event?: FormEvent, value = draft) => {
    event?.preventDefault();
    const nextQuestion = value.trim();
    if (!nextQuestion || isLoading) return;
    setQuestion(nextQuestion);
    setIsLoading(true);
    setError(null);
    try {
      setResponse(await sendChatMessage(nextQuestion));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossibile elaborare la domanda.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="mx-auto w-full max-w-5xl px-5 pb-12 pt-10 sm:px-8 sm:pt-12">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-signal">Chiedi ai dati</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-100 sm:text-4xl">Cosa vuoi sapere?</h1>
        <form onSubmit={submit} className="mt-7 flex items-center gap-3 rounded-[12px] border border-line bg-panel p-3">
          <Search className="ml-2 h-5 w-5 shrink-0 text-slate-500" />
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-base text-slate-100 outline-none placeholder:text-slate-500"
            placeholder="Scrivi una domanda sui dati..."
            aria-label="Domanda"
          />
          <button type="submit" disabled={isLoading} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-signal text-ink hover:brightness-105 disabled:cursor-wait disabled:opacity-60" aria-label="Invia domanda" title="Invia">
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>

      {question ? (
        <article className="mt-10 border-t border-line pt-6">
          <p className="text-sm text-slate-400">Domanda</p>
          <p className="mt-1 text-base text-slate-100">{question}</p>
          <div className="mt-5 max-w-4xl">
            <AnswerRenderer response={response ?? undefined} isLoading={isLoading} error={error} />
          </div>
        </article>
      ) : (
        <div className="mx-auto mt-10 flex max-w-2xl items-start gap-4 border-t border-line pt-6 text-left">
          <Database className="mt-1 h-5 w-5 shrink-0 text-signal" aria-hidden="true" />
          <p className="text-sm leading-6 text-slate-400">
            Ragled esplora il dataset ACLED sui conflitti nel mondo, rendendolo interrogabile in linguaggio naturale. Fai una domanda qui sopra oppure esplora tutti gli eventi sulla mappa interattiva.
          </p>
        </div>
      )}
    </section>
  );
}