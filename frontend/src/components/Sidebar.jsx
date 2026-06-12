import {
  IconTopologyStar3, IconLayoutDashboard, IconEye, IconGitBranch,
  IconTicket, IconPuzzle, IconDatabase, IconSettings, IconLogout,
} from '@tabler/icons-react';

const NAV = [
  { section: 'Monitor' },
  { icon: IconLayoutDashboard, label: 'Dashboard', active: true },
  { icon: IconEye,            label: 'Observability', placeholder: true },
  { icon: IconGitBranch,      label: 'Pipeline',       placeholder: true },
  { section: 'Manage' },
  { icon: IconTicket,   label: 'Incidents',   placeholder: true },
  { icon: IconPuzzle,   label: 'Scenarios',   placeholder: true },
  { icon: IconDatabase, label: 'Master Data', placeholder: true },
  { section: 'System' },
  { icon: IconSettings, label: 'Settings', placeholder: true },
];

const styles = {
  sidebar: {
    width: 'var(--sidebar-w)',
    background: 'linear-gradient(180deg, var(--navy-900) 0%, #0b1a3a 100%)',
    display: 'flex', flexDirection: 'column', flexShrink: 0,
  },
  logo: {
    padding: '20px 18px 16px',
    borderBottom: '1px solid rgba(255,255,255,0.07)',
    display: 'flex', alignItems: 'center', gap: 10,
  },
  logoIcon: {
    width: 32, height: 32, background: 'var(--accent-blue)',
    borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
    color: 'white',
  },
  logoName: { fontSize: 14, fontWeight: 600, color: 'white', letterSpacing: '-0.01em' },
  logoSub: { fontSize: 10, color: 'rgba(255,255,255,0.45)', letterSpacing: '0.04em' },
  nav: { padding: '12px 0', flex: 1 },
  section: {
    fontSize: 9, fontWeight: 600, letterSpacing: '0.1em',
    color: 'rgba(255,255,255,0.25)', padding: '12px 18px 4px', textTransform: 'uppercase',
  },
  footer: {
    padding: '14px 18px',
    borderTop: '1px solid rgba(255,255,255,0.07)',
    display: 'flex', alignItems: 'center', gap: 8,
  },
  avatar: {
    width: 28, height: 28, borderRadius: '50%',
    background: 'var(--navy-600)', display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 11, fontWeight: 600, color: 'var(--blue-300)',
    border: '1px solid rgba(255,255,255,0.12)',
  },
  userName: { fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.75)' },
  userRole: { fontSize: 10, color: 'rgba(255,255,255,0.35)' },
};

function navItemStyle(active) {
  return {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '9px 18px',
    fontSize: 13, fontWeight: active ? 500 : 400,
    color: active ? 'white' : 'rgba(255,255,255,0.5)',
    cursor: 'pointer',
    borderLeft: `2px solid ${active ? 'var(--accent-blue)' : 'transparent'}`,
    background: active ? 'rgba(79,142,247,0.15)' : 'transparent',
    userSelect: 'none',
    transition: 'all 0.15s',
  };
}

export default function Sidebar() {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        <div style={styles.logoIcon}>
          <IconTopologyStar3 size={18} />
        </div>
        <div>
          <div style={styles.logoName}>Orbit</div>
          <div style={styles.logoSub}>Integration Suite</div>
        </div>
      </div>

      <nav style={styles.nav}>
        {NAV.map((item, i) =>
          item.section ? (
            <div key={i} style={styles.section}>{item.section}</div>
          ) : (
            <div key={i} style={navItemStyle(item.active)} title={item.placeholder ? 'Coming soon' : undefined}>
              <item.icon size={16} />
              {item.label}
            </div>
          )
        )}
      </nav>

      <div style={styles.footer}>
        <div style={styles.avatar}>SB</div>
        <div style={{ flex: 1 }}>
          <div style={styles.userName}>Sameel Baker</div>
          <div style={styles.userRole}>Admin</div>
        </div>
        <IconLogout size={14} style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer' }} />
      </div>
    </aside>
  );
}
