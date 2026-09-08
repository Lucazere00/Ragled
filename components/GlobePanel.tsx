"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, Loader2, MessageSquareMore, Minus, Plus, X } from "lucide-react";
import type { GlobeMethods } from "react-globe.gl";
import FilterSidebar from "@/components/FilterSidebar";
import { fetchEventFilterOptions, fetchEvents } from "@/lib/api";
import type { EventFilterOptions, EventFilters, RagledEvent } from "@/lib/types";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

type Props = {
  onAskMore: (event: RagledEvent) => void;
};

const defaultFilters: EventFilters = {
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
};

export default function GlobePanel({ onAskMore }: Props) {
  const [events, setEvents] = useState<RagledEvent[]>([]);
  const [filterOptions, setFilterOptions] = useState<EventFilterOptions | null>(null);
  const [filters, setFilters] = useState<EventFilters>(defaultFilters);
  const [selectedEvent, setSelectedEvent] = useState<RagledEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [globeSize, setGlobeSize] = useState({ width: 0, height: 0 });
  const globeContainerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeMethods>();

  useEffect(() => {
    let ignore = false;
    void fetchEventFilterOptions()
      .then((options) => {
        if (!ignore) setFilterOptions(options);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof Error ? err.message : "Impossibile caricare le opzioni dei filtri.");
      });

    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    const container = globeContainerRef.current;
    if (!container) return;

    const measure = () => {
      const bounds = container.getBoundingClientRect();
      const nextSize = {
        width: Math.max(0, Math.floor(bounds.width)),
        height: Math.max(0, Math.floor(bounds.height))
      };

      // Temporary diagnostics: compare the parent viewport with the canvas size after layout.
      console.log("[GlobePanel] resize", {
        container: { width: bounds.width, height: bounds.height },
        canvas: nextSize
      });

      setGlobeSize((previousSize) => (
        previousSize.width === nextSize.width && previousSize.height === nextSize.height
          ? previousSize
          : nextSize
      ));
    };

    const observer = new ResizeObserver(measure);
    observer.observe(container);
    const frame = requestAnimationFrame(measure);

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!globeSize.width || !globeSize.height) return;

    const canvas = globeContainerRef.current?.querySelector("canvas");
    console.log("[GlobePanel] canvas updated", {
      container: globeContainerRef.current?.getBoundingClientRect(),
      canvas: canvas ? { width: canvas.clientWidth, height: canvas.clientHeight } : null
    });
  }, [globeSize]);

  useEffect(() => {
    let ignore = false;

    const hasActiveFilter = Object.entries(filters).some(([key, value]) => {
      if (key === "categories") return Array.isArray(value) && value.length > 0;
      return typeof value === "string" && value.length > 0;
    });

    // The initial map stays empty. Events are requested only after the user
    // chooses at least one filter, so opening the page does not load the dataset.
    if (!hasActiveFilter) {
      setEvents([]);
      setLoading(false);
      setError(null);
      return () => {
        ignore = true;
      };
    }

    const timeout = window.setTimeout(() => {
      void loadEvents();
    }, 350);

    async function loadEvents() {
      setLoading(true);
      setError(null);

      try {
        const nextEvents = await fetchEvents(filters);
        if (!ignore) setEvents(nextEvents);
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Errore inatteso nel caricamento degli eventi.");
      } finally {
        if (!ignore) setLoading(false);
      }
    }

    return () => {
      ignore = true;
      window.clearTimeout(timeout);
    };
  }, [filters]);

  const filteredEvents = useMemo(() => events, [events]);

  return (
    <div className="flex min-h-[620px] min-w-0 flex-col overflow-hidden rounded-lg border border-line bg-panel shadow-glow lg:h-[calc(100vh-128px)] lg:flex-row">
        <FilterSidebar
          events={events}
          filterOptions={filterOptions}
          filters={filters}
          onChange={setFilters}
          resultCount={filteredEvents.length}
        />

      <div ref={globeContainerRef} className="relative min-h-[620px] min-w-0 flex-1 overflow-hidden bg-ink">
        {loading ? (
          <div className="pointer-events-none absolute left-4 right-4 top-4 z-20 flex justify-center">
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

        {globeSize.width > 0 && globeSize.height > 0 ? (
          <Globe
            ref={globeRef}
            width={globeSize.width}
            height={globeSize.height}
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
            onGlobeReady={() => {
              globeRef.current?.pointOfView({ lat: 35, lng: -15, altitude: 2.2 }, 0);
              const canvas = globeContainerRef.current?.querySelector("canvas");
              console.log("[GlobePanel] initialized", {
                container: globeContainerRef.current?.getBoundingClientRect(),
                canvas: canvas ? { width: canvas.clientWidth, height: canvas.clientHeight } : null,
                camera: { lat: 0, lng: 0, altitude: 2.2 }
              });
            }}
            onPointClick={(event: object) => setSelectedEvent(event as RagledEvent)}
          />
        ) : null}

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

        {!loading && !error && filteredEvents.length === 0 ? (
          <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
            <p className="rounded-lg border border-line bg-panel/90 px-4 py-3 text-sm text-slate-300 shadow-glow">
              Seleziona almeno un filtro per visualizzare gli eventi
            </p>
          </div>
        ) : null}

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
