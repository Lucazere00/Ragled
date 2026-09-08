"use client";

import Navbar from "@/components/Navbar";
import SearchAnswerCard from "@/components/SearchAnswerCard";

export default function Home() {
  return (
    <main className="min-h-screen bg-coal text-slate-100">
      <Navbar />
      <SearchAnswerCard />
    </main>
  );
}
