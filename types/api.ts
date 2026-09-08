export type ResponseType = "text" | "semantic" | "structured" | "hybrid";

export interface TableData {
  columns: string[];
  rows: (string | number)[][];
}

export interface ChartData {
  chartType: "bar" | "line" | "pie" | "scatter";
  labels: string[];
  series: { name: string; values: number[] }[];
  highlightedLabel?: string;
}

export interface GraphData {
  nodes: { id: string; label: string; group?: string }[];
  edges: { source: string; target: string; label?: string }[];
}

export interface AskResponse {
  type: ResponseType;
  answer: string;
  explanation?: string;
  table?: TableData;
  chart?: ChartData;
  chart_message?: string;
  graph?: GraphData;
  sources?: string[];
}
