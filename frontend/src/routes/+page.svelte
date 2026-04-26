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
  import { onMount, tick } from 'svelte';
  import type { PageData } from './$types';

  const { data }: { data: PageData } = $props();

  let transactions: Transaction[] = $state(data.transactions);
  let stats = $state(data.stats);
  let budgets: Budget[] = $state(data.budgets ?? []);
  let alerts: AlertItem[] = $state(data.alerts ?? []);
  let loadingTx = $state(false);

  let drawerOpen = $state(false);
  let chatVisible = $state(true);
  let sidePanel: 'none' | 'goals' | 'import' | 'profiles' | 'whatif' | 'investments' | 'cdt' | 'subscriptions' | 'concepts' | 'health' = $state('none');
  let investigadorEnabled = $state(true);
  let alertsOpen = $state(false);
  let activeNav = $state('dashboard');

  let cashflowMode = $state<'weekly' | 'monthly'>('weekly');
  let historicalCashflow = $state<CashflowPoint[]>([]);
  let loadingCashflow = $state(false);
  let emergencyFund = $state<EmergencyFund | null>(null);

  let dashEl: HTMLDivElement;
  let chatRef: { focusInput?: () => void } | null = $state(null);

  const activeAlerts = $derived(alerts.filter(a => !a.dismissed));
  const urgentCount = $derived(activeAlerts.filter(a => a.severity === 'urgent').length);
  const badgeCount = $derived(activeAlerts.length);
  const savingsAmount = $derived(Math.max(0, (stats?.total_income ?? 0) - (stats?.total_expenses ?? 0)));

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
      try { historicalCashflow = await getDashboardCashflow(12); }
      finally { loadingCashflow = false; }
    }
  }

  const R = 52, SW = 14, C = 2 * Math.PI * R;
  const segments = $derived(stats ? buildSegments(stats.expenses_by_category ?? {}) : []);

  function buildSegments(byCategory: Record<string, number>) {
    const entries = Object.entries(byCategory)
      .filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]).slice(0, 5);
    const total = entries.reduce((s, [, v]) => s + v, 0);
    if (!total) return [];
    let cum = 0;
    return entries.map(([name, amount]) => {
      const pct = amount / total;
      const dashLength = pct * C;
      const seg = { name, amount, pct: pct * 100, color: CATEGORY_COLORS[name] ?? '#6a7868', dashLength, dashOffset: -cum };
      cum += dashLength;
      return seg;
    });
  }

  const efStatusColor = $derived(
    emergencyFund?.status === 'complete' ? '#4a9a4a'
      : emergencyFund?.status === 'warning' ? '#b88828'
      : '#c05050'
  );

  const _raw = new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
  const monthName = _raw.charAt(0).toUpperCase() + _raw.slice(1);

  onMount(async () => {
    try {
      const [status, ef] = await Promise.all([
        getInvestigadorStatus().catch(() => ({ enabled: true })),
        getEmergencyFund().catch(() => null),
      ]);
      investigadorEnabled = status.enabled;
      emergencyFund = ef;
    } catch { /* silent */ }

    const { gsap } = await import('gsap');
    await tick();
    if (dashEl) {
      // Subtle slide-in only — no opacity fade so cards are always visible
      gsap.from(dashEl.querySelectorAll('.kpi-card, .mid-card, .tile'), {
        y: 18, duration: 0.4, stagger: 0.04,
        ease: 'power2.out', delay: 0.02,
      });
    }
  });

  async function handleToggleInvestigador() {
    investigadorEnabled = !investigadorEnabled;
    await toggleInvestigador(investigadorEnabled);
  }

  async function refresh() {
    loadingTx = true;
    try {
      [transactions, stats, budgets, alerts] = await Promise.all([
        getTransactions(20), getStats(), getBudgets(), getAlerts(),
      ]);
      emergencyFund = await getEmergencyFund().catch(() => null);
    } finally { loadingTx = false; }
  }

  async function handleDelete(e: CustomEvent<number>) {
    await deleteTransaction(e.detail);
    await refresh();
  }

  function handleAlertDismissed(e: CustomEvent<number>) {
    alerts = alerts.map(a => a.id === e.detail ? { ...a, dismissed: true } : a);
  }

  function openChat() {
    chatVisible = true;
  }
</script>

<div class="app">

  <!-- ═══════════════════════════ SIDEBAR ═══════════════════════════════════ -->
  <aside class="sidebar">
    <div class="sidebar-inner">

      <div class="logo">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z"/>
            <path d="M12 8c-2 2-3 5-3 8 0 0 3-3 7-4C15 9 13 8 12 8z" opacity="0.5"/>
          </svg>
        </div>
        <span class="logo-text">Leaf</span>
      </div>

      <nav class="nav">
        {#each [
          { id: 'dashboard',     label: 'Dashboard',      path: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z' },
          { id: 'transacciones', label: 'Transacciones',  path: 'M7 16V4m0 0L3 8m4-4 4 4M17 8v12m0 0 4-4m-4 4-4-4' },
          { id: 'metas',         label: 'Metas',          path: 'M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2zm0 4a6 6 0 1 1 0 12A6 6 0 0 1 12 6zm0 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4z' },
          { id: 'presupuestos',  label: 'Presupuestos',   path: 'M18 20V10M12 20V4M6 20v-6' },
          { id: 'investigador',  label: 'Investigador',   path: 'M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z' },
          { id: 'salud',         label: 'Salud',          path: 'M22 12h-4l-3 9L9 3l-3 9H2' },
        ] as item}
          <button
            class="nav-item"
            class:active={activeNav === item.id}
            onclick={() => {
              activeNav = item.id;
              if      (item.id === 'transacciones') { drawerOpen = true; sidePanel = 'none'; }
              else if (item.id === 'metas')         { sidePanel = 'goals'; drawerOpen = false; }
              else if (item.id === 'presupuestos')  { drawerOpen = true; sidePanel = 'none'; }
              else if (item.id === 'salud')         { sidePanel = 'health'; drawerOpen = false; }
              else                                   { sidePanel = 'none'; drawerOpen = false; }
            }}
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d={item.path}/>
            </svg>
            <span class="nav-label">{item.label}</span>
          </button>
        {/each}
      </nav>

      <div class="nav-bottom">
        <div class="nav-divider"></div>
        {#each [
          { id: 'import', label: 'Importar / Exportar', panel: 'import' as const, path: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12' },
          { id: 'profiles', label: 'Perfiles', panel: 'profiles' as const, path: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75' },
        ] as item}
          <button
            class="nav-item"
            class:active={sidePanel === item.panel}
            onclick={() => { sidePanel = item.panel; activeNav = ''; drawerOpen = false; }}
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d={item.path}/>
            </svg>
            <span class="nav-label">{item.label}</span>
          </button>
        {/each}
      </div>

    </div>
  </aside>

  <!-- ════════════════════════ MAIN COLUMN ══════════════════════════════════ -->
  <div class="main-col">

    <!-- Header -->
    <header class="dash-header">
      <div class="header-left">
        <h1 class="month-title">{monthName}</h1>
        {#if activeAlerts.length > 0}
          <button
            class="alert-pill"
            class:urgent={urgentCount > 0}
            onclick={() => alertsOpen = !alertsOpen}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="13" height="13">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            {badgeCount} alerta{badgeCount > 1 ? 's' : ''}
          </button>
        {/if}
      </div>
      <div class="header-right">
        <button
          class="header-btn"
          title={chatVisible ? 'Ocultar chat' : 'Abrir chat con Leaf'}
          onclick={() => chatVisible = !chatVisible}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="16" height="16">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          {chatVisible ? 'Ocultar chat' : 'Chat Leaf'}
        </button>
        <div class="avatar">L</div>
      </div>
    </header>

    {#if alertsOpen && activeAlerts.length > 0}
      <div class="alerts-strip">
        <AlertBanner alerts={activeAlerts} on:dismissed={handleAlertDismissed} />
      </div>
    {/if}

    <!-- Body: dashboard + chat panel -->
    <div class="body-row">

      <!-- Dashboard -->
      <div class="dashboard" bind:this={dashEl}>

        <!-- KPI row -->
        <div class="kpi-row">

          <div class="kpi-card kpi-main">
            <div class="kpi-badge">🇨🇴 COP</div>
            <div class="kpi-label">Balance actual</div>
            <div class="kpi-value" class:neg={(stats?.balance ?? 0) < 0}>
              {formatCOP(stats?.balance ?? 0)}
            </div>
            <div class="kpi-sub">
              {savingsAmount > 0
                ? `${formatCOP(savingsAmount)} ahorrados este mes`
                : 'sin ahorro este mes'}
            </div>
            <div class="kpi-glow"></div>
          </div>

          <div class="kpi-card kpi-income">
            <div class="kpi-icon-wrap income-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="18" height="18">
                <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
              </svg>
            </div>
            <div class="kpi-label">Ingresos del mes</div>
            <div class="kpi-value income-val">{formatCOP(stats?.total_income ?? 0)}</div>
          </div>

          <div class="kpi-card kpi-expense">
            <div class="kpi-icon-wrap expense-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="18" height="18">
                <line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>
              </svg>
            </div>
            <div class="kpi-label">Gastos del mes</div>
            <div class="kpi-value expense-val">{formatCOP(stats?.total_expenses ?? 0)}</div>
            <div class="kpi-sub">
              {stats && stats.total_income > 0
                ? `${Math.round(stats.total_expenses / stats.total_income * 100)}% del ingreso`
                : ''}
            </div>
          </div>

        </div>

        <!-- Mid row: chart + donut -->
        <div class="mid-row">

          <!-- Cashflow chart -->
          <div class="mid-card chart-card">
            <div class="card-head">
              <span class="card-title">Cash flow</span>
              <div class="tab-group">
                <button class="tab" class:active={cashflowMode === 'weekly'} onclick={() => switchCashflow('weekly')}>Este mes</button>
                <button class="tab" class:active={cashflowMode === 'monthly'} onclick={() => switchCashflow('monthly')}>12 meses</button>
              </div>
            </div>
            <div class="chart-wrap">
              {#if loadingCashflow}
                <div class="chart-loading">
                  <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>
                </div>
              {:else}
                <CashflowChart data={chartData} showIncome={cashflowMode === 'monthly'} />
              {/if}
            </div>
            <div class="hablar-row">
              <button class="btn-3d" onclick={openChat}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="16" height="16">
                  <path d="M12 2a10 10 0 0 1 0 20c-2.5 0-4.8-.9-6.5-2.4L2 21l1.4-3.5A10 10 0 0 1 12 2z"/>
                </svg>
                Hablar con Leaf
              </button>
            </div>
          </div>

          <!-- Donut distribution -->
          <div class="mid-card donut-card">
            <div class="card-head">
              <span class="card-title">Distribución</span>
              <div class="leaf-deco">
                <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style="color: var(--green-light); opacity: 0.7">
                  <path d="M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z"/>
                </svg>
              </div>
            </div>

            {#if segments.length > 0}
              <div class="donut-center">
                <svg viewBox="0 0 160 160" class="donut-svg">
                  <circle cx="80" cy="80" r={R} fill="none" stroke="rgba(74,124,89,0.10)" stroke-width={SW} />
                  <g transform="rotate(-90 80 80)">
                    {#each segments as seg}
                      <circle cx="80" cy="80" r={R} fill="none"
                        stroke={seg.color} stroke-width={SW}
                        stroke-dasharray="{seg.dashLength} {C - seg.dashLength}"
                        stroke-dashoffset={seg.dashOffset}
                        stroke-linecap="butt"
                      />
                    {/each}
                  </g>
                  <text x="80" y="74" text-anchor="middle" class="donut-num">{stats?.transaction_count ?? 0}</text>
                  <text x="80" y="89" text-anchor="middle" class="donut-lbl">transacciones</text>
                </svg>
              </div>
              <div class="donut-legend">
                {#each segments.slice(0,5) as seg}
                  <div class="legend-row">
                    <span class="legend-dot" style="background:{seg.color}"></span>
                    <span class="legend-name">{seg.name}</span>
                    <span class="legend-pct" style="color:{seg.color}">{seg.pct.toFixed(0)}%</span>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="no-data">Sin gastos registrados</div>
            {/if}
          </div>

        </div>

        <!-- Tiles row 1 -->
        <div class="tiles-row">

          <button class="tile" onclick={() => { sidePanel = 'goals'; activeNav = 'metas'; drawerOpen = false; }}>
            <div class="tile-icon-wrap" style="--ic: #4a9a4a">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2" fill="currentColor"/>
              </svg>
            </div>
            <div class="tile-content">
              <span class="tile-title">Metas de ahorro</span>
              <span class="tile-sub">Proyecciones e inflación</span>
            </div>
            <svg class="tile-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M9 18l6-6-6-6"/></svg>
          </button>

          <button class="tile" onclick={() => { drawerOpen = true; activeNav = 'presupuestos'; sidePanel = 'none'; }}>
            <div class="tile-icon-wrap" style="--ic: #4878aa">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>
              </svg>
            </div>
            <div class="tile-content">
              <span class="tile-title">Presupuestos</span>
              <span class="tile-sub">Límites y alertas</span>
            </div>
            <svg class="tile-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M9 18l6-6-6-6"/></svg>
          </button>

          <!-- Investigador toggle -->
          <div class="tile tile-toggle">
            <div class="tile-icon-wrap" style="--ic: #7060aa">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
            </div>
            <div class="tile-content">
              <span class="tile-title">Investigador</span>
              <span class="tile-sub">{investigadorEnabled ? 'Activo · monitoreo en vivo' : 'Inactivo'}</span>
            </div>
            <button
              class="toggle-switch"
              class:on={investigadorEnabled}
              onclick={handleToggleInvestigador}
              title={investigadorEnabled ? 'Desactivar' : 'Activar'}
            >
              <span class="toggle-knob"></span>
            </button>
          </div>

        </div>

        <!-- Tiles row 2 -->
        <div class="tiles-row">

          <!-- Emergency fund -->
          <div class="tile tile-ef">
            <div class="tile-icon-wrap" style="--ic: {efStatusColor}">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
            </div>
            <div class="tile-content" style="flex:1">
              <span class="tile-title">Fondo de emergencia</span>
              {#if emergencyFund}
                <div class="ef-bar-wrap">
                  <div class="ef-bar-bg">
                    <div class="ef-bar-fill" style="width:{Math.min(100, emergencyFund.coverage_pct)}%; background:{efStatusColor}"></div>
                  </div>
                  <span class="ef-label" style="color:{efStatusColor}">
                    {emergencyFund.coverage_months.toFixed(1)} meses · {emergencyFund.coverage_pct.toFixed(0)}%
                  </span>
                </div>
              {:else}
                <span class="tile-sub">Calculando...</span>
              {/if}
            </div>
          </div>

          <button class="tile" onclick={() => { sidePanel = 'whatif'; activeNav = ''; drawerOpen = false; }}>
            <div class="tile-icon-wrap" style="--ic: #b88828">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/>
              </svg>
            </div>
            <div class="tile-content">
              <span class="tile-title">Simulador What-If</span>
              <span class="tile-sub">Escenarios financieros</span>
            </div>
            <svg class="tile-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M9 18l6-6-6-6"/></svg>
          </button>

          <button class="tile" onclick={() => { sidePanel = 'investments'; activeNav = ''; drawerOpen = false; }}>
            <div class="tile-icon-wrap" style="--ic: #2a9870">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="20" height="20">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
            </div>
            <div class="tile-content">
              <span class="tile-title">Inversiones CDT</span>
              <span class="tile-sub">Tasas y recomendaciones</span>
            </div>
            <svg class="tile-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14"><path d="M9 18l6-6-6-6"/></svg>
          </button>

        </div>

        <!-- Tiles row 3 (5 small) -->
        <div class="tiles-5">

          {#each [
            { label: 'Salud financiera', sub: 'Score y análisis', panel: 'health' as const, ic: '#4a7c59', path: 'M22 12h-4l-3 9L9 3l-3 9H2' },
            { label: 'Comparar CDT',     sub: 'Tasas en vivo',    panel: 'cdt' as const,    ic: '#7060aa', path: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z' },
            { label: 'Suscripciones',   sub: 'Pagos recurrentes', panel: 'subscriptions' as const, ic: '#b86028', path: 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8M3 3v5h5' },
            { label: 'Diccionario',     sub: 'CDT, UVT, GMF…',   panel: 'concepts' as const, ic: '#4878aa', path: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z' },
            { label: 'Importar',        sub: 'CSV y factura XML', panel: 'import' as const,  ic: '#b88828', path: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12' },
          ] as t}
            <button class="tile tile-sm" onclick={() => { sidePanel = t.panel; activeNav = ''; drawerOpen = false; }}>
              <div class="tile-icon-wrap-sm" style="--ic: {t.ic}">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
                  <path d={t.path}/>
                </svg>
              </div>
              <span class="tile-sm-label">{t.label}</span>
              <span class="tile-sm-sub">{t.sub}</span>
            </button>
          {/each}

        </div>

      </div>

      <!-- ═══════════════════ CHAT PANEL (persistent) ════════════════════════ -->
      {#if chatVisible}
        <div class="chat-col">
          <div class="chat-col-header">
            <div class="chat-col-title">
              <div class="chat-leaf-icon">
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                  <path d="M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z"/>
                </svg>
              </div>
              <span>Leaf IA</span>
              <span class="chat-online-dot"></span>
            </div>
            <button class="chat-close-btn" onclick={() => chatVisible = false} title="Ocultar chat">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14">
                <path d="M18 6 6 18M6 6l12 12"/>
              </svg>
            </button>
          </div>
          <div class="chat-col-body">
            <Chat on:sent={refresh} />
          </div>
        </div>
      {/if}

    </div>
  </div>

  <!-- ══════════════════════════ SIDE PANEL ══════════════════════════════════ -->
  {#if sidePanel !== 'none'}
    <div class="side-panel" class:wide={sidePanel === 'whatif' || sidePanel === 'investments'}>
      <button class="side-close" onclick={() => { sidePanel = 'none'; activeNav = 'dashboard'; }}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14">
          <path d="M18 6 6 18M6 6l12 12"/>
        </svg>
      </button>

      {#if sidePanel === 'goals'}
        <SavingsGoals />
      {:else if sidePanel === 'import'}
        <ImportExport />
      {:else if sidePanel === 'profiles'}
        <div class="panel-section">
          <h2 class="panel-title">Perfiles familiares</h2>
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

  <!-- ══════════════════════ TRANSACTION DRAWER ════════════════════════════ -->
  {#if drawerOpen}
    <TransactionDrawer
      {transactions} {stats} {budgets} loading={loadingTx}
      on:close={() => { drawerOpen = false; activeNav = 'dashboard'; }}
      on:delete={handleDelete}
    />
  {/if}

</div>

<style>
  /* ── App shell ── */
  .app {
    height: 100vh;
    display: flex;
    overflow: hidden;
    position: relative;
    z-index: 1;
  }

  /* ════════════════════ SIDEBAR ════════════════════ */
  .sidebar {
    width: 224px;
    flex-shrink: 0;
    background: rgba(185, 218, 175, 0.92);
    border-right: 1px solid rgba(255,255,255,0.55);
    box-shadow: 2px 0 20px rgba(52,100,68,0.08);
    z-index: 10;
  }

  .sidebar-inner {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 20px 12px 16px;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 10px 24px;
  }

  .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 3px 0 #2c5038, 0 5px 16px rgba(74,124,89,0.35);
    flex-shrink: 0;
  }

  .logo-text {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 22px;
    font-weight: 700;
    color: var(--green-dark);
    letter-spacing: -0.02em;
  }

  .nav { flex: 1; display: flex; flex-direction: column; gap: 2px; }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 12px;
    border-radius: 12px;
    border: none;
    background: none;
    color: var(--text-dim);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    cursor: pointer;
    width: 100%;
    text-align: left;
    transition: background 0.15s, color 0.15s;
  }

  .nav-item:hover { background: var(--green-pale); color: var(--text-mid); }

  .nav-item.active {
    background: rgba(74,124,89,0.14);
    color: var(--green-dark);
    font-weight: 500;
  }

  .nav-icon { flex-shrink: 0; width: 18px; height: 18px; }

  .nav-label { font-size: 13px; }

  .nav-bottom { padding-top: 12px; display: flex; flex-direction: column; gap: 2px; }
  .nav-divider { border-top: 1px solid var(--border); margin-bottom: 10px; }

  /* ════════════════════ MAIN COL ════════════════════ */
  .main-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Header ── */
  .dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px 12px;
    background: rgba(185, 218, 175, 0.90);
    border-bottom: 1px solid rgba(255,255,255,0.50);
    flex-shrink: 0;
    z-index: 5;
  }

  .header-left { display: flex; align-items: center; gap: 12px; }

  .month-title {
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 700;
    color: var(--green-dark);
    letter-spacing: -0.01em;
  }

  .alert-pill {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid rgba(184,136,40,0.35);
    background: rgba(184,136,40,0.10);
    color: var(--amber);
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .alert-pill.urgent {
    border-color: rgba(192,80,80,0.35);
    background: rgba(192,80,80,0.10);
    color: var(--red);
  }

  .header-right { display: flex; align-items: center; gap: 10px; }

  .header-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 7px 14px;
    border-radius: 20px;
    border: 1px solid rgba(180,210,170,0.50);
    background: rgba(200,228,192,0.70);
    color: var(--text-mid);
    font-family: 'Inter', sans-serif;
    font-size: 12px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .header-btn:hover { background: rgba(180,215,168,0.88); color: var(--green); }

  .avatar {
    width: 34px; height: 34px;
    border-radius: 50%;
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    color: white;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(74,124,89,0.3);
  }

  .alerts-strip { padding: 0 24px 8px; flex-shrink: 0; }

  /* ── Body row ── */
  .body-row {
    flex: 1;
    display: flex;
    overflow: hidden;
    gap: 0;
  }

  /* ════════════════════ DASHBOARD ════════════════════ */
  .dashboard {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    padding: 20px 20px 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ── KPI cards ── */
  .kpi-row {
    display: grid;
    grid-template-columns: 1.4fr 1fr 1fr;
    gap: 14px;
  }

  .kpi-card {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(255,255,255,0.80);
    border-radius: 20px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(52,100,68,0.08), inset 0 1px 0 rgba(255,255,255,0.85);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(52,100,68,0.14), inset 0 1px 0 rgba(255,255,255,0.9);
  }

  .kpi-badge {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.08em;
    margin-bottom: 10px;
    font-weight: 500;
  }

  .kpi-label {
    font-size: 11px;
    color: var(--text-mid);
    margin-bottom: 6px;
    font-weight: 400;
  }

  .kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.03em;
    line-height: 1.05;
    font-family: 'Inter', sans-serif;
    margin-bottom: 6px;
  }

  .kpi-value.neg { color: var(--red); }
  .income-val { color: var(--green-dark); }
  .expense-val { color: var(--amber); }

  .kpi-sub { font-size: 11px; color: var(--text-dim); }

  .kpi-icon-wrap {
    width: 36px; height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 12px;
  }

  .income-icon { background: rgba(74,154,74,0.14); color: var(--green); }
  .expense-icon { background: rgba(184,136,40,0.14); color: var(--amber); }

  .kpi-glow {
    position: absolute;
    top: 50%; right: -20px;
    transform: translateY(-50%);
    width: 140px; height: 140px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(109,184,126,0.15) 0%, transparent 70%);
    pointer-events: none;
  }

  /* ── Mid row ── */
  .mid-row {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 14px;
    min-height: 280px;
  }

  .mid-card {
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(255,255,255,0.80);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 4px 16px rgba(52,100,68,0.08), inset 0 1px 0 rgba(255,255,255,0.85);
    display: flex;
    flex-direction: column;
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    flex-shrink: 0;
  }

  .card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    letter-spacing: -0.01em;
  }

  .leaf-deco { opacity: 0.6; }

  /* Chart tabs */
  .tab-group {
    display: flex;
    gap: 3px;
    background: rgba(74,124,89,0.08);
    border: 1px solid rgba(74,124,89,0.12);
    border-radius: 10px;
    padding: 3px;
  }

  .tab {
    padding: 4px 12px;
    border: none;
    border-radius: 8px;
    background: none;
    color: var(--text-dim);
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .tab.active {
    background: var(--glass-strong);
    color: var(--green-dark);
    font-weight: 500;
    box-shadow: 0 1px 4px rgba(74,124,89,0.12);
  }

  .chart-card { position: relative; }

  .chart-wrap {
    flex: 1;
    min-height: 0;
    padding-bottom: 56px;
  }

  .chart-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    height: 100%;
  }

  .loading-dot {
    width: 7px; height: 7px;
    background: var(--green);
    border-radius: 50%;
    animation: ldot 1.2s infinite;
    display: inline-block;
  }

  .loading-dot:nth-child(2) { animation-delay: 0.2s; }
  .loading-dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes ldot {
    0%,80%,100% { transform: scale(0.7); opacity: 0.4; }
    40%          { transform: scale(1); opacity: 1; }
  }

  .hablar-row {
    position: absolute;
    bottom: 16px; left: 50%;
    transform: translateX(-50%);
    z-index: 2;
  }

  /* ── 3D Button ── */
  .btn-3d {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 11px 28px;
    border-radius: 24px;
    border: none;
    background: linear-gradient(145deg, #6db87e 0%, #4a7c59 100%);
    color: #fff;
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    box-shadow:
      0 5px 0 var(--green-dark),
      0 8px 20px rgba(44,80,56,0.35);
    transform: translateY(0);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
    letter-spacing: 0.01em;
  }

  .btn-3d:hover {
    transform: translateY(-3px);
    box-shadow:
      0 8px 0 var(--green-dark),
      0 14px 30px rgba(44,80,56,0.40);
  }

  .btn-3d:active {
    transform: translateY(4px);
    box-shadow:
      0 1px 0 var(--green-dark),
      0 3px 8px rgba(44,80,56,0.20);
  }

  /* ── Donut card ── */
  .donut-center {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-height: 0;
  }

  .donut-svg { width: 148px; height: 148px; }

  .donut-num {
    font-family: 'Playfair Display', serif;
    font-size: 26px;
    font-weight: 700;
    fill: var(--text);
  }

  .donut-lbl {
    font-family: 'Inter', sans-serif;
    font-size: 8px;
    fill: var(--text-dim);
    letter-spacing: 0.06em;
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
  }

  .legend-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legend-name { color: var(--text-mid); }
  .legend-pct { font-size: 10px; font-weight: 600; }

  /* ── Tiles ── */
  .tiles-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
  }

  .tile {
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(255,255,255,0.80);
    border-radius: 18px;
    padding: 16px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    text-align: left;
    box-shadow: 0 3px 12px rgba(74,124,89,0.07), inset 0 1px 0 rgba(255,255,255,0.85);
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.15s;
  }

  .tile:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 24px rgba(74,124,89,0.12), inset 0 1px 0 rgba(255,255,255,0.9);
    background: rgba(245, 255, 242, 0.96);
  }

  .tile-toggle { cursor: default; }
  .tile-toggle:hover { transform: none; }

  .tile-ef { cursor: default; align-items: flex-start; }
  .tile-ef:hover { transform: none; }

  .tile-icon-wrap {
    width: 40px; height: 40px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--ic) 12%, rgba(255,255,255,0.5));
    border: 1px solid color-mix(in srgb, var(--ic) 20%, rgba(255,255,255,0.6));
    color: var(--ic);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 2px 0 color-mix(in srgb, var(--ic) 30%, transparent),
                0 4px 10px color-mix(in srgb, var(--ic) 20%, transparent);
  }

  .tile-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }

  .tile-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tile-sub { font-size: 11px; color: var(--text-dim); }

  .tile-arrow { color: var(--text-dim); flex-shrink: 0; }

  /* Toggle switch */
  .toggle-switch {
    margin-left: auto;
    width: 48px; height: 28px;
    border-radius: 14px;
    border: none;
    background: rgba(74,124,89,0.15);
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
    transition: background 0.25s;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.12);
  }

  .toggle-switch.on {
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.15), 0 2px 0 #2c5038, 0 3px 8px rgba(74,124,89,0.3);
  }

  .toggle-knob {
    position: absolute;
    top: 3px; left: 3px;
    width: 22px; height: 22px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.18);
    transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1);
    display: block;
  }

  .toggle-switch.on .toggle-knob { transform: translateX(20px); }

  /* Emergency fund tile */
  .ef-bar-wrap { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }

  .ef-bar-bg {
    height: 5px;
    background: rgba(74,124,89,0.12);
    border-radius: 3px;
    overflow: hidden;
  }

  .ef-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.7s cubic-bezier(0.22,1,0.36,1);
  }

  .ef-label { font-size: 10px; font-weight: 600; }

  /* ── Tiles 5 ── */
  .tiles-5 {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
  }

  .tile-sm {
    background: var(--glass);
    border: 1px solid rgba(255,255,255,0.80);
    border-radius: 16px;
    padding: 14px 14px 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    font-family: 'Inter', sans-serif;
    cursor: pointer;
    text-align: left;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 2px 8px rgba(74,124,89,0.06), inset 0 1px 0 rgba(255,255,255,0.85);
    transition: transform 0.2s, box-shadow 0.2s, background 0.15s;
  }

  .tile-sm:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(74,124,89,0.11), inset 0 1px 0 rgba(255,255,255,0.9);
    background: rgba(245, 255, 242, 0.96);
  }

  .tile-icon-wrap-sm {
    width: 32px; height: 32px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--ic) 12%, rgba(255,255,255,0.5));
    border: 1px solid color-mix(in srgb, var(--ic) 18%, rgba(255,255,255,0.6));
    color: var(--ic);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 0 color-mix(in srgb, var(--ic) 25%, transparent);
  }

  .tile-sm-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.2;
  }

  .tile-sm-sub { font-size: 10px; color: var(--text-dim); line-height: 1.3; }

  /* No data */
  .no-data {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: var(--text-dim);
  }

  /* ════════════════════ CHAT COL ════════════════════ */
  .chat-col {
    width: 360px;
    flex-shrink: 0;
    background: var(--glass-mid);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-left: 1px solid rgba(255,255,255,0.72);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: -4px 0 24px rgba(52,100,68,0.06);
  }

  .chat-col-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px 12px;
    border-bottom: 1px solid rgba(74,124,89,0.12);
    background: rgba(255,255,255,0.35);
    flex-shrink: 0;
  }

  .chat-col-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--green-dark);
  }

  .chat-leaf-icon {
    width: 26px; height: 26px;
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    box-shadow: 0 2px 0 #2c5038, 0 3px 8px rgba(74,124,89,0.3);
  }

  .chat-online-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #4a9a4a;
    box-shadow: 0 0 6px rgba(74,154,74,0.6);
  }

  .chat-close-btn {
    width: 28px; height: 28px;
    border-radius: 8px;
    border: 1px solid rgba(74,124,89,0.15);
    background: rgba(255,255,255,0.5);
    color: var(--text-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .chat-close-btn:hover { background: rgba(192,80,80,0.12); color: var(--red); border-color: rgba(192,80,80,0.2); }

  .chat-col-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

  /* ════════════════════ SIDE PANEL ════════════════════ */
  .side-panel {
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: min(400px, 100vw);
    background: var(--glass-strong);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-left: 1px solid var(--glass-border);
    box-shadow: -8px 0 40px rgba(52,100,68,0.12);
    padding: 52px 0 0;
    overflow-y: auto;
    z-index: 30;
    display: flex;
    flex-direction: column;
  }

  .side-panel.wide { width: min(480px, 100vw); }

  .side-close {
    position: absolute;
    top: 14px; right: 14px;
    width: 30px; height: 30px;
    border-radius: 10px;
    border: 1px solid rgba(74,124,89,0.18);
    background: rgba(255,255,255,0.6);
    color: var(--text-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .side-close:hover { background: rgba(192,80,80,0.10); color: var(--red); }

  .panel-section { padding: 0 20px; }
  .panel-title {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    color: var(--green-dark);
    margin-bottom: 16px;
    font-weight: 700;
  }

  /* ════════════════════ RESPONSIVE ════════════════════ */
  @media (max-width: 1280px) {
    .tiles-5 { grid-template-columns: repeat(3, 1fr); }
    .chat-col { width: 320px; }
  }

  @media (max-width: 1024px) {
    .sidebar { width: 64px; }
    .nav-label, .logo-text { display: none; }
    .logo { justify-content: center; padding: 4px 0 20px; }
    .nav-item { justify-content: center; padding: 10px 0; }
    .chat-col { display: none; }
    .kpi-row { grid-template-columns: 1fr 1fr; }
    .kpi-card:first-child { grid-column: span 2; }
    .mid-row { grid-template-columns: 1fr; }
    .tiles-row { grid-template-columns: 1fr 1fr; }
    .tiles-5 { grid-template-columns: repeat(2, 1fr); }
  }

  @media (max-width: 640px) {
    .kpi-row { grid-template-columns: 1fr; }
    .kpi-card:first-child { grid-column: auto; }
    .tiles-row { grid-template-columns: 1fr; }
    .tiles-5 { grid-template-columns: 1fr 1fr; }
    .dashboard { padding: 14px 14px 24px; }
    .dash-header { padding: 12px 16px; }
    .month-title { font-size: 16px; }
  }
</style>
