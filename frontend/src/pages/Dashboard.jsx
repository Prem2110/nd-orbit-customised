import { useState, useEffect, useCallback } from 'react';
import Sidebar from '../components/Sidebar';
import Topbar from '../components/Topbar';
import KpiStrip from '../components/KpiStrip';
import ProcessHealth from '../components/ProcessHealth';
import DetailView from '../components/DetailView';
import { getDashboardKpis, getProcessHealth, getLogDetail, startIngestion, getIngestionStatus } from '../services/api';

const POLL_INTERVAL = 5000;

export default function Dashboard() {
  const [view, setView] = useState('overview');
  const [pageTitle, setPageTitle] = useState('Integration Error Monitor');
  const [kpis, setKpis] = useState(null);
  const [groups, setGroups] = useState([]);
  const [detail, setDetail] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState(null);
  const [error, setError] = useState(null);

  const loadDashboard = useCallback(async () => {
    try {
      const [kpiRes, phRes] = await Promise.all([getDashboardKpis(), getProcessHealth()]);
      setKpis(kpiRes.data);
      setGroups(phRes.data);
      setError(null);
    } catch (e) {
      setError('Failed to load dashboard data');
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (!syncing) return;
    const id = setInterval(async () => {
      try {
        const res = await getIngestionStatus();
        setSyncStatus(res.data);
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          setSyncing(false);
          clearInterval(id);
          await loadDashboard();
        }
      } catch (_) {}
    }, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [syncing, loadDashboard]);

  const handleSync = async () => {
    if (syncing) return;
    try {
      await startIngestion();
      setSyncing(true);
      setSyncStatus({ status: 'running', total_fetched: 0, total_classified: 0 });
    } catch (e) {
      if (e.response?.status === 409) {
        setSyncing(true);
      } else {
        setError('Failed to start sync: ' + (e.response?.data?.detail || e.message));
      }
    }
  };

  const handleOpenScenario = async (id) => {
    try {
      const res = await getLogDetail(id);
      setDetail(res.data);
      setPageTitle(res.data.title);
      setView('detail');
      document.getElementById('content-area')?.scrollTo(0, 0);
    } catch (e) {
      setError('Failed to load log detail');
    }
  };

  const handleBack = () => {
    setView('overview');
    setPageTitle('Integration Error Monitor');
    setDetail(null);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Topbar title={pageTitle} onSync={handleSync} syncing={syncing} />

        {/* Sync progress banner */}
        {syncing && syncStatus && (
          <div style={{
            padding: '8px 28px', background: '#eff6ff', borderBottom: '1px solid #bfdbfe',
            fontSize: 12, color: '#1d4ed8', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#3b82f6', display: 'inline-block', animation: 'pulse 1.5s infinite' }} />
            Syncing CPI data…&nbsp;
            {syncStatus.total_fetched > 0 && <span>Fetched {syncStatus.total_fetched} logs</span>}
            {syncStatus.total_classified > 0 && <span>· Classified {syncStatus.total_classified}</span>}
          </div>
        )}

        {error && (
          <div style={{
            padding: '8px 28px', background: '#fff5f5', borderBottom: '1px solid #fecaca',
            fontSize: 12, color: '#b91c1c',
          }}>
            {error}
          </div>
        )}

        <div id="content-area" style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
          {view === 'overview' && (
            <>
              <KpiStrip kpis={kpis} />
              <div style={{
                fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)',
                marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em',
              }}>
                Process health
              </div>
              <ProcessHealth groups={groups} onOpenScenario={handleOpenScenario} />
            </>
          )}

          {view === 'detail' && (
            <DetailView detail={detail} onBack={handleBack} />
          )}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
