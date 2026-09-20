

import { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import {
  SAMPLE_DECISIONS, SAMPLE_METRICS, OUTPUT_DISTRIBUTION,
  METHOD_DISTRIBUTION, STATUS_CONFIG, METHOD_LABELS, formatCurrency, parsePlan,
} from './data';
import { StatusBadge, DecisionCard, MetricBar, StatCard, DonutChart } from './components/ui';

// ─────────────────────────────────────────────
// Generate mock cash-flow forecast data
// ─────────────────────────────────────────────
function generateForecast(balance, minBalance) {
  const data = [];
  let bal = balance;
  const income = balance * 0.15;
  const expenses = balance * 0.12;
  for (let i = 0; i <= 90; i += 3) {
    if (i > 0 && i % 30 === 0) bal += income;
    bal -= expenses / 10;
    bal += (Math.random() - 0.48) * balance * 0.015;
    data.push({
      day: i,
      balance: Math.max(minBalance * 0.3, bal),
      minimum: minBalance,
    });
  }
  return data;
}

// ─────────────────────────────────────────────
// Custom Recharts Tooltip
// ─────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 8, padding: '10px 14px',
      fontSize: '0.82rem', color: 'var(--text-primary)',
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Day {label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>
          {p.name}: {p.value.toLocaleString()}
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Overview Page
// ─────────────────────────────────────────────
export function OverviewPage() {
  const [animated, setAnimated] = useState(false);
  useEffect(() => { setTimeout(() => setAnimated(true), 100); }, []);

  const donutData = [
    { label: 'Affordable Now', value: OUTPUT_DISTRIBUTION.affordable_now, color: '#4ade80' },
    { label: 'With Plan', value: OUTPUT_DISTRIBUTION.affordable_with_plan, color: '#60a5fa' },
    { label: 'Affordable Later', value: OUTPUT_DISTRIBUTION.affordable_later, color: '#fbbf24' },
    { label: 'Not Affordable', value: OUTPUT_DISTRIBUTION.not_affordable, color: '#f87171' },
  ];

  const total = Object.values(OUTPUT_DISTRIBUTION).reduce((a, b) => a + b, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Hero stats */}
      <div className="stats-grid">
        <StatCard icon="📊" label="Requests Processed" value={total.toString()} sub="250 main + 25 samples" accentColor="#60a5fa" />
        <StatCard icon="✓" label="Status Accuracy" value={`${Math.round(SAMPLE_METRICS.status_accuracy * 100)}%`} sub="24 / 25 matched" accentColor="#4ade80" />
        <StatCard icon="💳" label="Method Accuracy" value={`${Math.round(SAMPLE_METRICS.method_accuracy * 100)}%`} sub="24 / 25 matched" accentColor="#22d3ee" />
        <StatCard icon="⚡" label="Avg Speed" value="7ms" sub="per request" accentColor="#a78bfa" />
      </div>

      {/* Distribution + Accuracy */}
      <div className="grid-2">
        {/* Donut */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">🎯 Affordability Distribution</div>
              <div className="card-subtitle">All 275 processed requests</div>
            </div>
          </div>
          <DonutChart data={donutData} size={170} />
        </div>

        {/* Accuracy breakdown */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">📈 Model Accuracy (25 samples)</div>
              <div className="card-subtitle">Compared to ground truth</div>
            </div>
          </div>
          <MetricBar label="Affordability Status" value={SAMPLE_METRICS.status_accuracy} color="#4ade80" />
          <MetricBar label="Payment Method" value={SAMPLE_METRICS.method_accuracy} color="#60a5fa" />
          <MetricBar label="Payment Plan" value={SAMPLE_METRICS.plan_accuracy} color="#22d3ee" />
          <MetricBar label="Spending Changes" value={SAMPLE_METRICS.changes_accuracy} color="#a78bfa" />
          <MetricBar label="Overall Weighted Score" value={SAMPLE_METRICS.avg_score} color="#fbbf24" />
        </div>
      </div>

      {/* Method bar chart */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">💰 Payment Method Recommendations</div>
            <div className="card-subtitle">Across all 275 requests</div>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart
            data={[
              { name: 'Full Payment', value: METHOD_DISTRIBUTION.full_payment, color: '#4ade80' },
              { name: 'Installments', value: METHOD_DISTRIBUTION.installments, color: '#60a5fa' },
              { name: 'Wait', value: METHOD_DISTRIBUTION.wait, color: '#fbbf24' },
              { name: 'Not Recommended', value: METHOD_DISTRIBUTION.not_recommended, color: '#f87171' },
            ]}
            barSize={52}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {[
                { color: '#4ade80' }, { color: '#60a5fa' },
                { color: '#fbbf24' }, { color: '#f87171' },
              ].map((c, i) => <Cell key={i} fill={c.color} fillOpacity={0.85} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Decisions Page
// ─────────────────────────────────────────────
export function DecisionsPage() {
  const [selected, setSelected] = useState(SAMPLE_DECISIONS[0]);
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all'
    ? SAMPLE_DECISIONS
    : SAMPLE_DECISIONS.filter(d => d.affordability_status === filter);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Filter bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {['all', ...Object.keys(STATUS_CONFIG)].map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              padding: '6px 16px',
              borderRadius: 20,
              border: `1px solid ${filter === s ? STATUS_CONFIG[s]?.color || 'var(--accent-blue)' : 'var(--border)'}`,
              background: filter === s ? (STATUS_CONFIG[s]?.bg || 'rgba(96,165,250,0.1)') : 'transparent',
              color: filter === s ? (STATUS_CONFIG[s]?.color || 'var(--accent-blue)') : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            {s === 'all' ? 'All Requests' : STATUS_CONFIG[s]?.label}
          </button>
        ))}
      </div>

      <div className="grid-2" style={{ gridTemplateColumns: '1fr 1.6fr' }}>
        {/* Request list */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
            <div className="card-title">📋 Requests ({filtered.length})</div>
          </div>
          <div style={{ maxHeight: 480, overflowY: 'auto' }}>
            {filtered.map(d => {
              const cfg = STATUS_CONFIG[d.affordability_status];
              return (
                <div
                  key={d.request_id}
                  onClick={() => setSelected(d)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 20px',
                    cursor: 'pointer',
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: selected?.request_id === d.request_id ? 'rgba(96,165,250,0.06)' : 'transparent',
                    borderLeft: `3px solid ${selected?.request_id === d.request_id ? cfg?.color || 'transparent' : 'transparent'}`,
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{
                    width: 36, height: 36, borderRadius: 10, background: cfg?.bg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '1rem', flexShrink: 0,
                  }}>
                    {cfg?.icon}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {d.item || d.request_id}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{d.request_id}</div>
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 700, color: cfg?.color }}>
                    {formatCurrency(d.amount_safe_to_pay, d.currency)}
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <div className="empty-title">No requests</div>
                <div className="empty-desc">Try a different filter</div>
              </div>
            )}
          </div>
        </div>

        {/* Decision detail */}
        {selected
          ? <DecisionCard decision={selected} />
          : <div className="card empty-state">
            <div className="empty-icon">👆</div>
            <div className="empty-title">Select a request</div>
            <div className="empty-desc">Click any row to see the decision details</div>
          </div>
        }
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Financial Twin Page
// ─────────────────────────────────────────────
export function FinancialTwinPage() {
  const twin = {
    user_id: 'user_01',
    name: 'Priya Sharma',
    currency: 'INR',
    balance: 285000,
    minBalance: 50000,
    income: [{ source: 'Salary', amount: 85000, day: 1, confirmed: true }],
    expenses: [
      { category: 'rent', amount: 25000, day: 1, flex: 'fixed' },
      { category: 'groceries', amount: 12000, day: 10, flex: 'reducible' },
      { category: 'transport', amount: 5000, day: 5, flex: 'reducible' },
      { category: 'utilities', amount: 3500, day: 8, flex: 'fixed' },
      { category: 'netflix', amount: 649, day: 15, flex: 'stoppable' },
      { category: 'gym', amount: 2000, day: 1, flex: 'stoppable' },
    ],
  };

  const forecast = generateForecast(twin.balance, twin.minBalance);
  const totalExpenses = twin.expenses.reduce((s, e) => s + e.amount, 0);
  const netFlow = twin.income[0].amount - totalExpenses;
  const safeNow = twin.balance - twin.minBalance - totalExpenses;

  const FLEX_COLORS = { fixed: '#f87171', reducible: '#fbbf24', stoppable: '#4ade80' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Twin header */}
      <div className="card" style={{ background: 'linear-gradient(135deg, var(--bg-card), rgba(13,21,48,0.8))', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: -60, right: -60, width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(96,165,250,0.08), transparent)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
          <div style={{
            width: 64, height: 64, borderRadius: 20,
            background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.8rem', flexShrink: 0,
          }}>
            👤
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>{twin.name}</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{twin.user_id} • {twin.currency}</div>
          </div>
          <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
            {[
              { label: 'Current Balance', value: formatCurrency(twin.balance, twin.currency), color: '#4ade80' },
              { label: 'Safe to Spend', value: formatCurrency(Math.max(0, safeNow), twin.currency), color: '#60a5fa' },
              { label: 'Net Monthly', value: formatCurrency(netFlow, twin.currency), color: netFlow >= 0 ? '#4ade80' : '#f87171' },
            ].map((m, i) => (
              <div key={i} style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{m.label}</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, color: m.color }}>{m.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Cash Flow Forecast */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">📈 90-Day Cash Flow Forecast</div>
              <div className="card-subtitle">Projected balance vs minimum reserve</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={forecast} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="balGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="minGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f87171" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={v => `D${v}`} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="minimum" stroke="#f87171" strokeWidth={1.5} strokeDasharray="4 4" fill="url(#minGrad)" dot={false} name="Minimum" />
              <Area type="monotone" dataKey="balance" stroke="#60a5fa" strokeWidth={2} fill="url(#balGrad)" dot={false} name="Balance" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Recurring Expenses */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">💸 Monthly Commitments</div>
              <div className="card-subtitle">Recurring expense breakdown</div>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Total: {formatCurrency(totalExpenses, twin.currency)}
            </div>
          </div>
          <div>
            {twin.expenses.map((exp, i) => (
              <div className="expense-item" key={i}>
                <div className="expense-dot" style={{ background: FLEX_COLORS[exp.flex] }} />
                <div className="expense-name" style={{ textTransform: 'capitalize' }}>{exp.category}</div>
                <div className={`expense-flex flex-${exp.flex}`}>{exp.flex}</div>
                <div className="expense-amount">{formatCurrency(exp.amount, twin.currency)}</div>
              </div>
            ))}
          </div>
          <div className="divider" />
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {[
              { flex: 'fixed', label: 'Fixed', color: '#f87171' },
              { flex: 'reducible', label: 'Reducible', color: '#fbbf24' },
              { flex: 'stoppable', label: 'Stoppable', color: '#4ade80' },
            ].map(f => (
              <div key={f.flex} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: f.color }} />
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  {f.label}: {formatCurrency(twin.expenses.filter(e => e.flex === f.flex).reduce((s, e) => s + e.amount, 0), twin.currency)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// New Request Page
// ─────────────────────────────────────────────
export function NewRequestPage() {
  const [form, setForm] = useState({
    user_id: 'user_01',
    item: '',
    amount: '',
    currency: 'INR',
    date: new Date().toISOString().split('T')[0],
    deadline: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const update = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const simulate = async () => {
    if (!form.amount || !form.item) return;
    setLoading(true);
    setResult(null);
    await new Promise(r => setTimeout(r, 1200)); // simulate API latency

    // Deterministic mock based on amount
    const amt = parseFloat(form.amount);
    const userBalance = { user_01: 285000, user_04: 52206950, user_08: 1536, user_16: 12400, user_22: 8800 };
    const userMin = { user_01: 50000, user_04: 30686600, user_08: 800, user_16: 2000, user_22: 1500 };
    const bal = userBalance[form.user_id] || 10000;
    const minBal = userMin[form.user_id] || 1000;
    const safeAmt = Math.max(0, bal * 0.72 - minBal);

    let status, method, plan, explanation;
    if (amt <= safeAmt) {
      status = 'affordable_now'; method = 'full_payment';
      plan = 'none';
      explanation = `Your current balance of ${formatCurrency(bal, form.currency)} safely covers ${formatCurrency(amt, form.currency)} while maintaining your minimum reserve.`;
    } else if (amt <= bal * 0.9) {
      status = 'affordable_with_plan'; method = 'installments';
      const next = new Date(form.date); next.setMonth(next.getMonth() + 1);
      plan = `${next.toISOString().split('T')[0]}:${(amt / 2).toFixed(2)}|${new Date(next.getFullYear(), next.getMonth() + 1, next.getDate()).toISOString().split('T')[0]}:${(amt / 2).toFixed(2)}`;
      explanation = `A 2-installment plan starting next month safely distributes the cost while protecting your minimum reserve.`;
    } else if (amt <= bal * 1.2) {
      status = 'affordable_later'; method = 'wait';
      const next = new Date(form.date); next.setDate(15); next.setMonth(next.getMonth() + 1);
      plan = `${next.toISOString().split('T')[0]}:${amt.toFixed(2)}`;
      explanation = `After your next salary payment you will have sufficient funds. We recommend waiting until ${next.toLocaleDateString()}.`;
    } else {
      status = 'not_affordable'; method = 'not_recommended';
      plan = 'none';
      explanation = `The requested amount significantly exceeds your available cash flow. No safe payment path exists within the 90-day forecast window.`;
    }

    setResult({
      request_id: `sim_${Date.now()}`,
      item: form.item,
      requested_amount: amt,
      currency: form.currency,
      amount_safe_to_pay: Math.min(safeAmt, amt),
      affordability_status: status,
      recommended_payment_method: method,
      payment_plan: plan,
      earliest_date_for_full_payment: method === 'wait' ? plan.split(':')[0] : '',
      spending_changes_needed: 'none',
      decision_explanation: explanation,
      desired_completion_date: form.deadline,
    });
    setLoading(false);
  };

  return (
    <div className="grid-2" style={{ gridTemplateColumns: '1fr 1.4fr', alignItems: 'start' }}>
      {/* Form */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 4 }}>
          <div>
            <div className="card-title">💬 New Affordability Request</div>
            <div className="card-subtitle">Ask if you can safely afford a purchase</div>
          </div>
        </div>
        <div className="divider" />

        <div className="form-group">
          <label className="form-label">Item / Purchase Description</label>
          <input className="form-input" value={form.item} onChange={update('item')} placeholder="e.g. MacBook Pro 14&quot;, Emergency car repair..." />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label className="form-label">Amount</label>
            <input className="form-input" type="number" value={form.amount} onChange={update('amount')} placeholder="0.00" min="0" />
          </div>
          <div className="form-group">
            <label className="form-label">Currency</label>
            <select className="form-select" value={form.currency} onChange={update('currency')}>
              {['INR', 'IDR', 'EUR', 'USD', 'SAR', 'THB', 'MXN', 'PHP'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">User Profile</label>
          <select className="form-select" value={form.user_id} onChange={update('user_id')}>
            <option value="user_01">user_01 – Priya Sharma (INR)</option>
            <option value="user_04">user_04 – Budi Santoso (IDR)</option>
            <option value="user_08">user_08 – Lena Müller (EUR)</option>
            <option value="user_16">user_16 – Alex Chen (USD)</option>
            <option value="user_22">user_22 – Fatima Al-Hassan (SAR)</option>
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div className="form-group">
            <label className="form-label">Request Date</label>
            <input className="form-input" type="date" value={form.date} onChange={update('date')} />
          </div>
          <div className="form-group">
            <label className="form-label">Deadline</label>
            <input className="form-input" type="date" value={form.deadline} onChange={update('deadline')} />
          </div>
        </div>

        <button className="btn btn-primary" onClick={simulate} disabled={loading || !form.amount || !form.item}>
          {loading ? '⏳  Analyzing...' : '🔍  Check Affordability'}
        </button>
      </div>

      {/* Result */}
      <div>
        {loading && (
          <div className="card">
            <div className="loading-overlay">
              <div className="spinner" />
              <div>Running financial analysis...</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Building cash-flow forecast · Simulating 6 strategies</div>
            </div>
          </div>
        )}
        {!loading && result && <DecisionCard decision={result} />}
        {!loading && !result && (
          <div className="card empty-state">
            <div className="empty-icon">💡</div>
            <div className="empty-title">Enter a purchase request</div>
            <div className="empty-desc">Fill in the form and click "Check Affordability" to get an instant AI-powered decision.</div>
          </div>
        )}
      </div>
    </div>
  );
}
