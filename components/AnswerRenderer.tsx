"use client";

import { AlertCircle, BarChart3, Table2 } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";
import type { AskResponse } from "@/types/api";
import ChartRenderer from "@/components/ChartRenderer";
import DataTable from "@/components/DataTable";
import ExplanationCallout from "@/components/ExplanationCallout";

const GraphRenderer = dynamic(() => import("@/components/GraphRenderer"), { ssr: false });

type Props = { response?: AskResponse; isLoading?: boolean; error?: string | null };

export default function AnswerRenderer({ response, isLoading = false, error = null }: Props) {
  const [view, setView] = useState<"table" | "chart">("table");

  if (isLoading) return <p className="text-base leading-7 text-slate-300">Sto elaborando la domanda...</p>;
  if (error) return <div className="flex items-start gap-2 rounded-lg border border-amber/40 bg-amber/10 px-4 py-3 text-sm text-amber"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>;
  if (!response) return null;

  const showExplanation = response.type === "structured" || response.type === "hybrid";
  const showAnswer = Boolean(response.answer?.trim());

  return (
    <div className="space-y-4">
      {showAnswer ? <p className="whitespace-pre-wrap text-base leading-7 text-slate-200">{response.answer}</p> : null}
      {showExplanation && response.explanation ? <ExplanationCallout explanation={response.explanation} /> : null}
      {response.chart_message ? <p className="text-sm text-slate-400">{response.chart_message}</p> : null}
      {response.table && response.chart ? (
        <div className="space-y-3">
          <div className="inline-flex rounded-lg border border-line bg-panel p-1" role="tablist" aria-label="Visualizzazione dati">
            <button type="button" role="tab" aria-selected={view === "table"} onClick={() => setView("table")} className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ${view === "table" ? "bg-signal text-ink" : "text-slate-300 hover:text-slate-100"}`}><Table2 className="h-4 w-4" />Tabella</button>
            <button type="button" role="tab" aria-selected={view === "chart"} onClick={() => setView("chart")} className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ${view === "chart" ? "bg-signal text-ink" : "text-slate-300 hover:text-slate-100"}`}><BarChart3 className="h-4 w-4" />Grafico</button>
          </div>
          {view === "table" ? <DataTable table={response.table} /> : <ChartRenderer chart={response.chart} />}
        </div>
      ) : response.table ? <DataTable table={response.table} /> : response.chart ? <ChartRenderer chart={response.chart} /> : null}
      {response.graph ? <GraphRenderer graph={response.graph} /> : null}
    </div>
  );
}