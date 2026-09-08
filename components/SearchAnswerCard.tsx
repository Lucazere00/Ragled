"use client";

import { FormEvent, useState } from "react";
import { Copy, Search, Send } from "lucide-react";
import AnswerRenderer from "@/components/AnswerRenderer";
import { sendChatMessage } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

const suggestions = ["Eventi in Francia", "Emissioni CO2", "Inflazione 2024"];
const initialQuestion = "Qual è stato il PIL dell'Italia negli ultimi 5 anni?";

export default function SearchAnswerCard() {
  const [draft, setDraft] = useState(initialQuestion);
  const [question, setQuestion] = useState(initialQuestion);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse>({
    type: "hybrid",
    answer: "Il PIL italiano ha mostrato una crescita costante dal 2021 al 2025, con un'accelerazione negli ultimi due anni trainata da export e investimenti.",
    explanation: "I valori rappresentano la variazione percentuale annua del PIL italiano nel periodo 2021-2025.",
    chart: {
      chartType: "bar",
      labels: ["2021", "2022", "2023", "2024", "2025"],
      series: [{ name: "PIL", values: [100, 104, 108, 107, 112] }]
    }
  });

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

  const copyAnswer = async () => {
    await navigator.clipboard?.writeText(`${question}\n\n${response.answer}`);
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
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => { setDraft(suggestion); void submit(undefined, suggestion); }}
              className="rounded-lg border border-line px-3 py-1.5 text-sm text-slate-300 hover:border-signal/60 hover:text-slate-100"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>

      <article className="mt-10 border-t border-line pt-6">
        <p className="text-sm text-slate-400">Domanda</p>
        <p className="mt-1 text-base text-slate-100">{question}</p>
        <div className="mt-5 max-w-4xl">
          <AnswerRenderer response={response} isLoading={isLoading} error={error} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <a href="/mappa" className="rounded-lg border border-line px-4 py-2 text-sm text-slate-200 hover:bg-white/5">Vedi sulla mappa</a>
          <button type="button" onClick={copyAnswer} className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm text-slate-200 hover:bg-white/5">
            <Copy className="h-4 w-4" />
            Copia
          </button>
        </div>
      </article>
    </section>
  );
}