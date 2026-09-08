"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis
} from "recharts";
import type { ChartData } from "@/types/api";

const colors = ["#54d6a8", "#f4bd50", "#6ea8fe", "#f17878", "#c084fc", "#8bd3dd"];

type Props = {
  chart: ChartData;
};

export default function ChartRenderer({ chart }: Props) {
  const chartType = chart.chartType;
  const data = chart.labels.map((label, index) => {
    const point: Record<string, string | number> = { label };
    chart.series.forEach((series) => { point[series.name] = series.values[index] ?? 0; });
    return point;
  });

  if (!data.length || !chart.series.length) {
    return null;
  }
  const showLegend = chart.series.length > 1;
  const chartMargins = { top: 8, right: 18, left: 0, bottom: 8 };

  return (
    <div className="rounded-lg border border-line bg-coal/70 p-4">
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === "line" ? (
            <LineChart data={data} margin={chartMargins}>
              <CartesianGrid stroke="#2b333b" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <Tooltip
                contentStyle={{ background: "#171c21", border: "1px solid #2b333b", borderRadius: 8 }}
                labelStyle={{ color: "#eef4f0" }}
              />
              {showLegend ? <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} /> : null}
              {chart.series.map((series, index) => <Line key={series.name} type="monotone" dataKey={series.name} stroke={colors[index % colors.length]} strokeWidth={3} dot={{ fill: colors[index % colors.length], strokeWidth: 0, r: 4 }} />)}
            </LineChart>
          ) : chartType === "pie" ? (
            <PieChart>
              <Pie data={data} dataKey={chart.series[0].name} nameKey="label" innerRadius={58} outerRadius={92} paddingAngle={3}>
                {chart.labels.map((label, index) => (
                  <Cell key={label} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#171c21", border: "1px solid #2b333b", borderRadius: 8 }}
                labelStyle={{ color: "#eef4f0" }}
              />
              {showLegend ? <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} /> : null}
            </PieChart>
          ) : chartType === "scatter" ? (
            <ScatterChart margin={chartMargins}>
              <CartesianGrid stroke="#2b333b" strokeDasharray="3 3" />
              <XAxis dataKey="label" type="category" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <YAxis type="number" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <ZAxis range={[64, 64]} />
              <Tooltip contentStyle={{ background: "#171c21", border: "1px solid #2b333b", borderRadius: 8 }} labelStyle={{ color: "#eef4f0" }} />
              {showLegend ? <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} /> : null}
              {chart.series.map((series, index) => <Scatter key={series.name} name={series.name} data={data} dataKey={series.name} fill={colors[index % colors.length]} />)}
            </ScatterChart>
          ) : (
            <BarChart data={data} margin={chartMargins}>
              <CartesianGrid stroke="#2b333b" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={{ stroke: "#2b333b" }} />
              <Tooltip
                contentStyle={{ background: "#171c21", border: "1px solid #2b333b", borderRadius: 8 }}
                labelStyle={{ color: "#eef4f0" }}
              />
              {showLegend ? <Legend wrapperStyle={{ color: "#cbd5e1", fontSize: 12 }} /> : null}
              {chart.series.map((series, index) => (
                <Bar key={series.name} dataKey={series.name} name={series.name} fill={colors[index % colors.length]} radius={[6, 6, 0, 0]}>
                  {chart.labels.map((label, labelIndex) => (
                    <Cell
                      key={`${label}-${labelIndex}`}
                      fill={labelIndex === 0 || label === chart.highlightedLabel ? "#f4bd50" : colors[index % colors.length]}
                    />
                  ))}
                </Bar>
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
