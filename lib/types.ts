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
  region: string;
  place: string;
  category: string;
  disorderType: string;
  subEventType: string;
  lat: number;
  lng: number;
  fatalities: number;
  description: string;
  intensity?: number;
};

export type EventFilters = {
  dateFrom: string;
  dateTo: string;
  country: string;
  region: string;
  eventType: string;
  disorderType: string;
  subEventType: string;
  fatalitiesMin: string;
  fatalitiesMax: string;
  categories: string[];
};

export type EventFilterOptions = {
  years: number[];
  countries: string[];
  regions: string[];
  eventTypes: string[];
  disorderTypes: string[];
  subEventTypes: string[];
  subEventTypesByEventType: Record<string, string[]>;
};

export type ChatResponse = AskResponse;
