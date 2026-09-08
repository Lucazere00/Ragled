import type { RagledEvent } from "@/lib/types";
import type { AskResponse } from "@/types/api";

export const mockEvents: RagledEvent[] = [
  {
    id: "evt-001",
    title: "Diplomatic statement in Tehran",
    date: "2024-04-13",
    country: "Iran",
    region: "Middle East",
    place: "Tehran",
    category: "Diplomacy",
    disorderType: "Political developments",
    subEventType: "Diplomatic statement",
    fatalities: 2,
    lat: 35.6892,
    lng: 51.389,
    description: "Official statements raised regional attention after a sequence of security incidents.",
    intensity: 68
  },
  {
    id: "evt-002",
    title: "Maritime alert near Strait of Hormuz",
    date: "2024-05-08",
    country: "Iran",
    region: "Middle East",
    place: "Strait of Hormuz",
    category: "Security",
    disorderType: "Political violence",
    subEventType: "Maritime incident",
    fatalities: 6,
    lat: 26.5667,
    lng: 56.25,
    description: "Commercial traffic monitoring increased after reported naval activity in the area.",
    intensity: 81
  },
  {
    id: "evt-003",
    title: "Energy market briefing in Washington",
    date: "2024-06-21",
    country: "United States",
    region: "North America",
    place: "Washington, DC",
    category: "Economy",
    disorderType: "Political developments",
    subEventType: "Economic activity",
    fatalities: 0,
    lat: 38.9072,
    lng: -77.0369,
    description: "Analysts compared regional risk signals with crude oil volatility and shipping routes.",
    intensity: 43
  },
  {
    id: "evt-004",
    title: "UN consultation on regional stability",
    date: "2024-07-18",
    country: "United States",
    region: "North America",
    place: "New York",
    category: "Diplomacy",
    disorderType: "Political developments",
    subEventType: "Consultation",
    fatalities: 0,
    lat: 40.7128,
    lng: -74.006,
    description: "Representatives discussed de-escalation channels and humanitarian monitoring.",
    intensity: 52
  },
  {
    id: "evt-005",
    title: "Border incident report",
    date: "2024-08-02",
    country: "Iraq",
    region: "Middle East",
    place: "Erbil",
    category: "Security",
    disorderType: "Political violence",
    subEventType: "Border incident",
    fatalities: 4,
    lat: 36.1911,
    lng: 44.0094,
    description: "Local sources reported a security event with cross-border diplomatic implications.",
    intensity: 74
  },
  {
    id: "evt-006",
    title: "Humanitarian corridor assessment",
    date: "2024-09-10",
    country: "Syria",
    region: "Middle East",
    place: "Damascus",
    category: "Humanitarian",
    disorderType: "Political violence",
    subEventType: "Humanitarian access",
    fatalities: 1,
    lat: 33.5138,
    lng: 36.2765,
    description: "Field reports mapped access constraints and changes in displacement patterns.",
    intensity: 37
  }
];

export const mockTextResponse: AskResponse = {
  type: "text",
  answer: "La diplomazia e la sicurezza regionale sono i temi piu ricorrenti nelle fonti consultate."
};

export const mockStructuredResponse: AskResponse = {
  type: "structured",
  answer: "Risultati numerici trovati per il periodo selezionato.",
  explanation: "La tabella riporta il numero di eventi osservati per mese nel 2024. Il picco di maggio indica una concentrazione temporale superiore alla media del periodo.",
  table: {
    columns: ["Mese", "Eventi", "Intensita media"],
    rows: [["Aprile", 2, 55], ["Maggio", 6, 78], ["Giugno", 4, 61], ["Luglio", 3, 49]]
  },
  chart: {
    chartType: "bar",
    labels: ["Aprile", "Maggio", "Giugno", "Luglio"],
    series: [{ name: "Eventi", values: [2, 6, 4, 3] }]
  }
};

export const mockHybridResponse: AskResponse = {
  type: "hybrid",
  answer: "La crescita del PIL e stata sostenuta soprattutto dal miglioramento degli investimenti e delle esportazioni.",
  explanation: "I valori sono variazioni percentuali annue, riferite al periodo 2021-2025. Il rallentamento del 2024 e seguito da una ripresa nel 2025.",
  table: {
    columns: ["Anno", "Crescita PIL (%)"],
    rows: [[2021, 6.7], [2022, 4.0], [2023, 0.9], [2024, 0.7], [2025, 1.2]]
  },
  chart: {
    chartType: "line",
    labels: ["2021", "2022", "2023", "2024", "2025"],
    series: [{ name: "Crescita PIL (%)", values: [6.7, 4.0, 0.9, 0.7, 1.2] }]
  }
};

export const mockChatResponse = (question: string): AskResponse => {
  const normalized = question.toLowerCase();

  if (normalized.includes("pil") || normalized.includes("crescita")) return mockHybridResponse;
  if (normalized.includes("timeline") || normalized.includes("tempo") || normalized.includes("serie") || normalized.includes("categoria")) return mockStructuredResponse;
  return mockTextResponse;
};
