import { STATUS_CONFIG, METHOD_LABELS, formatCurrency, parsePlan } from '../data';

// ─────────────────────────────────────────────
// StatusBadge
// ─────────────────────────────────────────────
export function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.not_affordable;
  return (
    <span className={`badge ${cfg.cls}`}>
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

// ─────────────────────────────────────────────
// DecisionCard — Hero card for single request
// ─────────────────────────────────────────────
export function DecisionCard({ decision }) {
  if (!decision) return null;
  const cfg = STATUS_CONFIG[decision.affordability_status] || STATUS_CONFIG.not_affordable;
  const method = METHOD_LABELS[decision.recommended_payment_method] || { label: decision.recommended_payment_method, icon: '?' };
  const plan = parsePlan(decision.payment_plan);
  const safeAmt = decision.amount_safe_to_pay;

  return (
    <div className="decision-card card" style={{ borderColor: cfg.border }}>
      {/* Glow accent top border */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 3, background: cfg.color, borderRadius: '16px 16px 0 0' }} />

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div className="decision-label">Amount Safe to Pay</div>
          <div className="decision-amount">
            {formatCurrency(safeAmt, decision.currency)}
          </div>
          <StatusBadge status={decision.affordability_status} />
          <div className="decision-method" style={{ marginTop: 10 }}>
            {method.icon} {method.label}
          </div>
        </div>

        {/* Item info */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 4 }}>Purchase Request</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            {decision.item || decision.request_id}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 4 }}>
            {formatCurrency(decision.requested_amount, decision.currency)}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
            by {decision.desired_completion_date || '—'}
          </div>
        </div>
      </div>

      {/* Explanation */}
      <div style={{
        marginTop: 20, padding: '14px 18px',
        background: 'rgba(255,255,255,0.03)',
        borderRadius: 10,
        border: '1px solid var(--border)',
        fontSize: '0.87rem', color: 'var(--text-secondary)', lineHeight: 1.7,
      }}>
        {decision.decision_explanation}
      </div>

      {/* Payment Plan */}
      {plan.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <div style={{ fontSize: '0.78rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1, color: 'var(--text-muted)', marginBottom: 12 }}>
            Payment Schedule
          </div>
          <div className="plan-timeline">
            {plan.map((step, i) => (
              <div className="plan-step" key={i}>
                <div className="plan-dot" />
                <div className="plan-date">{step.date}</div>
                <div className="plan-amount">{formatCurrency(step.amount, decision.currency)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// MetricBar — accuracy display
// ─────────────────────────────────────────────
export function MetricBar({ label, value, color = 'var(--accent-blue)' }) {
  const pct = Math.round(value * 100);
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: '0.83rem', color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ fontSize: '0.83rem', fontWeight: 700, color }}>{pct}%</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${color}, ${color}88)` }} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// StatCard
// ─────────────────────────────────────────────
export function StatCard({ icon, label, value, sub, accentColor = 'var(--accent-blue)', accentBg }) {
  return (
    <div className="stat-card" style={{ '--accent-color': accentColor, '--accent-bg': accentBg || `${accentColor}18` }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-change up">{sub}</div>}
    </div>
  );
}

// ─────────────────────────────────────────────
// DonutChart — SVG donut
// ─────────────────────────────────────────────
export function DonutChart({ data, size = 160 }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;

  const cx = size / 2, cy = size / 2;
  const r = size * 0.35, stroke = size * 0.14;

  let angle = -90;
  const segments = data.map(d => {
    const sweep = (d.value / total) * 360;
    const start = angle;
    angle += sweep;
    return { ...d, start, sweep };
  });

  function arcPath(start, sweep) {
    const toRad = a => (a * Math.PI) / 180;
    const x1 = cx + r * Math.cos(toRad(start));
    const y1 = cy + r * Math.sin(toRad(start));
    const x2 = cx + r * Math.cos(toRad(start + sweep));
    const y2 = cy + r * Math.sin(toRad(start + sweep));
    const large = sweep > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {segments.map((s, i) => (
          <path
            key={i}
            d={arcPath(s.start, s.sweep - 1)}
            fill="none"
            stroke={s.color}
            strokeWidth={stroke}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 6px ${s.color}66)` }}
          />
        ))}
        <text x={cx} y={cy - 6} textAnchor="middle" fill="var(--text-primary)" fontSize={size * 0.16} fontWeight={700}>
          {total}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill="var(--text-muted)" fontSize={size * 0.09}>
          requests
        </text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.map((d, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: d.color, flexShrink: 0 }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{d.label}</span>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: d.color, marginLeft: 'auto', paddingLeft: 12 }}>{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
