import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useState } from "react";

import { HubNodeCard } from "./components/HubNodeCard";
import { ProblemsPanel } from "./components/ProblemsPanel";
import { Sidebar } from "./components/Sidebar";
import { layout } from "./layout";
import type { EdgeKind, HubData } from "./types";

const nodeTypes = { hub: HubNodeCard };

const EDGE_FILTERS: { key: EdgeKind; label: string }[] = [
  { key: "calls", label: "Calls" },
  { key: "stores", label: "Storage" },
  { key: "publishes", label: "Publishes" },
  { key: "consumes", label: "Consumes" },
];

export default function App() {
  const [data, setData] = useState<HubData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [hidden, setHidden] = useState<Set<EdgeKind>>(new Set());

  useEffect(() => {
    fetch("./hub.json")
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const visibleEdges = useMemo(
    () => data?.edges.filter((e) => !hidden.has(e.kind)) ?? [],
    [data, hidden],
  );

  const { nodes, edges } = useMemo(() => {
    if (!data) return { nodes: [] as Node[], edges: [] as Edge[] };
    return layout(data.nodes, visibleEdges);
  }, [data, visibleEdges]);

  const query = search.trim().toLowerCase();

  // Search dims rather than removes: a node vanishing mid-search makes the map
  // jump and loses the context of where the match sits.
  const styledNodes = useMemo(
    () =>
      nodes.map((n) => {
        const hubNode = (n.data as { node: { label: string; id: string } }).node;
        const matches =
          !query ||
          hubNode.label.toLowerCase().includes(query) ||
          hubNode.id.toLowerCase().includes(query);
        return {
          ...n,
          selected: n.id === selected,
          style: { opacity: matches ? 1 : 0.25 },
        };
      }),
    [nodes, query, selected],
  );

  const styledEdges = useMemo(
    () =>
      edges.map((e) => {
        const edge = (e.data as { edge: { confidence: string; dangling: boolean } })
          .edge;
        const touchesSelected =
          selected !== null && (e.source === selected || e.target === selected);
        const unproven = edge.confidence !== "verified";
        return {
          ...e,
          animated: touchesSelected,
          style: {
            // Anything not verified is drawn as not verified. The map should
            // never make an assumption look like a confirmed fact.
            strokeDasharray: unproven ? "6 4" : undefined,
            stroke: touchesSelected ? "#7f77dd" : edge.dangling ? "#b4b2a9" : "#9aa3ae",
            strokeWidth: touchesSelected ? 2 : 1.4,
          },
        };
      }),
    [edges, selected],
  );

  if (error) {
    return (
      <div className="boot">
        <h1>No data</h1>
        <p>
          Could not load <code>hub.json</code>: {error}
        </p>
        <p className="muted">
          Generate it with <code>hub collect -o web/public/hub.json</code>
        </p>
      </div>
    );
  }

  if (!data) return <div className="boot muted">Loading…</div>;

  const selectedNode = data.nodes.find((n) => n.id === selected);
  const selectedService = data.services.find((s) => s.id === selected);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">platform-hub</div>

        <input
          className="search"
          placeholder="Search services…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        <div className="filters">
          {EDGE_FILTERS.map((f) => (
            <button
              key={f.key}
              className={hidden.has(f.key) ? "off" : "on"}
              onClick={() => {
                const next = new Set(hidden);
                next.has(f.key) ? next.delete(f.key) : next.add(f.key);
                setHidden(next);
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="stats">
          {data.stats.services} services · {data.stats.edges} edges
        </div>

        <ProblemsPanel problems={data.problems} />
      </header>

      <main>
        <ReactFlow
          nodes={styledNodes}
          edges={styledEdges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, n) => setSelected(n.id)}
          onPaneClick={() => setSelected(null)}
          fitView
          minZoom={0.2}
          proOptions={{ hideAttribution: false }}
        >
          <Background gap={20} size={1} />
          <Controls showInteractive={false} />
          <MiniMap pannable zoomable />
        </ReactFlow>

        {selectedNode && (
          <Sidebar
            node={selectedNode}
            service={selectedService}
            outgoing={data.edges.filter((e) => e.source === selected)}
            incoming={data.edges.filter((e) => e.target === selected)}
            onClose={() => setSelected(null)}
            onSelect={setSelected}
          />
        )}
      </main>
    </div>
  );
}
