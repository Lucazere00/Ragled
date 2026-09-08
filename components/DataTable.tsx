"use client";

import { ArrowDown, ArrowUp, Download } from "lucide-react";
import { useMemo, useState } from "react";
import type { TableData } from "@/types/api";

type SortState = { column: number; direction: "asc" | "desc" };

function compareValues(left: string | number, right: string | number) {
  if (typeof left === "number" && typeof right === "number") return left - right;
  return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
}

function csvValue(value: string | number) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export default function DataTable({ table }: { table: TableData }) {
  const [sort, setSort] = useState<SortState | null>(null);
  const rows = useMemo(() => {
    if (!sort) return table.rows;
    return [...table.rows].sort((left, right) => compareValues(left[sort.column] ?? "", right[sort.column] ?? "") * (sort.direction === "asc" ? 1 : -1));
  }, [sort, table.rows]);

  const toggleSort = (column: number) => {
    setSort((current) => current?.column === column
      ? { column, direction: current.direction === "asc" ? "desc" : "asc" }
      : { column, direction: "asc" });
  };

  const exportCsv = () => {
    const content = [table.columns, ...table.rows].map((row) => row.map(csvValue).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "ragled-data.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-lg border border-line bg-coal/70">
      <div className="flex items-center justify-end border-b border-line px-4 py-3">
        <button type="button" onClick={exportCsv} className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm text-slate-200 hover:bg-white/5">
          <Download className="h-4 w-4" aria-hidden="true" />
          Esporta CSV
        </button>
      </div>
      <div className="max-h-[28rem] overflow-auto">
        <table className="min-w-full border-collapse text-sm">
          <thead className="sticky top-0 z-10 bg-panel text-left text-slate-300">
            <tr>{table.columns.map((column, index) => (
              <th key={column} scope="col" className="whitespace-nowrap border-b border-line px-4 py-3 font-medium">
                <button type="button" onClick={() => toggleSort(index)} className="inline-flex items-center gap-2 hover:text-slate-100">
                  {column}
                  {sort?.column === index ? (sort.direction === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />) : null}
                </button>
              </th>
            ))}</tr>
          </thead>
          <tbody>{rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-line/70 last:border-0">
              {table.columns.map((column, columnIndex) => {
                const value = row[columnIndex] ?? "";
                return <td key={`${column}-${columnIndex}`} className={`whitespace-nowrap px-4 py-3 text-slate-200 ${typeof value === "number" ? "text-right tabular-nums" : "text-left"}`}>{value}</td>;
              })}
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}