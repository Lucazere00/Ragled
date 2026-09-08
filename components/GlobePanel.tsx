"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Loader2, MessageSquareMore, Minus, Plus, X } from "lucide-react";
import type { GlobeMethods } from "react-globe.gl";
import FilterSidebar from "@/components/FilterSidebar";
import { fetchEvents } from "@/lib/api";
import type { EventFilters, RagledEvent } from "@/lib/types";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

type Props = {
  onAskMore: (event: RagledEvent) => void;
};

const defaultFilters: EventFilters = {
  dateFrom: "",
  dateTo: "",
  country: "",
  categories: []
};

export default function GlobePanel({ onAskMore }: Props) {
  const [events, setEvents] = useState<RagledEvent[]>([]);
  const [filters, setFilters] = useState<EventFilters>(defaultFilters);
  const [selectedEvent, setSelectedEvent] = useState<RagledEvent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const globeRef = useRef<GlobeMethods>();

  useEffect(() => {
    let ignore = false;

    async function loadEvents() {
      setLoading(true);
      setError(null);

      try {
        const nextEvents = await fetchEvents();
        if (!ignore) setEvents(nextEvents);
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Errore inatteso nel caricamento degli eventi.");
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    void loadEvents();

    return () => {
      ignore = true;
    };
  }, []);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const eventDate = new Date(event.date).getTime();
      const from = filters.dateFrom ? new Date(filters.dateFrom).getTime() : undefined;
      const to = filters.dateTo ? new Date(filters.dateTo).getTime() : undefined;
      const countryMatch = filters.country ? event.country.toLowerCase().includes(filters.country.toLowerCase()) : true;
      const categoryMatch = filters.categories.length ? filters.categories.includes(event.category) : true;

      return (!from || eventDate >= from) && (!to || eventDate <= to) && countryMatch && categoryMatch;
    });
  }, [events, filters]);

  return (
    <div className="flex min-h-[620px] flex-col overflow-hidden rounded-lg border border-line bg-panel shadow-glow lg:h-[calc(100vh-128px)] lg:flex-row">
      <FilterSidebar events={events} filters={filters} onChange={setFilters} resultCount={filteredEvents.length} />

      <div className="relative min-h-[620px] flex-1 bg-ink">
        {loading ? (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-ink">
            <div className="flex items-center gap-3 rounded-lg border border-line bg-panel px-4 py-3 text-sm text-slate-200">
              <Loader2 className="h-4 w-4 animate-spin text-signal" />
              Caricamento eventi...
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="absolute left-4 right-4 top-4 z-20 flex items-center gap-3 rounded-lg border border-red-400/30 bg-red-950/70 px-4 py-3 text-sm text-red-100">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        ) : null}

        <Globe
          ref={globeRef}
          backgroundColor="#0f1720"
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-night.jpg"
          bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
          pointsData={filteredEvents}
          pointLat={(event: object) => (event as RagledEvent).lat}
          pointLng={(event: object) => (event as RagledEvent).lng}
          pointAltitude={(event: object) => Math.max(((event as RagledEvent).intensity ?? 35) / 450, 0.06)}
          pointRadius={0.45}
          pointColor={(event: object) => {
            const category = (event as RagledEvent).category;
            if (category === "Security") return "#f17878";
            if (category === "Diplomacy") return "#54d6a8";
            if (category === "Economy") return "#f4bd50";
            return "#6ea8fe";
          }}
          pointLabel={(event: object) => {
            const item = event as RagledEvent;
            return `${item.title}<br/>${item.place} - ${item.date}`;
          }}
          onPointClick={(event: object) => setSelectedEvent(event as RagledEvent)}
        />

        <div className="absolute right-4 top-4 z-10 flex flex-col overflow-hidden rounded-lg border border-line bg-panel/90">
          <button
            type="button"
            onClick={() => globeRef.current?.pointOfView({ altitude: 1.4 })}
            className="p-2 text-slate-200 hover:bg-white/5"
            aria-label="Ingrandisci mappa"
            title="Ingrandisci"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => globeRef.current?.pointOfView({ altitude: 2.8 })}
            className="border-t border-line p-2 text-slate-200 hover:bg-white/5"
            aria-label="Riduci mappa"
            title="Riduci"
          >
            <Minus className="h-4 w-4" />
          </button>
        </div>

        <div className="absolute left-4 top-4 z-10 rounded-lg border border-line bg-panel/90 px-4 py-3 backdrop-blur">
          <p className="text-xs uppercase tracking-wide text-slate-400">Eventi visibili</p>
          <p className="mt-1 text-2xl font-semibold text-white">{filteredEvents.length}</p>
        </div>

        {selectedEvent ? (
          <div className="absolute bottom-4 left-4 right-4 z-20 max-w-xl rounded-lg border border-line bg-panel/95 p-4 shadow-glow backdrop-blur">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-signal">{selectedEvent.category}</p>
                <h2 className="mt-1 text-lg font-semibold text-white">{selectedEvent.title}</h2>
              </div>
              <button
                type="button"
                onClick={() => setSelectedEvent(null)}
                className="rounded-md p-2 text-slate-300 hover:bg-white/5"
                aria-label="Chiudi dettagli evento"
                title="Chiudi"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <dl className="mt-3 grid gap-2 text-sm text-slate-300 sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Data</dt>
                <dd>{selectedEvent.date}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Luogo</dt>
                <dd>
                  {selectedEvent.place}, {selectedEvent.country}
                </dd>
              </div>
            </dl>

            <p className="mt-3 text-sm leading-6 text-slate-300">{selectedEvent.description}</p>
            <button
              type="button"
              onClick={() => onAskMore(selectedEvent)}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-signal px-4 py-2 text-sm font-semibold text-ink hover:brightness-105"
            >
              <MessageSquareMore className="h-4 w-4" />
              Chiedi di piu
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
