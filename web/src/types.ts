/** Mirrors the collector's output. Keep in sync with `hub/graph.py`. */

export type NodeKind = "service" | "datastore" | "queue" | "unknown";
export type EdgeKind = "calls" | "stores" | "publishes" | "consumes";
export type Confidence = "verified" | "assumed" | "unknown";
export type Severity = "error" | "warning";

export interface HubNode {
  id: string;
  kind: NodeKind;
  label: string;
  purpose: string | null;
  team: string | null;
  lifecycle: string | null;
  tags: string[];
  /** False for anything inferred from someone else's descriptor rather than read. */
  described: boolean;
  repo_url: string | null;
  commit: string | null;
}

export interface HubEdge {
  source: string;
  target: string;
  kind: EdgeKind;
  confidence: Confidence;
  summary: string | null;
  via: string | null;
  code: string | null;
  code_url: string | null;
  topics: string[];
  /** Target is not described by any collected descriptor. */
  dangling: boolean;
}

export interface HubProblem {
  severity: Severity;
  source: string;
  repo: string;
  message: string;
  detail: string | null;
}

export interface HttpEndpoint {
  id: string;
  method: string;
  path: string;
  summary: string;
  code: string | null;
  flow: string | null;
}

export interface MessageEndpoint {
  id: string;
  channel: string;
  topic: string;
  direction: "publish" | "consume";
  summary: string;
  code: string | null;
  flow: string | null;
}

export interface ServiceDoc {
  service: {
    id: string;
    name: string;
    purpose: string;
    owner: { team: string; contact: string | null } | null;
    lifecycle: string;
    tags: string[];
  };
  source: { repo: string; default_branch: string; language: string | null } | null;
  provides: { http: HttpEndpoint[]; messages: MessageEndpoint[] };
  docs: {
    architecture: string | null;
    flows_index: string | null;
    changelog: string | null;
  };
  coverage: {
    http: string;
    messages: string;
    depends_on: string;
    notes: string | null;
  };
  verified: { commit: string | null; date: string | null };
}

export interface CollectedService {
  id: string;
  source: string;
  repo: string;
  repo_url: string | null;
  ref: string | null;
  commit: string | null;
  doc: ServiceDoc;
}

export interface HubData {
  generated_at: string;
  service_file: string;
  nodes: HubNode[];
  edges: HubEdge[];
  problems: HubProblem[];
  services: CollectedService[];
  stats: {
    services: number;
    nodes: number;
    edges: number;
    problems: number;
    unresolved_edges: number;
    unknown_targets: number;
  };
}
