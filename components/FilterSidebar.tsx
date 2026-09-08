"use client";

import { RotateCcw } from "lucide-react";
import type { EventFilterOptions, EventFilters, RagledEvent } from "@/lib/types";

type Props = {
  events: RagledEvent[];
  filterOptions: EventFilterOptions | null;
  filters: EventFilters;
  onChange: (filters: EventFilters) => void;
  resultCount: number;
};

export default function FilterSidebar({ events, filterOptions, filters, onChange, resultCount }: Props) {
  const countries = filterOptions?.countries ?? [];
  const regions = filterOptions?.regions ?? [];
  const eventTypes = filterOptions?.eventTypes ?? [];
  const disorderTypes = filterOptions?.disorderTypes ?? [];
  const subEventTypes = filters.eventType
    ? filterOptions?.subEventTypesByEventType[filters.eventType] ?? []
    : filterOptions?.subEventTypes ?? [];
  const years = filterOptions?.years ?? [];
  const minYear = years.length ? Math.min(...years) : new Date().getFullYear();
  const maxYear = years.length ? Math.max(...years) : minYear;
  const fromYear = filters.dateFrom ? Number(filters.dateFrom.slice(0, 4)) : minYear;
  const toYear = filters.dateTo ? Number(filters.dateTo.slice(0, 4)) : maxYear;
  const optionsLoading = !filterOptions;

  const reset = () => {
    onChange({
      dateFrom: "",
      dateTo: "",
      country: "",
      region: "",
      eventType: "",
      disorderType: "",
      subEventType: "",
      fatalitiesMin: "",
      fatalitiesMax: "",
      categories: []
    });
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
            Da
            <select
              value={filters.dateFrom ? fromYear : ""}
              disabled={optionsLoading}
              onChange={(event) => onChange({ ...filters, dateFrom: event.target.value ? `${event.target.value}-01-01` : "" })}
              className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-sm text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60"
              aria-label="Anno iniziale"
            >
              <option value="">Primo anno</option>
              {years.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-xs text-slate-500">
            A
            <select
              value={filters.dateTo ? toYear : ""}
              disabled={optionsLoading}
              onChange={(event) => onChange({ ...filters, dateTo: event.target.value ? `${event.target.value}-12-31` : "" })}
              className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-sm text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60"
              aria-label="Anno finale"
            >
              <option value="">Ultimo anno</option>
              {years.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
        </div>

        <label className="grid gap-2 text-sm text-slate-300">
          Paese
          <select
            value={filters.country}
            disabled={optionsLoading}
            onChange={(event) => onChange({ ...filters, country: event.target.value })}
            className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4"
          >
            <option value="">Seleziona un paese</option>
            {countries.map((country) => <option key={country} value={country}>{country}</option>)}
          </select>
        </label>

        <label className="grid gap-2 text-sm text-slate-300">
          Regione
          <select value={filters.region} disabled={optionsLoading} onChange={(event) => onChange({ ...filters, region: event.target.value })} className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60">
            <option value="">Seleziona una regione</option>
            {regions.map((region) => <option key={region} value={region}>{region}</option>)}
          </select>
        </label>

        <label className="grid gap-2 text-sm text-slate-300">
          Event type
          <select value={filters.eventType} disabled={optionsLoading} onChange={(event) => onChange({ ...filters, eventType: event.target.value, subEventType: "" })} className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60">
            <option value="">Seleziona un event type</option>
            {eventTypes.map((eventType) => <option key={eventType} value={eventType}>{eventType}</option>)}
          </select>
        </label>

        <label className="grid gap-2 text-sm text-slate-300">
          Disorder type
          <select value={filters.disorderType} disabled={optionsLoading} onChange={(event) => onChange({ ...filters, disorderType: event.target.value })} className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60">
            <option value="">Seleziona un disorder type</option>
            {disorderTypes.map((disorderType) => <option key={disorderType} value={disorderType}>{disorderType}</option>)}
          </select>
        </label>

        <label className="grid gap-2 text-sm text-slate-300">
          Sub event type
          <select value={filters.subEventType} disabled={optionsLoading} onChange={(event) => onChange({ ...filters, subEventType: event.target.value })} className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4 disabled:cursor-wait disabled:opacity-60">
            <option value="">Seleziona un sub event type</option>
            {subEventTypes.map((subEventType) => <option key={subEventType} value={subEventType}>{subEventType}</option>)}
          </select>
        </label>

        <div className="grid gap-2 text-sm text-slate-300">
          <span>Fatalities</span>
          <div className="grid grid-cols-2 gap-2">
            <input type="number" min="0" value={filters.fatalitiesMin} onChange={(event) => onChange({ ...filters, fatalitiesMin: event.target.value })} placeholder="Min" aria-label="Fatalities minime" className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4" />
            <input type="number" min="0" value={filters.fatalitiesMax} onChange={(event) => onChange({ ...filters, fatalitiesMax: event.target.value })} placeholder="Max" aria-label="Fatalities massime" className="w-full rounded-lg border border-line bg-coal px-3 py-2 text-slate-100 outline-none ring-signal/30 focus:ring-4" />
          </div>
        </div>
      </div>
      <p className="mt-6 border-t border-line pt-4 text-sm text-slate-400">
        <span className="font-medium text-slate-100">{resultCount}</span> risultati
      </p>
    </aside>
  );
}
