import { useState } from 'react';
import {
  IconChevronDown, IconChevronRight,
  IconFileDollar, IconUserPlus, IconReceipt, IconTableExport,
  IconActivity, IconBuilding, IconCreditCard, IconIdBadge, IconSettings,
} from '@tabler/icons-react';

const ICON_MAP = {
  'file-dollar':   IconFileDollar,
  'user-plus':     IconUserPlus,
  'receipt':       IconReceipt,
  'table-export':  IconTableExport,
  'building':      IconBuilding,
  'credit-card':   IconCreditCard,
  'id-badge':      IconIdBadge,
  'settings':      IconSettings,
  'activity':      IconActivity,
};

const STATUS_PILL = {
  error:   { background: '#ef4444', boxShadow: '0 0 0 3px rgba(239,68,68,0.18)' },
  warning: { background: '#f59e0b', boxShadow: '0 0 0 3px rgba(245,158,11,0.18)' },
  success: { background: '#22c55e', boxShadow: '0 0 0 3px rgba(34,197,94,0.18)' },
};

const TAG_STYLE = {
  error:   { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' },
  warning: { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' },
  success: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' },
};

const SI_STYLE = {
  error:   { background: '#fef2f2', color: '#b91c1c' },
  warning: { background: '#fffbeb', color: '#92400e' },
  success: { background: '#f0fdf4', color: '#166534' },
};

function Tag({ status, children }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 5,
      letterSpacing: '0.02em', ...TAG_STYLE[status] || TAG_STYLE.success,
    }}>
      {children}
    </span>
  );
}

function tagLabel(g) {
  if (g.error_count > 0) return `${g.error_count} error${g.error_count > 1 ? 's' : ''}`;
  if (g.warning_count > 0) return `${g.warning_count} warning${g.warning_count > 1 ? 's' : ''}`;
  return 'All healthy';
}

function ScenarioRow({ scenario, onOpen }) {
  const Icon = ICON_MAP[scenario.icon] || IconActivity;
  const siStyle = SI_STYLE[scenario.status] || SI_STYLE.success;
  const tagText = scenario.status === 'error' ? 'Failed' : scenario.status === 'warning' ? 'Warning' : 'Success';

  return (
    <div
      onClick={() => onOpen(scenario.id)}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px 10px 36px',
        borderBottom: '1px solid var(--border)',
        cursor: 'pointer', transition: 'background 0.1s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = '#f1f5fb'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <div style={{
        width: 26, height: 26, borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, ...siStyle,
      }}>
        <Icon size={13} />
      </div>
      <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', flex: 1 }}>
        {scenario.name}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{scenario.time}</div>
      <Tag status={scenario.status}>{tagText}</Tag>
      <IconChevronRight size={12} style={{ color: '#94a3b8' }} />
    </div>
  );
}

function ProcessRow({ group, onOpenScenario }) {
  const [open, setOpen] = useState(false);
  const pillStyle = STATUS_PILL[group.status] || STATUS_PILL.success;

  return (
    <div style={{ background: 'white', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden', marginBottom: 10 }}>
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '12px 16px', cursor: 'pointer', transition: 'background 0.12s', userSelect: 'none',
        }}
        onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
      >
        <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, ...pillStyle }} />
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>{group.name}</div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{group.route}</div>
        <Tag status={group.status}>{tagLabel(group)}</Tag>
        <IconChevronDown
          size={14}
          style={{ color: 'var(--text-muted)', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'none' }}
        />
      </div>

      {open && (
        <div style={{ borderTop: '1px solid var(--border)', background: '#fafbfc' }}>
          {group.scenarios.length === 0 ? (
            <div style={{ padding: '12px 36px', fontSize: 12, color: 'var(--text-muted)' }}>No scenarios found</div>
          ) : (
            group.scenarios.map((sc, i) => (
              <ScenarioRow
                key={sc.id}
                scenario={sc}
                onOpen={onOpenScenario}
                style={i === group.scenarios.length - 1 ? { borderBottom: 'none' } : {}}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function ProcessHealth({ groups, onOpenScenario }) {
  if (!groups || groups.length === 0) {
    return (
      <div style={{
        background: 'white', border: '1px solid var(--border)', borderRadius: 12,
        padding: '40px 24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13,
      }}>
        No integration data yet. Click <strong>Sync Data</strong> to fetch the last 3 months of CPI logs.
      </div>
    );
  }

  return (
    <div>
      {groups.map(g => (
        <ProcessRow key={g.id} group={g} onOpenScenario={onOpenScenario} />
      ))}
    </div>
  );
}
