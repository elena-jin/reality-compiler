import { Package, Link2, Wrench, ShieldCheck, AlertTriangle, ExternalLink, ChevronDown, ChevronUp, Factory, Layers } from "lucide-react";
import { useState } from "react";

function Card({ title, icon: Icon, children, visible, delay, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      className={`rc-card ${visible ? "rc-card-visible" : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <button className="rc-card-header" onClick={() => setOpen(!open)} type="button">
        <div className="rc-card-title">
          <Icon size={14} strokeWidth={1.5} />
          <span>{title}</span>
        </div>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && <div className="rc-card-body">{children}</div>}
    </div>
  );
}

function FeasibilityBadge({ score }) {
  const colors = {
    green: { bg: "rgba(16, 185, 129, 0.12)", text: "#10b981", label: "Feasible" },
    yellow: { bg: "rgba(245, 158, 11, 0.12)", text: "#f59e0b", label: "Moderate" },
    red: { bg: "rgba(239, 68, 68, 0.12)", text: "#ef4444", label: "Challenging" },
  };
  const c = colors[score] || colors.green;
  return (
    <span className="rc-feasibility-badge" style={{ background: c.bg, color: c.text }}>
      <span className="rc-feasibility-dot" style={{ background: c.text }} />
      {c.label}
    </span>
  );
}

function RiskBadge({ severity }) {
  const colors = { green: "#10b981", yellow: "#f59e0b", red: "#ef4444" };
  return <span className="rc-risk-dot" style={{ background: colors[severity] || colors.green }} />;
}

function TabSwitcher({ tabs, active, onChange }) {
  return (
    <div className="rc-tab-switcher">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          className={`rc-tab-btn ${active === tab.id ? "rc-tab-active" : ""}`}
          onClick={() => onChange(tab.id)}
          type="button"
        >
          <tab.icon size={12} />
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  );
}

function MassProductionGuide({ feasibility, bom }) {
  const unitCost = feasibility?.manufacturing_unit_cost_gbp || 0;
  const quantities = [100, 500, 1000, 5000];
  return (
    <div className="rc-mass-production">
      <div className="rc-mp-header">
        <Factory size={14} />
        <span>Manufacturing Scale Analysis</span>
      </div>

      <div className="rc-mp-guide-overlay">
        <div className="rc-mp-guide-title">Production Readiness</div>
        <div className="rc-mp-guide-steps">
          <div className="rc-mp-step">
            <div className="rc-mp-step-num">1</div>
            <div>
              <strong>Design for Manufacturing</strong>
              <p>Simplify geometry, reduce unique parts, standardize fasteners</p>
            </div>
          </div>
          <div className="rc-mp-step">
            <div className="rc-mp-step-num">2</div>
            <div>
              <strong>Material Selection</strong>
              <p>Switch 3D-printed parts to injection moulding for volumes &gt;500</p>
            </div>
          </div>
          <div className="rc-mp-step">
            <div className="rc-mp-step-num">3</div>
            <div>
              <strong>Supply Chain</strong>
              <p>Negotiate MOQ pricing, establish supplier relationships</p>
            </div>
          </div>
          <div className="rc-mp-step">
            <div className="rc-mp-step-num">4</div>
            <div>
              <strong>Quality & Testing</strong>
              <p>Define acceptance criteria, set up QC stations</p>
            </div>
          </div>
        </div>
      </div>

      <table className="rc-bom-table">
        <thead>
          <tr>
            <th>Volume</th>
            <th>Unit Cost</th>
            <th>Tooling</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {quantities.map((qty) => {
            const discount = qty >= 5000 ? 0.45 : qty >= 1000 ? 0.55 : qty >= 500 ? 0.65 : 0.75;
            const adjusted = unitCost * discount;
            const tooling = qty >= 1000 ? 2500 : qty >= 500 ? 1500 : 500;
            return (
              <tr key={qty}>
                <td className="rc-bom-name">{qty.toLocaleString()} units</td>
                <td className="rc-bom-cost">£{adjusted.toFixed(2)}</td>
                <td className="rc-bom-cost">£{tooling.toLocaleString()}</td>
                <td className="rc-bom-cost rc-bom-total">
                  £{(adjusted * qty + tooling).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="rc-mp-notes">
        <p>Estimates based on Shenzhen manufacturing for electronics + UK assembly. Tooling includes injection mould setup for custom enclosures.</p>
      </div>
    </div>
  );
}

export default function ResultsPanel({ result, loading, revealStage, error }) {
  const [bomTab, setBomTab] = useState("prototype");

  if (error) {
    return (
      <div className="rc-panel rc-results-panel">
        <div className="rc-error">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!result && !loading) {
    return (
      <div className="rc-panel rc-results-panel">
        <div className="rc-results-empty">
          <p>Results will appear here after generation</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rc-panel rc-results-panel">
        <div className="rc-results-loading">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rc-skeleton-card">
              <div className="rc-skeleton-header" />
              <div className="rc-skeleton-line" />
              <div className="rc-skeleton-line rc-skeleton-short" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const { bom, sourcing, assembly, feasibility } = result;

  const groupedSourcing = {};
  if (sourcing?.links) {
    for (const link of sourcing.links) {
      if (!groupedSourcing[link.platform]) groupedSourcing[link.platform] = [];
      groupedSourcing[link.platform].push(link);
    }
  }

  const bomTabs = [
    { id: "prototype", label: "Prototype", icon: Layers },
    { id: "mass", label: "Mass Production", icon: Factory },
  ];

  return (
    <div className="rc-panel rc-results-panel">
      <Card title="Bill of Materials" icon={Package} visible={revealStage >= 1} delay={0}>
        <TabSwitcher tabs={bomTabs} active={bomTab} onChange={setBomTab} />
        {bomTab === "prototype" ? (
          <table className="rc-bom-table">
            <thead>
              <tr>
                <th>Component</th>
                <th>Qty</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {bom?.items?.map((item, i) => (
                <tr key={i}>
                  <td>
                    <div className="rc-bom-name">{item.name}</div>
                    <div className="rc-bom-spec">{item.specification}</div>
                  </td>
                  <td className="rc-bom-qty">{item.quantity}</td>
                  <td className="rc-bom-cost">
                    £{(item.unit_cost_gbp * item.quantity).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={2}>Total</td>
                <td className="rc-bom-cost rc-bom-total">£{bom?.total_cost_gbp?.toFixed(2)}</td>
              </tr>
            </tfoot>
          </table>
        ) : (
          <MassProductionGuide feasibility={feasibility} bom={bom} />
        )}
      </Card>

      <Card title="Sourcing Links" icon={Link2} visible={revealStage >= 2} delay={100} defaultOpen={false}>
        <div className="rc-sourcing-groups">
          {Object.entries(groupedSourcing).map(([platform, links]) => (
            <div key={platform} className="rc-sourcing-group">
              <div className="rc-sourcing-platform">{platform}</div>
              {links.map((link, i) => (
                <a key={i} href={link.url} target="_blank" rel="noopener noreferrer" className="rc-sourcing-link">
                  <span>{link.component}</span>
                  <ExternalLink size={10} />
                </a>
              ))}
            </div>
          ))}
        </div>
      </Card>

      <Card title="Assembly Steps" icon={Wrench} visible={revealStage >= 3} delay={200} defaultOpen={false}>
        <div className="rc-assembly-steps">
          {assembly?.steps?.map((step) => (
            <div key={step.step_number} className="rc-assembly-step">
              <div className="rc-step-number">{step.step_number}</div>
              <div className="rc-step-content">
                <div className="rc-step-title">{step.title}</div>
                <div className="rc-step-desc">{step.description}</div>
                {step.tools_required?.length > 0 && (
                  <div className="rc-step-tools">
                    {step.tools_required.map((tool, i) => (
                      <span key={i} className="rc-tool-chip">{tool}</span>
                    ))}
                  </div>
                )}
                <div className="rc-step-time">~{step.estimated_time_min} min</div>
              </div>
            </div>
          ))}
          {assembly?.total_time_min > 0 && (
            <div className="rc-assembly-total">
              Total estimated time: {assembly.total_time_min} minutes
            </div>
          )}
        </div>
      </Card>

      <Card title="Feasibility Assessment" icon={ShieldCheck} visible={revealStage >= 4} delay={300}>
        <div className="rc-feasibility">
          <div className="rc-feasibility-header">
            <FeasibilityBadge score={feasibility?.score} />
          </div>
          <p className="rc-feasibility-summary">{feasibility?.summary}</p>
          <div className="rc-cost-estimates">
            <div className="rc-cost-row">
              <span>Prototype cost</span>
              <span className="rc-cost-value">£{feasibility?.prototype_cost_gbp?.toFixed(2)}</span>
            </div>
            <div className="rc-cost-row">
              <span>Manufacturing unit cost</span>
              <span className="rc-cost-value">£{feasibility?.manufacturing_unit_cost_gbp?.toFixed(2)}</span>
            </div>
          </div>
          {feasibility?.risks?.length > 0 && (
            <div className="rc-risks">
              <div className="rc-risks-title">Risk Assessment</div>
              {feasibility.risks.map((risk, i) => (
                <div key={i} className="rc-risk-item">
                  <div className="rc-risk-header">
                    <RiskBadge severity={risk.severity} />
                    <span className="rc-risk-area">{risk.area}</span>
                  </div>
                  <p className="rc-risk-desc">{risk.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
