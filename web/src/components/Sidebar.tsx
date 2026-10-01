import type { CollectedService, HubEdge, HubNode } from "../types";

interface Props {
  node: HubNode;
  service: CollectedService | undefined;
  outgoing: HubEdge[];
  incoming: HubEdge[];
  onClose: () => void;
  onSelect: (id: string) => void;
}

function Coverage({ value }: { value: string }) {
  return <span className={`coverage coverage-${value}`}>{value}</span>;
}

function EdgeRow({
  edge,
  peer,
  onSelect,
}: {
  edge: HubEdge;
  peer: string;
  onSelect: (id: string) => void;
}) {
  return (
    <li>
      <button className="peer" onClick={() => onSelect(peer)}>
        {peer}
      </button>
      <span className={`conf conf-${edge.confidence}`}>{edge.confidence}</span>
      {edge.summary && <div className="edge-summary">{edge.summary}</div>}
      {edge.code && <code className="code-ref">{edge.code}</code>}
    </li>
  );
}

export function Sidebar({
  node,
  service,
  outgoing,
  incoming,
  onClose,
  onSelect,
}: Props) {
  const doc = service?.doc;

  return (
    <aside className="sidebar">
      <header>
        <div>
          <h2>{node.label}</h2>
          <div className="muted">{node.id}</div>
        </div>
        <button className="close" onClick={onClose} aria-label="Close">
          ×
        </button>
      </header>

      {/* A node with no descriptor is the interesting case, not an error state:
          it is on the map only because something else declared a dependency. */}
      {!node.described && (
        <div className="notice">
          Not described. This node exists only because another service declares a
          dependency on it — nothing was collected from its own repository.
        </div>
      )}

      {doc && (
        <>
          <p className="purpose">{doc.service.purpose}</p>

          <dl className="meta">
            {doc.service.owner && (
              <>
                <dt>Team</dt>
                <dd>{doc.service.owner.team}</dd>
              </>
            )}
            {service?.repo && (
              <>
                <dt>Repository</dt>
                <dd>{service.repo}</dd>
              </>
            )}
            {doc.verified.commit && (
              <>
                <dt>Verified</dt>
                <dd>
                  <code>{doc.verified.commit}</code>
                  {doc.verified.date && ` · ${doc.verified.date}`}
                </dd>
              </>
            )}
          </dl>

          <section>
            <h3>Coverage</h3>
            <div className="coverage-row">
              <span>HTTP</span> <Coverage value={doc.coverage.http} />
              <span>Messages</span> <Coverage value={doc.coverage.messages} />
              <span>Dependencies</span> <Coverage value={doc.coverage.depends_on} />
            </div>
            {doc.coverage.notes && <p className="notes">{doc.coverage.notes}</p>}
          </section>

          {doc.provides.http.length > 0 && (
            <section>
              <h3>HTTP</h3>
              <ul className="endpoints">
                {doc.provides.http.map((ep) => (
                  <li key={ep.id}>
                    <div className="endpoint">
                      <span className={`method m-${ep.method.toLowerCase()}`}>
                        {ep.method}
                      </span>
                      <code>{ep.path}</code>
                    </div>
                    <div className="edge-summary">{ep.summary}</div>
                    {ep.code && <code className="code-ref">{ep.code}</code>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {doc.provides.messages.length > 0 && (
            <section>
              <h3>Messages</h3>
              <ul className="endpoints">
                {doc.provides.messages.map((msg) => (
                  <li key={msg.id}>
                    <div className="endpoint">
                      <span className={`method m-${msg.direction}`}>
                        {msg.direction}
                      </span>
                      <code>{msg.topic}</code>
                    </div>
                    <div className="edge-summary">{msg.summary}</div>
                    {msg.code && <code className="code-ref">{msg.code}</code>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {outgoing.length > 0 && (
        <section>
          <h3>Depends on</h3>
          <ul className="peers">
            {outgoing.map((edge, i) => (
              <EdgeRow
                key={i}
                edge={edge}
                peer={edge.target}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </section>
      )}

      {incoming.length > 0 && (
        <section>
          <h3>Depended on by</h3>
          <ul className="peers">
            {incoming.map((edge, i) => (
              <EdgeRow
                key={i}
                edge={edge}
                peer={edge.source}
                onSelect={onSelect}
              />
            ))}
          </ul>
        </section>
      )}

      {doc?.docs && (doc.docs.architecture || doc.docs.flows_index) && (
        <section>
          <h3>Documents</h3>
          <ul className="docs">
            {doc.docs.architecture && <li><code>{doc.docs.architecture}</code></li>}
            {doc.docs.flows_index && <li><code>{doc.docs.flows_index}</code></li>}
            {doc.docs.changelog && <li><code>{doc.docs.changelog}</code></li>}
          </ul>
        </section>
      )}
    </aside>
  );
}
