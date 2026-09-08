import Navbar from "@/components/Navbar";

export default function InfoPage() {
  return (
    <main className="min-h-screen bg-coal text-slate-100">
      <Navbar />
      <section className="mx-auto max-w-3xl px-5 py-12 sm:px-8">
        <p className="text-sm uppercase tracking-[0.08em] text-signal">Ragled</p>
        <h1 className="mt-3 text-3xl font-semibold">Esplora dati, luoghi e tempo.</h1>
        <p className="mt-5 max-w-2xl leading-7 text-slate-300">
          Un&apos;interfaccia per interrogare dati strutturati e osservare gli eventi sul globo in modo sintetico.
        </p>
      </section>
    </main>
  );
}
