import dagre from "@dagrejs/dagre";
import type { Edge, Node } from "@xyflow/react";

import type { HubEdge, HubNode } from "./types";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 64;

/**
 * Layered top-to-bottom layout.
 *
 * Dependencies have a direction, so a layered graph reads far better here than
 * a force-directed one: callers sit above what they call, and infrastructure
 * settles at the bottom on its own.
 */
export function layout(
  hubNodes: HubNode[],
  hubEdges: HubEdge[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 48, ranksep: 88, marginx: 24, marginy: 24 });

  for (const node of hubNodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of hubEdges) {
    // Dagre throws on an edge referencing a node it does not know about.
    if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
      g.setEdge(edge.source, edge.target);
    }
  }

  dagre.layout(g);

  const nodes: Node[] = hubNodes.map((node) => {
    const positioned = g.node(node.id);
    return {
      id: node.id,
      type: "hub",
      // Dagre returns centre points; React Flow positions by top-left corner.
      position: {
        x: positioned.x - NODE_WIDTH / 2,
        y: positioned.y - NODE_HEIGHT / 2,
      },
      data: { node } as unknown as Record<string, unknown>,
    };
  });

  const edges: Edge[] = hubEdges.map((edge, index) => ({
    id: `${edge.source}->${edge.target}-${index}`,
    source: edge.source,
    target: edge.target,
    type: "smoothstep",
    data: { edge } as unknown as Record<string, unknown>,
  }));

  return { nodes, edges };
}
