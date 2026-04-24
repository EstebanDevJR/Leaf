<script lang="ts">
  import {
    deleteTransaction, dismissAlert, formatCOP,
    getAlerts, getBudgets, getStats, getTransactions,
    getInvestigadorStatus, toggleInvestigador,
    getDashboardCashflow, getEmergencyFund,
    CATEGORY_COLORS,
  } from '$lib/api';
  import type { AlertItem, Budget, Transaction, CashflowPoint, EmergencyFund } from '$lib/api';
  import Chat from '$lib/components/Chat.svelte';
  import TransactionDrawer from '$lib/components/TransactionDrawer.svelte';
  import SavingsGoals from '$lib/components/SavingsGoals.svelte';
  import ImportExport from '$lib/components/ImportExport.svelte';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import AlertBanner from '$lib/components/AlertBanner.svelte';
  import CashflowChart from '$lib/components/CashflowChart.svelte';
  import WhatIfSimulator from '$lib/components/WhatIfSimulator.svelte';
  import InvestmentRecommendations from '$lib/components/InvestmentRecommendations.svelte';
  import CDTComparator from '$lib/components/CDTComparator.svelte';
  import SubscriptionsList from '$lib/components/SubscriptionsList.svelte';
  import ConceptExplainer from '$lib/components/ConceptExplainer.svelte';
  import HealthReport from '$lib/components/HealthReport.svelte';
  import { onMount } from 'svelte';
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  let transactions: Transaction[] = $state(data.transactions);
  let stats = $state(data.stats);
  let budgets: Budget[] = $state(data.budgets ?? []);
  let alerts: AlertItem[] = $state(data.alerts ?? []);
  let loadingTx = $state(false);

  let chatOpen = $state(false);
  let drawerOpen = $state(false);
  let sidePanel: 'none' | 'goals' | 'import' | 'profiles' | 'whatif' | 'investments' | 'cdt' | 'subscriptions' | 'concepts' | 'health' = $state('none');
  let investigadorEnabled = $state(true);
  let alertsOpen = $state(false);
  let activeNav = $state('dashboard');

  // Cashflow: weekly (current month) vs 12-month historical
  // eslint-disable-next-line prefer-const
  let cashflowMode = $state<'weekly' | 'monthly'>('weekly');
  let historicalCashflow = $state<CashflowPoint[]>([]);
  let loadingCashflow = $state(false);

  // Emergency fund
  let emergencyFund = $state<EmergencyFund | null>(null);

  const activeAlerts = $derived(alerts.filter(a => !a.dismissed));
  const urgentCount = $derived(activeAlerts.filter(a => a.severity === 'urgent').length);
  const badgeCount = $derived(activeAlerts.length);
  const savingsAmount = $derived(Math.max(0, (stats?.total_income ?? 0) - (stats?.total_expenses ?? 0)));

  // ── Cashflow data ─────────────────────────────────────────────────────────
  const weeklyCashflow = $derived(buildWeeklyCashflow(transactions));

  function buildWeeklyCashflow(txs: Transaction[]) {
    const now = new Date();
    const weeks = [
      { label: 'Sem 1', income: 0, expenses: 0 },
      { label: 'Sem 2', income: 0, expenses: 0 },
      { label: 'Sem 3', income: 0, expenses: 0 },
      { label: 'Sem 4', income: 0, expenses: 0 },
    ];
    for (const tx of txs) {
      const d = new Date(tx.date);
      if (d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear()) continue;
      const week = Math.min(Math.floor((d.getDate() - 1) / 7), 3);
      if (tx.type === 'income') weeks[week].income += tx.amount;
      else weeks[week].expenses += tx.amount;
    }
    return weeks;
  }

  const chartData = $derived(cashflowMode === 'monthly' ? historicalCashflow : weeklyCashflow);

  async function switchCashflow(mode: 'weekly' | 'monthly') {
    cashflowMode = mode;
    if (mode === 'monthly' && historicalCashflow.length === 0) {
      loadingCashflow = true;
      try {
        historicalCashflow = await getDashboardCashflow(12);
      } finally {
        loadingCashflow = false;
      }
    }
  }

  // ── Donut segments ────────────────────────────────────────────────────────
  const R = 52, SW = 14, C = 2 * Math.PI * R;

  const segments = $derived(stats ? buildSegments(stats.expenses_by_category ?? {}) : []);

  function buildSegments(byCategory: Record<string, number>) {
    const entries = Object.entries(byCategory)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    const total = entries.reduce((s, [, v]) => s + v, 0);
    if (!total) return [];
    let cum = 0;
    return entries.map(([name, amount]) => {
      const pct = amount / total;
      const dashLength = pct * C;
      const seg = {
        name, amount, pct: pct * 100,
        color: CATEGORY_COLORS[name] ?? '#94a3b8',
        dashLength,
        dashOffset: -cum,
      };
      cum += dashLength;
      return seg;
    });
  }

  // ── Emergency fund helpers ────────────────────────────────────────────────
  const efStatusColor = $derived(
    emergencyFund?.status === 'complete' ? '#4ade80'
      : emergencyFund?.status === 'warning' ? '#fbbf24'
      : '#f87171'
  );

  // ── Month label ───────────────────────────────────────────────────────────
  const monthName = new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });

  // ── Actions ───────────────────────────────────────────────────────────────
  onMount(async () => {
    try {
      const [status, ef] = await Promise.all([
        getInvestigadorStatus().catch(() => ({ enabled: true })),
        getEmergencyFund().catch(() => null),
      ]);
      investigadorEnabled = status.enabled;
      emergencyFund = ef;
    } catch { /* silent */ }
  });

  async function handleToggleInvestigador() {
    investigadorEnabled = !investigadorEnabled;
    await toggleInvestigador(investigadorEnabled);
  }

  async function refresh() {
    loadingTx = true;
    try {
      [transactions, stats, budgets, alerts] = await Promise.all([
        getTransactions(20),
        getStats(),
        getBudgets(),
        getAlerts(),
      ]);
      emergencyFund = await getEmergencyFund().catch(() => null);
    } finally {
      loadingTx = false;
    }
  }

  async function handleDelete(e: CustomEvent<number>) {
    await deleteTransaction(e.detail);
    await refresh();
  }

  function handleAlertDismissed(e: CustomEvent<number>) {
    alerts = alerts.map(a => a.id === e.detail ? { ...a, dismissed: true } : a);
  }
</script>

<div class="app">

  <!-- ════════════════════════════════ SIDEBAR ════════════════════════════════ -->
  <aside class="sidebar">
    <div class="sidebar-logo">
      <span class="logo-leaf">🌿</span>
      <span class="logo-text">Leaf</span>
    </div>

    <nav class="sidebar-nav">
      {#each [
        { id: 'dashboard',      icon: '⊞', label: 'Leaf' },
        { id: 'transacciones',  icon: '⊙', label: 'Transacciones' },
        { id: 'metas',          icon: '⊕', label: 'Metas' },
        { id: 'presupuestos',   icon: '⊡', label: 'Presupuestos' },
        { id: 'investigador',   icon: '⊘', label: 'Investigador' },
        { id: 'voz',            icon: '◎', label: 'Voz' },
      ] as item}
        <button
          class="nav-item"
          class:active={activeNav === item.id}
          on:click={() => {
            activeNav = item.id;
            if      (item.id === 'transacciones') { drawerOpen = true; sidePanel = 'none'; }
            else if (item.id === 'metas')         { sidePanel = 'goals'; drawerOpen = false; }
            else if (item.id === 'presupuestos')  { drawerOpen = true; sidePanel = 'none'; }
            else if (item.id === 'voz')           { sidePanel = 'profiles'; drawerOpen = false; }
            else                                  { sidePanel = 'none'; drawerOpen = false; }
          }}
        >
          <span class="nav-icon">{item.icon}</span>
          <span class="nav-label">{item.label}</span>
        </button>
      {/each}
    </nav>

    <div class="sidebar-bottom">
      <div class="sidebar-deco">🌿</div>
      <button class="nav-item" on:click={() => { sidePanel = 'import'; activeNav = ''; }}>
        <span class="nav-icon">↕</span>
        <span class="nav-label">Importar</span>
      </button>
      <button class="nav-item" on:click={() => { sidePanel = 'profiles'; activeNav = ''; }}>
        <span class="nav-icon">⊛</span>
        <span class="nav-label">Perfiles</span>
      </button>
    </div>
  </aside>

  <!-- ═══════════════════════════ MAIN CONTENT ════════════════════════════════ -->
  <div class="main-content">

    <!-- Header -->
    <header class="dash-header">
      <h1 class="dash-title">{monthName}</h1>
      <div class="header-right">
        <div class="search-bar">🔍 <span>Buscar...</span></div>
        {#if badgeCount > 0}
          <button
            class="icon-btn bell-btn"
            class:urgent={urgentCount > 0}
            on:click={() => alertsOpen = !alertsOpen}
            title="Alertas"
          >
            🔔
            <span class="bell-badge">{badgeCount}</span>
          </button>
        {:else}
          <button class="icon-btn" title="Sin alertas">🔔</button>
        {/if}
        <div class="avatar-wrap">
          <div class="avatar">L</div>
        </div>
      </div>
    </header>

    {#if alertsOpen && activeAlerts.length > 0}
      <div class="alerts-bar">
        <AlertBanner alerts={activeAlerts} on:dismissed={handleAlertDismissed} />
      </div>
    {/if}

    <!-- Dashboard -->
    <div class="dashboard">

      <!-- ── Row 1: KPI cards ── -->
      <div class="kpi-row">

        <div class="kpi-card kpi-primary">
          <div class="kpi-inner">
            <div>
              <div class="kpi-label">Balance Actual COP</div>
              <div class="kpi-value" class:neg={(stats?.balance ?? 0) < 0}>
                {formatCOP(stats?.balance ?? 0)}
              </div>
            </div>
            <span class="flag">🇨🇴</span>
          </div>
          <div class="kpi-glow"></div>
        </div>

        <div class="kpi-card">
          <div class="kpi-inner">
            <div>
              <div class="kpi-label">Ingresos del mes</div>
              <div class="kpi-value">{formatCOP(stats?.total_income ?? 0)}</div>
              <div class="kpi-sub positive">💰 {savingsAmount > 0 ? formatCOP(savingsAmount) + ' ahorrados' : 'sin ahorro este mes'}</div>
            </div>
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-inner">
            <div>
              <div class="kpi-label">Gastos del mes</div>
              <div class="kpi-value neg-light">{formatCOP(stats?.total_expenses ?? 0)}</div>
              <div class="kpi-sub">
                {stats && stats.total_income > 0
                  ? Math.round(stats.total_expenses / stats.total_income * 100) + '% del ingreso'
                  : 'sin ingresos'}
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- ── Row 2: Chart + Donut ── -->
      <div class="mid-row">

        <!-- Cashflow chart -->
        <div class="card chart-card">
          <div class="card-header">
            <span class="card-title">Cash flow</span>
            <div class="chart-tabs">
              <button
                class="chart-tab"
                class:active={cashflowMode === 'weekly'}
                on:click={() => switchCashflow('weekly')}
              >Este mes</button>
              <button
                class="chart-tab"
                class:active={cashflowMode === 'monthly'}
                on:click={() => switchCashflow('monthly')}
              >12 meses</button>
            </div>
          </div>
          <div class="chart-area">
            {#if loadingCashflow}
              <div class="chart-loading">Cargando...</div>
            {:else}
              <CashflowChart data={chartData} showIncome={cashflowMode === 'monthly'} />
            {/if}
          </div>
          <div class="hablar-wrap">
            <button class="hablar-btn" on:click={() => chatOpen = true}>
              <span class="hablar-icon">🎙</span>
              Hablar con Leaf
            </button>
          </div>
        </div>

        <!-- Donut chart -->
        <div class="card donut-card">
          <div class="card-header">
            <span class="card-title">Gastos</span>
            <span style="font-size:18px">🌿</span>
          </div>

          {#if segments.length > 0}
            <div class="donut-center-wrap">
              <svg viewBox="0 0 160 160" class="donut-svg">
                <circle cx="80" cy="80" r={R} fill="none" stroke="#1d221d" stroke-width={SW} />
                <g transform="rotate(-90 80 80)">
                  {#each segments as seg}
                    <circle
                      cx="80" cy="80" r={R}
                      fill="none"
                      stroke={seg.color}
                      stroke-width={SW}
                      stroke-dasharray="{seg.dashLength} {C - seg.dashLength}"
                      stroke-dashoffset={seg.dashOffset}
                    />
                  {/each}
                </g>
                <text x="80" y="72" text-anchor="middle" class="donut-num">
                  {stats?.transaction_count ?? 0}
                </text>
                <text x="80" y="90" text-anchor="middle" class="donut-sub">transacciones</text>
              </svg>
            </div>

            <div class="donut-legend">
              {#each segments.slice(0, 4) as seg}
                <div class="legend-row">
                  <span class="legend-dot" style="background:{seg.color}"></span>
                  <span class="legend-name">{seg.name}</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="no-data">Sin gastos registrados</div>
          {/if}
        </div>

      </div>

      <!-- ── Row 3: Action tiles ── -->
      <div class="tiles-row">

        <button class="tile" on:click={() => { sidePanel = 'goals'; activeNav = 'metas'; }}>
          <span class="tile-icon">🎯</span>
          <span>Metas de ahorro</span>
        </button>

        <button class="tile" on:click={() => { drawerOpen = true; activeNav = 'presupuestos'; }}>
          <span class="tile-icon">👥</span>
          <span>Presupuestos</span>
        </button>

        <div class="tile tile-inv">
          <span class="tile-icon">⚙️</span>
          <span>Investigador</span>
          <button
            class="toggle"
            class:on={investigadorEnabled}
            on:click={handleToggleInvestigador}
            title={investigadorEnabled ? 'Investigador activo' : 'Investigador inactivo'}
          >
            <span class="toggle-thumb"></span>
          </button>
        </div>

      </div>

      <!-- ── Row 4: Feature tiles ── -->
      <div class="tiles-row">

        <!-- Emergency Fund tile -->
        <button class="tile tile-ef" on:click={() => { sidePanel = 'none'; drawerOpen = false; }}>
          <div class="ef-tile-content">
            <div class="ef-tile-top">
              <span class="tile-icon">🛡️</span>
              <span>Fondo de Emergencia</span>
            </div>
            {#if emergencyFund}
              <div class="ef-progress-wrap">
                <div class="ef-bar-bg">
                  <div
                    class="ef-bar-fill"
                    style="width: {Math.min(100, emergencyFund.coverage_pct)}%; background: {efStatusColor};"
                  ></div>
                </div>
                <span class="ef-pct" style="color: {efStatusColor}">
                  {emergencyFund.coverage_months.toFixed(1)} meses · {emergencyFund.coverage_pct.toFixed(0)}%
                </span>
              </div>
            {:else}
              <span class="ef-empty">Cargando...</span>
            {/if}
          </div>
        </button>

        <!-- What-If tile -->
        <button class="tile" on:click={() => { sidePanel = 'whatif'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">🔮</span>
          <span>Simulador What-If</span>
        </button>

        <!-- Investments tile -->
        <button class="tile" on:click={() => { sidePanel = 'investments'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">📊</span>
          <span>Inversiones CDT</span>
        </button>

      </div>

      <!-- ── Row 5: 5 Ideas Top ── -->
      <div class="tiles-row tiles-5">

        <button class="tile" on:click={() => { sidePanel = 'health'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">🌿</span>
          <span>Salud financiera</span>
        </button>

        <button class="tile" on:click={() => { sidePanel = 'cdt'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">💎</span>
          <span>Comparar CDT</span>
        </button>

        <button class="tile" on:click={() => { sidePanel = 'subscriptions'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">🔄</span>
          <span>Suscripciones</span>
        </button>

        <button class="tile" on:click={() => { sidePanel = 'concepts'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">📚</span>
          <span>Diccionario</span>
        </button>

        <button class="tile" on:click={() => { sidePanel = 'whatif'; activeNav = ''; drawerOpen = false; }}>
          <span class="tile-icon">🔮</span>
          <span>What-If</span>
        </button>

      </div>

    </div>
  </div>

  <!-- ═══════════════════════════ CHAT OVERLAY ════════════════════════════════ -->
  {#if chatOpen}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div class="chat-backdrop" on:click|self={() => chatOpen = false}>
      <div class="chat-panel">
        <button class="chat-close" on:click={() => chatOpen = false}>✕ Cerrar</button>
        <Chat on:sent={refresh} />
      </div>
    </div>
  {/if}

  <!-- ══════════════════════ TRANSACTION DRAWER ═══════════════════════════════ -->
  {#if drawerOpen}
    <TransactionDrawer
      {transactions}
      {stats}
      {budgets}
      loading={loadingTx}
      on:close={() => { drawerOpen = false; activeNav = 'dashboard'; }}
      on:delete={handleDelete}
    />
  {/if}

  <!-- ═════════════════════════ SIDE PANEL ════════════════════════════════════ -->
  {#if sidePanel !== 'none'}
    <div class="side-panel" class:wide={sidePanel === 'whatif' || sidePanel === 'investments'}>
      <button class="panel-close" on:click={() => { sidePanel = 'none'; activeNav = 'dashboard'; }}>✕</button>
      {#if sidePanel === 'goals'}
        <SavingsGoals />
      {:else if sidePanel === 'import'}
        <ImportExport />
      {:else if sidePanel === 'profiles'}
        <div class="panel-section">
          <h2>Perfiles familiares</h2>
          <ProfileSwitcher />
        </div>
      {:else if sidePanel === 'whatif'}
        <WhatIfSimulator />
      {:else if sidePanel === 'investments'}
        <InvestmentRecommendations />
      {:else if sidePanel === 'cdt'}
        <CDTComparator />
      {:else if sidePanel === 'subscriptions'}
        <SubscriptionsList />
      {:else if sidePanel === 'concepts'}
        <ConceptExplainer />
      {:else if sidePanel === 'health'}
        <HealthReport />
      {/if}
    </div>
  {/if}

</div>

<style>
  /* ── App shell ── */
  .app {
    height: 100vh;
    display: flex;
    overflow: hidden;
    background: var(--bg);
  }

  /* ════════════════════ SIDEBAR ════════════════════ */
  .sidebar {
    width: 210px;
    flex-shrink: 0;
    background: #141714;
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    padding: 20px 10px 16px;
  }

  .sidebar-logo {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 4px 10px 22px;
  }

  .logo-leaf { font-size: 22px; }

  .logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 700;
    font-style: italic;
    color: #fff;
  }

  .sidebar-nav {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 9px 12px;
    border-radius: 10px;
    border: none;
    background: none;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 13px;
    cursor: pointer;
    width: 100%;
    text-align: left;
    transition: color 0.15s, background 0.15s;
  }

  .nav-item:hover { background: rgba(90,170,90,0.07); color: var(--text-mid); }
  .nav-item.active { background: var(--green-nav); color: var(--text); }

  .nav-icon { font-size: 14px; flex-shrink: 0; opacity: 0.8; }

  .sidebar-bottom {
    position: relative;
    padding-top: 14px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .sidebar-deco {
    position: absolute;
    bottom: 32px;
    left: 8px;
    font-size: 64px;
    opacity: 0.05;
    pointer-events: none;
    transform: rotate(-20deg);
    line-height: 1;
  }

  /* ════════════════════ MAIN CONTENT ════════════════════ */
  .main-content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--bg);
  }

  /* ── Header ── */
  .dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 24px 12px;
    flex-shrink: 0;
  }

  .dash-title {
    font-family: 'Inter', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    text-transform: capitalize;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 7px 16px;
    font-size: 12px;
    color: var(--text-dim);
    min-width: 150px;
    cursor: text;
  }

  .icon-btn {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    position: relative;
    font-size: 14px;
    transition: border-color 0.15s;
  }

  .icon-btn:hover { border-color: var(--border-light); }
  .icon-btn.urgent { border-color: rgba(248,113,113,0.4); }

  .bell-badge {
    position: absolute;
    top: -5px; right: -5px;
    background: var(--red);
    color: #fff;
    font-size: 9px;
    min-width: 16px;
    height: 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 3px;
  }

  .avatar-wrap {
    width: 36px; height: 36px;
    border-radius: 50%;
    border: 2px solid var(--green-dim);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: var(--green-dim);
    color: var(--green);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
  }

  .alerts-bar {
    padding: 0 24px 8px;
    flex-shrink: 0;
  }

  /* ════════════════════ DASHBOARD ════════════════════ */
  .dashboard {
    flex: 1;
    overflow-y: auto;
    padding: 4px 24px 24px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* ── KPI cards ── */
  .kpi-row {
    display: grid;
    grid-template-columns: 1.35fr 1fr 1fr;
    gap: 14px;
  }

  .kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
  }

  .kpi-inner {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    position: relative;
    z-index: 1;
  }

  .kpi-glow {
    position: absolute;
    top: 50%;
    right: -10px;
    transform: translateY(-50%);
    width: 130px;
    height: 130px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.07) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
  }

  .kpi-label {
    font-size: 11px;
    color: var(--text-mid);
    margin-bottom: 8px;
    font-weight: 400;
  }

  .kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.03em;
    line-height: 1.05;
    font-family: 'Inter', sans-serif;
  }

  .kpi-value.neg { color: var(--red); }
  .kpi-value.neg-light { color: #f87171; }
  .flag { font-size: 20px; flex-shrink: 0; margin-top: 2px; }

  .kpi-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 5px;
  }

  .kpi-sub.positive { color: #4ade80; }

  /* ── Mid row ── */
  .mid-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 14px;
    min-height: 290px;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px;
    display: flex;
    flex-direction: column;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    flex-shrink: 0;
  }

  .card-title {
    font-size: 14px;
    color: var(--text);
    font-weight: 500;
  }

  /* Chart tabs */
  .chart-tabs {
    display: flex;
    gap: 4px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
  }

  .chart-tab {
    padding: 4px 12px;
    border: none;
    border-radius: 6px;
    background: none;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .chart-tab.active {
    background: var(--surface3);
    color: var(--text);
  }

  /* Chart card */
  .chart-card { position: relative; }

  .chart-area {
    flex: 1;
    min-height: 0;
    padding-bottom: 54px;
  }

  .chart-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-size: 12px;
    color: var(--text-dim);
  }

  .hablar-wrap {
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2;
  }

  .hablar-btn {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 13px 32px;
    border-radius: 28px;
    border: none;
    background: linear-gradient(135deg, #3a6b3a 0%, #5aaa5a 100%);
    color: #e8f5e8;
    font-size: 14px;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    white-space: nowrap;
    box-shadow: 0 6px 24px rgba(74,222,128,0.2);
    transition: transform 0.18s, box-shadow 0.18s;
  }

  .hablar-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(74,222,128,0.3);
  }

  .hablar-icon { font-size: 16px; }

  /* Donut card */
  .donut-center-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
  }

  .donut-svg { width: 160px; height: 160px; }

  .donut-num {
    font-family: 'Inter', sans-serif;
    font-size: 28px;
    font-weight: 700;
    fill: var(--text);
  }

  .donut-sub {
    font-family: 'Inter', sans-serif;
    font-size: 9px;
    fill: var(--text-dim);
  }

  .donut-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    padding-top: 10px;
    flex-shrink: 0;
  }

  .legend-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: var(--text-mid);
  }

  .legend-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* ── Bottom tiles ── */
  .tiles-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 14px;
  }

  .tiles-5 {
    grid-template-columns: repeat(5, 1fr);
  }

  .tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    color: var(--text-mid);
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s, background 0.15s, color 0.15s;
  }

  .tile:hover {
    border-color: var(--border-light);
    background: var(--surface2);
    color: var(--text);
  }

  .tile-icon { font-size: 18px; flex-shrink: 0; }

  .tile-inv {
    cursor: default;
  }

  .tile-inv:hover {
    border-color: var(--border);
    background: var(--surface);
    color: var(--text-mid);
  }

  /* Emergency Fund tile */
  .tile-ef {
    flex-direction: column;
    align-items: stretch;
    padding: 14px 16px;
    gap: 8px;
    cursor: default;
  }

  .tile-ef:hover {
    border-color: var(--border-light);
  }

  .ef-tile-content {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
  }

  .ef-tile-top {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    color: var(--text-mid);
  }

  .ef-progress-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ef-bar-bg {
    height: 6px;
    background: var(--surface3);
    border-radius: 3px;
    overflow: hidden;
  }

  .ef-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease;
  }

  .ef-pct {
    font-size: 11px;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
  }

  .ef-empty {
    font-size: 11px;
    color: var(--text-dim);
  }

  /* Toggle switch */
  .toggle {
    margin-left: auto;
    width: 46px;
    height: 26px;
    border-radius: 13px;
    border: none;
    background: var(--surface3);
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
    transition: background 0.22s;
  }

  .toggle.on { background: #3a6b3a; }

  .toggle-thumb {
    position: absolute;
    top: 3px; left: 3px;
    width: 20px; height: 20px;
    border-radius: 50%;
    background: var(--text-dim);
    transition: transform 0.22s, background 0.22s;
    display: block;
  }

  .toggle.on .toggle-thumb {
    transform: translateX(20px);
    background: var(--green-bright);
  }

  .no-data {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    padding: 20px;
  }

  /* ════════════════════ CHAT OVERLAY ════════════════════ */
  .chat-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.65);
    z-index: 50;
    display: flex;
    align-items: stretch;
    justify-content: flex-end;
  }

  .chat-panel {
    width: min(480px, 100vw);
    background: #141714;
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    position: relative;
  }

  .chat-close {
    position: absolute;
    top: 12px; right: 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 8px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 12px;
    font-family: inherit;
    z-index: 1;
    transition: color 0.15s;
  }

  .chat-close:hover { color: var(--text); }

  /* ════════════════════ SIDE PANEL ════════════════════ */
  .side-panel {
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: min(380px, 100vw);
    background: #141714;
    border-left: 1px solid var(--border);
    padding: 52px 16px 16px;
    overflow-y: auto;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .side-panel.wide {
    width: min(460px, 100vw);
  }

  .panel-close {
    position: absolute;
    top: 14px; right: 14px;
    background: none;
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 6px;
    width: 28px; height: 28px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .panel-section h2 {
    font-size: 1rem;
    color: var(--text);
    margin: 0 0 12px;
    font-weight: 600;
  }

  /* ════════════════════ RESPONSIVE ════════════════════ */
  @media (max-width: 900px) {
    .sidebar { width: 60px; }
    .nav-label, .logo-text, .sidebar-deco { display: none; }
    .sidebar-logo { justify-content: center; padding-bottom: 16px; }
    .nav-item { justify-content: center; padding: 10px 0; }
    .kpi-row { grid-template-columns: 1fr 1fr; }
    .kpi-card:first-child { grid-column: span 2; }
    .mid-row { grid-template-columns: 1fr; }
    .tiles-row { grid-template-columns: 1fr 1fr; }
    .tiles-5 { grid-template-columns: repeat(3, 1fr); }
    .tile-inv { grid-column: span 2; }
  }

  @media (max-width: 600px) {
    .kpi-row { grid-template-columns: 1fr; }
    .kpi-card:first-child { grid-column: auto; }
    .tiles-row { grid-template-columns: 1fr 1fr; }
    .tiles-5 { grid-template-columns: repeat(2, 1fr); }
    .tile-inv { grid-column: auto; }
    .dash-header { padding: 14px 16px 10px; }
    .dashboard { padding: 4px 16px 16px; }
    .search-bar { display: none; }
  }
</style>
