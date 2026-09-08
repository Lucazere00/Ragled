"use client";

import { useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphData } from "@/types/api";

const groupColors = ["#54d6a8", "#f4bd50", "#6ea8fe", "#f17878", "#c084fc", "#8bd3dd"];

export default function GraphRenderer({ graph }: { graph: GraphData }) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const groupIndexes = useMemo(() => {
    const groups = new Map<string, number>();
    graph.nodes.forEach((node) => { if (node.group && !groups.has(node.group)) groups.set(node.group, groups.size); });
    return groups;
  }, [graph.nodes]);
  const graphData = useMemo(() => ({
    nodes: graph.nodes.map((node) => ({ ...node })),
    links: graph.edges.map((edge) => ({ ...edge }))
  }), [graph]);

  if (!graph.nodes.length) return null;

  return (
    <div className="overflow-hidden rounded-lg border border-line bg-coal/70">
      <div className="h-[24rem] w-full">
        <ForceGraph2D
          graphData={graphData}
          nodeLabel={(node) => `${node.label}${node.group ? ` (${node.group})` : ""}`}
          nodeColor={(node) => groupColors[(node.group ? groupIndexes.get(node.group) ?? 0 : 0) % groupColors.length]}
          nodeRelSize={6}
          linkColor={() => "#52606d"}
          linkLabel={(link) => link.label ?? ""}
          onNodeHover={(node) => setHoveredNode(node?.id ?? null)}
          nodeCanvasObject={(node, context, globalScale) => {
            const fontSize = Math.max(10 / globalScale, 2);
            context.beginPath();
            context.arc(node.x ?? 0, node.y ?? 0, 5, 0, 2 * Math.PI, false);
            context.fillStyle = groupColors[(node.group ? groupIndexes.get(node.group) ?? 0 : 0) % groupColors.length];
            context.fill();
            if (hoveredNode === node.id) {
              context.font = `${fontSize}px Sans-Serif`;
              context.textAlign = "center";
              context.textBaseline = "middle";
              context.fillStyle = "#eef4f0";
              context.fillText(node.label, node.x ?? 0, (node.y ?? 0) - 9);
            }
          }}
        />
      </div>
    </div>
  );
}