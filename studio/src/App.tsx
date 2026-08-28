// SPDX-License-Identifier: Apache-2.0

const primitives = [
  "Identity",
  "Mandate",
  "Work",
  "Approval",
  "Causality",
] as const;

export function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="wordmark"
          href="#top"
          aria-label="Digital Colleagues home"
        >
          <span className="wordmark-mark" aria-hidden="true">
            DC
          </span>
          <span>Digital Colleagues</span>
        </a>
        <span className="milestone-tag">P2 · Core primitives</span>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">Local-first reference stack</p>
            <h1 id="hero-title">
              Persistent coworkers need explicit boundaries.
            </h1>
            <p className="lede">
              Build, govern, and run AI coworkers whose identity, authority,
              work, effects, and causal history can be inspected—not merely
              inferred.
            </p>
            <div
              className="boundary-note"
              role="note"
              aria-label="Milestone boundary"
            >
              <span className="boundary-pulse" aria-hidden="true" />
              Immutable core contracts are ready. Runtime orchestration begins
              in P3.
            </div>
          </div>

          <div
            className="system-frame"
            aria-label="Target architecture primitives"
          >
            <div className="frame-heading">
              <span>Reference control plane</span>
              <span className="frame-state">Core contract</span>
            </div>
            <ol className="primitive-list">
              {primitives.map((primitive, index) => (
                <li key={primitive}>
                  <span className="primitive-index">0{index + 1}</span>
                  <span>{primitive}</span>
                  <span className="primitive-line" aria-hidden="true" />
                </li>
              ))}
            </ol>
            <p className="frame-caption">
              Deterministic reference path · no live provider required
            </p>
          </div>
        </section>

        <section className="definition" aria-labelledby="definition-title">
          <p className="section-number">01 / DEFINITION</p>
          <div>
            <h2 id="definition-title">Beyond a task agent</h2>
            <p>
              A digital colleague operates under a durable, revisable mandate.
              It owns ongoing responsibilities, resumes finite work, proposes
              exact effects for human review, and preserves why each result
              happened.
            </p>
          </div>
        </section>
      </main>

      <footer>
        <span>Apache-2.0</span>
        <span>Pre-release · local reference only</span>
      </footer>
    </div>
  );
}
