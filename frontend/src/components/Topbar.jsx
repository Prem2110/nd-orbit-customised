import { IconCircleFilled, IconRefresh } from '@tabler/icons-react';

const badge = (label, color, bg, textColor) => ({
  label, color, bg, textColor,
});

const BADGES = [
  badge('SAP CPI',   '#22c55e', '#e0edff', '#185aac'),
  badge('Cloud ALM', '#3b82f6', '#e0f2fe', '#0369a1'),
  badge('EIH',       '#22c55e', '#f0fdf4', '#166534'),
];

const s = {
  topbar: {
    padding: '14px 28px',
    background: 'white',
    borderBottom: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    flexShrink: 0,
  },
  title: { fontSize: 17, fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.02em' },
  right: { display: 'flex', alignItems: 'center', gap: 10 },
  badge: {
    padding: '4px 10px', borderRadius: 6,
    fontSize: 11, fontWeight: 600,
    display: 'flex', alignItems: 'center', gap: 5,
  },
  syncBtn: {
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '5px 12px', borderRadius: 7,
    fontSize: 12, fontWeight: 500,
    background: '#eff6ff', color: '#1d4ed8',
    border: '1px solid #bfdbfe',
    cursor: 'pointer', fontFamily: 'var(--font)',
    transition: 'all 0.12s',
  },
};

export default function Topbar({ title = 'Integration Error Monitor', onSync, syncing }) {
  return (
    <div style={s.topbar}>
      <div style={s.title}>{title}</div>
      <div style={s.right}>
        {BADGES.map((b) => (
          <div key={b.label} style={{ ...s.badge, background: b.bg, color: b.textColor }}>
            <IconCircleFilled size={8} style={{ color: b.color }} />
            {b.label}
          </div>
        ))}
        <button style={s.syncBtn} onClick={onSync} disabled={syncing}>
          <IconRefresh size={13} style={{ animation: syncing ? 'spin 1s linear infinite' : 'none' }} />
          {syncing ? 'Syncing…' : 'Sync Data'}
        </button>
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
