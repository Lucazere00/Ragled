"use client";

import { RotateCcw } from "lucide-react";
import type { EventFilters, RagledEvent } from "@/lib/types";

type Props = {
  events: RagledEvent[];
  filters: EventFilters;
  onChange: (filters: EventFilters) => void;
  resultCount: number;
};

export default function FilterSidebar({ events, filters, onChange, resultCount }: Props) {
  const countries = Array.from(new Set(events.map((event) => event.country))).sort();
  const categories = Array.from(new Set(events.map((event) => event.category))).sort();
  const years = events.map((event) => Number(event.date.slice(0, 4)));
  const minYear = years.length ? Math.min(...years) : new Date().getFullYear();
  const maxYear = years.length ? Math.max(...years) : minYear;
  const fromYear = filters.dateFrom ? Number(filters.dateFrom.slice(0, 4)) : minYear;
  const toYear = filters.dateTo ? Number(filters.dateTo.slice(0, 4)) : maxYear;

  const updateCategory = (category: string) => {
    const exists = filters.categories.includes(category);
    onChange({
      ...filters,
      categories: exists ? filters.categories.filter((item) => item !== category) : [...filters.categories, category]
    });
  };

  const reset = () => {
    onChange({ dateFrom: "", dateTo: "", country: "", categories: [] });
  };

  return (
    <aside className="w-full border-b border-line bg-panel p-4 lg:w-80 lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Filtri</h2>
        <button
          type="button"
          onClick={reset}
          className="rounded-md border border-line p-2 text-slate-300 hover:bg-white/5"
          aria-label="Reset filtri"
          title="Reset filtri"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5 grid gap-4">
        <div className="grid gap-3 text-sm text-slate-300">
          <div className="flex items-center justify-between">
            <span>Intervallo date</span>
            <span className="text-slate-500">{fromYear} - {toYear}</span>
          </div>
          <label className="grid gap-1 text-xs text-slate-500">
            Da {fromYear}
            <input
              type="range"
              min={minYear}
              max={maxYear}
              value={fromYear}
              onChange={(event) => onChange({ ...filters, dateFrom: `${event.target.value}-01-01` })}
              className="accent-signal"
              aria-label="Anno iniziale"
            />
          </label>
          <label className="grid gap-1 text-xs text-slate-500">
            A {toYear}
            <input
              type="range"
              min={minYear}
              max={maxYear}
              value={toYear}
              onChange={(event) => onChange({ ...filters, dateTo: `${event.target.value}-12-31` })}
              className="accent-signal"
              aria-label="Anno finale"
            />
          </label>
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Paese
          <select
              value={filters.country}
              onChange={(event) => onChange({ ...filters, country: event.target.value })}
              className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4"
            >
              <option value="">Tutti i paesi</option>
              {countries.map((country) => (
                <option key={country} value={country} />
              ))}
            </select>
        </label>

        <div className="grid gap-2">
          <span className="text-sm text-slate-300">Categorie</span>
          <div className="grid gap-2">
            {categories.map((category) => (
              <label key={category} className="flex items-center gap-3 rounded-lg border border-line bg-coal px-3 py-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={filters.categories.includes(category)}
                  onChange={() => updateCategory(category)}
                  className="h-4 w-4 accent-signal"
                />
                <span className={`h-2.5 w-2.5 rounded-full ${category === "Security" ? "bg-amber" : "bg-signal"}`} />
                {category}
              </label>
            ))}
          </div>
        </div>
      </div>
      <p className="mt-6 border-t border-line pt-4 text-sm text-slate-400">
        <span className="font-medium text-slate-100">{resultCount}</span> risultati
      </p>
    </aside>
  );
}
