"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Home" },
  { href: "/mappa", label: "Mappa" },
  { href: "/info", label: "Info" }
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-line">
      <nav className="mx-auto flex h-[74px] w-full max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link href="/" className="text-lg font-medium text-slate-100">
          Ragled
        </Link>
        <div className="flex h-full items-center gap-6 sm:gap-8">
          {links.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex h-full items-center border-b-2 px-0.5 text-sm transition ${
                  active ? "border-signal text-slate-100" : "border-transparent text-slate-400 hover:text-slate-200"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </div>
        <button type="button" className="rounded-lg border border-line px-4 py-2 text-sm text-slate-200 hover:bg-white/5">
          Accedi
        </button>
      </nav>
    </header>
  );
}