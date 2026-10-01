import { useState } from "react";

import type { HubProblem } from "../types";

/**
 * Problems are a first-class view, not a console warning.
 *
 * The whole premise is that an incomplete map should look incomplete. Hiding
 * the gaps in a log nobody opens would quietly undo that.
 */
export function ProblemsPanel({ problems }: { problems: HubProblem[] }) {
  const [open, setOpen] = useState(false);

  if (problems.length === 0) {
    return <div className="problems-pill clean">no problems</div>;
  }

  const errors = problems.filter((p) => p.severity === "error").length;

  return (
    <div className={`problems ${open ? "open" : ""}`}>
      <button className="problems-pill" onClick={() => setOpen(!open)}>
        {problems.length} problem{problems.length === 1 ? "" : "s"}
        {errors > 0 && <span className="err-count">{errors} error</span>}
      </button>

      {open && (
        <ul className="problem-list">
          {problems.map((problem, i) => (
            <li key={i} className={problem.severity}>
              <div className="problem-head">
                <span className={`sev sev-${problem.severity}`}>
                  {problem.severity}
                </span>
                <code>{problem.repo}</code>
              </div>
              <div>{problem.message}</div>
              {problem.detail && <div className="muted">{problem.detail}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
