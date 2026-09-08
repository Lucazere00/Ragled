import { Info } from "lucide-react";

export default function ExplanationCallout({ explanation }: { explanation: string }) {
  return (
    <aside className="flex gap-3 rounded-lg border border-signal/25 bg-panel px-4 py-3 text-sm leading-6 text-slate-300">
      <Info className="mt-1 h-4 w-4 shrink-0 text-signal" aria-hidden="true" />
      <p>{explanation}</p>
    </aside>
  );
}
