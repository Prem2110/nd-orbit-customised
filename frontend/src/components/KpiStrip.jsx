const s = {
  wrap: {
    background: 'linear-gradient(135deg, #1a3068 0%, #1e4db7 50%, #2563eb 100%)',
    borderRadius: 14, padding: '0 24px',
    marginBottom: 20, position: 'relative', overflow: 'hidden',
  },
  glow: {
    position: 'absolute', inset: 0,
    background: 'radial-gradient(ellipse at 80% 50%, rgba(96,165,250,0.15) 0%, transparent 60%)',
    pointerEvents: 'none',
  },
  row: { display: 'grid', padding: '18px 0' },
  item: {
    padding: '0 20px 0 0',
    borderRight: '1px solid rgba(255,255,255,0.12)',
    position: 'relative',
  },
  val: { fontSize: 26, fontWeight: 600, color: 'white', letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 5 },
  label: { fontSize: 11, color: 'rgba(255,255,255,0.5)', letterSpacing: '0.02em' },
  dot: { width: 6, height: 6, borderRadius: '50%', display: 'inline-block', marginRight: 5, verticalAlign: 'middle' },
};

function Dot({ color }) {
  return <span style={{ ...s.dot, background: color }} />;
}

function Item({ val, label, dotColor, valColor, unit }) {
  return (
    <div style={s.item}>
      <div style={{ ...s.val, color: valColor || 'white' }}>
        {val}
        {unit && <span style={{ fontSize: 14, fontWeight: 400 }}>{unit}</span>}
      </div>
      <div style={s.label}><Dot color={dotColor} />{label}</div>
    </div>
  );
}

export default function KpiStrip({ kpis }) {
  if (!kpis) return null;

  return (
    <div style={s.wrap}>
      <div style={s.glow} />
      <div style={{ ...s.row, gridTemplateColumns: 'repeat(5, 1fr)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <Item val={kpis.in_progress}    label="In Progress"      dotColor="#60a5fa" />
        <Item val={kpis.total_incidents} label="Total Incidents"  dotColor="#c4b5fd" />
        <Item val={kpis.pending_approval} label="Pending Approval" dotColor="#fcd34d" />
        <Item val={kpis.fix_failed}      label="Fix Failed"       dotColor="#fca5a5" valColor="#fca5a5" />
        <Item val={kpis.auto_fixed}      label="Auto Fixed"       dotColor="#86efac" valColor="#86efac" />
      </div>
      <div style={{ ...s.row, gridTemplateColumns: 'repeat(4, 1fr)' }}>
        <Item val={kpis.failed_messages}         label="Failed Messages"    dotColor="#fca5a5" valColor="#fca5a5" />
        <Item val={kpis.auto_fix_rate}           label="Auto Fix Rate"      dotColor="#86efac" valColor="#86efac" unit="%" />
        <Item val={kpis.avg_resolution_minutes}  label="Avg Resolution Time" dotColor="#fcd34d" valColor="#fcd34d" unit="m" />
        <Item val={kpis.rca_coverage}            label="RCA Coverage"       dotColor="#60a5fa" unit="%" />
      </div>
    </div>
  );
}
