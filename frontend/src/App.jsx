import { useState } from 'react';
import { OverviewPage, DecisionsPage, FinancialTwinPage, NewRequestPage } from './pages';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');

  const navItems = [
    { id: 'overview', label: 'Overview', icon: '📊', badge: 'Metrics' },
    { id: 'decisions', label: 'Decisions', icon: '📋', badge: '275' },
    { id: 'twin', label: 'Financial Twin', icon: '👤', badge: 'Forecast' },
    { id: 'new_request', label: 'New Request', icon: '➕', badge: 'Simulate' },
  ];

  return (
    <div className="app-shell">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="logo-icon">💳</div>
          <div>
            <span className="logo-text">AffordAI</span>{' '}
            <span className="logo-sub">Autonomous Financial Affordability Agent</span>
          </div>
        </div>

        <div className="topbar-right">
          <div className="accuracy-pill">
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#4ade80', marginRight: 6, boxShadow: '0 0 6px #4ade80' }}></span>
            96% Method • 96% Status (95.2% Overall)
          </div>
          <a
            href="https://github.com/siddhihingne12/AffordAI"
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.82rem',
              color: 'var(--text-secondary)',
              textDecoration: 'none',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              background: 'var(--bg-glass)',
              transition: 'all 0.2s',
            }}
          >
            <span>GitHub</span>
            <span style={{ fontSize: '0.75rem' }}>↗</span>
          </a>
        </div>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-section-label">Navigation</div>
        {navItems.map((item) => (
          <div
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span style={{ flex: 1 }}>{item.label}</span>
            {item.badge && (
              <span
                style={{
                  fontSize: '0.7rem',
                  padding: '2px 7px',
                  borderRadius: 12,
                  background:
                    activeTab === item.id
                      ? 'rgba(96,165,250,0.2)'
                      : 'rgba(255,255,255,0.06)',
                  color:
                    activeTab === item.id
                      ? 'var(--accent-blue)'
                      : 'var(--text-muted)',
                  fontWeight: 600,
                }}
              >
                {item.badge}
              </span>
            )}
          </div>
        ))}

        <div style={{ marginTop: 'auto', paddingTop: 20 }}>
          <div className="sidebar-section-label">Engine Info</div>
          <div
            style={{
              padding: '12px 14px',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)',
              fontSize: '0.78rem',
              color: 'var(--text-muted)',
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Engine:</span>
              <strong style={{ color: 'var(--accent-cyan)' }}>Deterministic + LLM</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Latency:</span>
              <strong style={{ color: '#4ade80' }}>~15ms / req</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Batch Output:</span>
              <strong style={{ color: 'var(--text-primary)' }}>275 / 275</strong>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === 'overview' && <OverviewPage />}
        {activeTab === 'decisions' && <DecisionsPage />}
        {activeTab === 'twin' && <FinancialTwinPage />}
        {activeTab === 'new_request' && <NewRequestPage />}
      </main>
    </div>
  );
}
