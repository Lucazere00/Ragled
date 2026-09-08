import type { AskResponse, ChartData } from "@/types/api";

export type { ChartData };

export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  chart?: ChartData;
  response?: AskResponse;
  createdAt: string;
};

export type RagledEvent = {
  id: string;
  title: string;
  date: string;
  country: string;
  place: string;
  category: string;
  lat: number;
  lng: number;
  description: string;
  intensity?: number;
};

export type EventFilters = {
  dateFrom: string;
  dateTo: string;
  country: string;
  categories: string[];
};

export type ChatResponse = AskResponse;
