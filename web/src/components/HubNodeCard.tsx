import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { HubNode } from "../types";

const KIND_LABEL: Record<HubNode["kind"], string> = {
  service: "service",
  datastore: "datastore",
  queue: "queue",
  unknown: "undetermined",
};

export function HubNodeCard({ data, selected }: NodeProps) {
  const node = (data as unknown as { node: HubNode }).node;

  const classes = [
    "node-card",
    `kind-${node.kind}`,
    node.described ? "described" : "undescribed",
    selected ? "selected" : "",
  ]
    .filter(Boolean)
    .join(" ");

  // Subtitle carries the most useful distinguishing fact available: who owns a
  // described service, or — more importantly — that a node was never described
  // and is only on the map because something else pointed at it.
  const subtitle = node.described
    ? (node.team ?? KIND_LABEL[node.kind])
    : node.kind === "unknown"
      ? "target not established"
      : "not described";

  return (
    <div className={classes}>
      <Handle type="target" position={Position.Top} />
      <div className="node-label">{node.label}</div>
      <div className="node-sub">{subtitle}</div>
      {node.lifecycle && node.lifecycle !== "active" && (
        <div className="node-badge">{node.lifecycle}</div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
