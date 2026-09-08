"use client";

import { useState } from "react";
import Navbar from "@/components/Navbar";
import GlobePanel from "@/components/GlobePanel";
import type { RagledEvent } from "@/lib/types";

export default function MapPage() {
  const [, setSelectedEvent] = useState<RagledEvent | null>(null);

  return (
    <main className="min-h-screen bg-coal text-slate-100">
      <Navbar />
      <section className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <GlobePanel onAskMore={setSelectedEvent} />
      </section>
    </main>
  );
}