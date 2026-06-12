import { IconArrowLeft, IconChevronRight, IconHash, IconClock, IconArrowRight, IconAlertTriangle, IconBulb, IconX, IconCheck } from '@tabler/icons-react';

const TAG = {
  error:   { background: '#fef2f2', color: '#b91c1c', border: '1px solid #fecaca' },
  warning: { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' },
  success: { background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' },
};

const TL_DOT = {
  ok:    '#22c55e',
  error: '#ef4444',
  warn:  '#f59e0b',
  idle:  '#cbd5e1',
};

const FLOW_NODE = {
  ok:    { background: '#f0fdf4', color: '#16a34a', borderColor: '#bbf7d0' },
  error: { background: '#fef2f2', color: '#dc2626', borderColor: '#fecaca' },
  idle:  { background: '#f8fafc', color: '#94a3b8', borderColor: '#e2e8f0' },
};

function Tag({ status }) {
  const text = status === 'error' ? 'Error' : status === 'warning' ? 'Warning' : 'Success';
  return (
    <span style={{ fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 5, letterSpacing: '0.02em', ...TAG[status] || TAG.success }}>
      {text}
    </span>
  );
}

function FlowTrack({ steps }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', overflowX: 'auto', paddingBottom: 2 }}>
      {steps.map((step, i) => {
        const ns = FLOW_NODE[step.status] || FLOW_NODE.idle;
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5, minWidth: 88 }}>
              <div style={{
                width: 52, height: 38, borderRadius: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 600, border: `1px solid ${ns.borderColor}`,
                background: ns.background, color: ns.color,
              }}>
                {step.status === 'error' ? <IconX size={13} /> : step.status === 'idle' ? <span style={{ fontSize: 12, color: '#94a3b8' }}>—</span> : <IconCheck size={12} />}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.3 }}>
                <strong style={{ display: 'block', fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>{step.label}</strong>
                {step.step}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div style={{ fontSize: 14, color: '#cbd5e1', margin: '0 -2px 14px', flexShrink: 0 }}>›</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Timeline({ events }) {
  return (
    <div>
      {events.map((ev, i) => (
        <div key={i} style={{
          display: 'flex', gap: 12, padding: '9px 0',
          borderBottom: i < events.length - 1 ? '1px solid var(--border)' : 'none',
          alignItems: 'flex-start',
        }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', marginTop: 4, flexShrink: 0, background: TL_DOT[ev.status] || TL_DOT.idle }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{ev.event}</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{ev.description}</div>
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap', paddingTop: 3 }}>{ev.time}</div>
        </div>
      ))}
    </div>
  );
}

const card = {
  background: 'white', border: '1px solid var(--border)', borderRadius: 12,
  padding: '16px 20px', marginBottom: 14,
};

const secLabel = {
  fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
  color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12,
};

export default function DetailView({ detail, onBack }) {
  if (!detail) return null;

  return (
    <div>
      {/* Nav */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <button
          onClick={onBack}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '6px 12px', fontSize: 12, fontWeight: 500,
            color: 'var(--text-secondary)', background: 'white',
            border: '1px solid var(--border)', borderRadius: 7,
            cursor: 'pointer', fontFamily: 'var(--font)', transition: 'all 0.12s',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-blue)'; e.currentTarget.style.color = 'var(--accent-blue)'; e.currentTarget.style.background = '#eff6ff'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.background = 'white'; }}
        >
          <IconArrowLeft size={13} /> Back
        </button>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 5 }}>
          <span>Dashboard</span>
          <IconChevronRight size={10} />
          <span>{detail.process}</span>
          <IconChevronRight size={10} />
          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{detail.title}</span>
        </div>
      </div>

      {/* Detail card */}
      <div style={card}>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>{detail.title}</div>
        <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
          {[
            { icon: IconHash, text: detail.incident_id },
            { icon: IconClock, text: detail.time },
            { icon: IconArrowRight, text: `${detail.source} → ${detail.destination}` },
          ].map(({ icon: Icon, text }, i) => (
            <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: 'var(--text-secondary)' }}>
              <Icon size={13} style={{ color: 'var(--text-muted)' }} />
              {text}
            </span>
          ))}
          <Tag status={detail.status} />
        </div>
      </div>

      {/* Flow */}
      {detail.flow && detail.flow.length > 0 && (
        <div style={card}>
          <div style={secLabel}>Integration flow</div>
          <FlowTrack steps={detail.flow} />
        </div>
      )}

      {/* Timeline */}
      {detail.timeline && detail.timeline.length > 0 && (
        <div style={card}>
          <div style={secLabel}>Execution timeline</div>
          <Timeline events={detail.timeline} />
        </div>
      )}

      {/* Error box */}
      {detail.error && detail.error.heading && (
        <div style={{ background: '#fff5f5', border: '1px solid #fecaca', borderRadius: 10, padding: '14px 16px', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#b91c1c', marginBottom: 8 }}>
            <IconAlertTriangle size={14} />
            {detail.error.heading}
          </div>
          <pre style={{
            fontFamily: 'var(--mono)', fontSize: 11, color: '#9b1c1c',
            background: 'rgba(220,38,38,0.06)', padding: '10px 12px',
            borderRadius: 6, lineHeight: 1.7, whiteSpace: 'pre-wrap',
          }}>
            {detail.error.code}
          </pre>
        </div>
      )}

      {/* Recommendations */}
      {detail.recommendations && detail.recommendations.length > 0 && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 10, padding: '14px 16px', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: '#1d4ed8', marginBottom: 8 }}>
            <IconBulb size={14} />
            AI-suggested actions
          </div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
            {detail.recommendations.map((r, i) => (
              <li key={i} style={{ fontSize: 12, color: '#1e40af', display: 'flex', alignItems: 'flex-start', gap: 6, lineHeight: 1.5 }}>
                <span style={{ flexShrink: 0 }}>→</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
