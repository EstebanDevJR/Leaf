<script lang="ts">
  import { deleteTransaction, dismissAlert, formatCOP, getAlerts, getBudgets, getStats, getTransactions, getInvestigadorStatus, toggleInvestigador } from '$lib/api';
  import type { AlertItem, Budget } from '$lib/api';
  import AlertBanner from '$lib/components/AlertBanner.svelte';
  import Chat from '$lib/components/Chat.svelte';
  import TransactionDrawer from '$lib/components/TransactionDrawer.svelte';
  import SavingsGoals from '$lib/components/SavingsGoals.svelte';
  import ImportExport from '$lib/components/ImportExport.svelte';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import CallButton from '$lib/voice/CallButton.svelte';
  import type { PageData } from './$types';

  export let data: PageData;

  let transactions = data.transactions;
  let stats = data.stats;
  let budgets: Budget[] = data.budgets ?? [];
  let alerts: AlertItem[] = data.alerts ?? [];
  let loadingTx = false;
  let drawerOpen = false;
  let sidePanel: 'none' | 'goals' | 'import' | 'profiles' = 'none';
  let investigadorEnabled = $state(true);

  $: activeAlerts = alerts.filter(a => !a.dismissed);
  $: urgentCount = activeAlerts.filter(a => a.severity === 'urgent').length;
  $: warnCount = activeAlerts.filter(a => a.severity === 'warn').length;
  $: badgeCount = activeAlerts.length;

  // Load investigador status on mount
  import { onMount } from 'svelte';
  onMount(async () => {
    try {
      const status = await getInvestigadorStatus();
      investigadorEnabled = status.enabled;
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

  function toggleDrawer() {
    drawerOpen = !drawerOpen;
    if (drawerOpen) sidePanel = 'none';
  }

  function togglePanel(panel: typeof sidePanel) {
    sidePanel = sidePanel === panel ? 'none' : panel;
    if (sidePanel !== 'none') drawerOpen = false;
  }

  let alertsOpen = false;
</script>

<div class="app">
  <header class="topbar">
    <div class="logo">
      <span class="logo-text">Leaf</span>
      <span class="logo-emoji">🌿</span>
      <span class="logo-tag">v2</span>
    </div>

    {#if stats}
      <div class="quick-stats">
        <span class="qs-exp">{formatCOP(stats.total_expenses)}</span>
        <span class="qs-sep">·</span>
        <span class="qs-inc">{formatCOP(stats.total_income)}</span>
        <span class="qs-label">este mes</span>
      </div>
    {/if}

    <!-- DIAN alerts bell -->
    {#if badgeCount > 0}
      <button
        class="alert-bell"
        class:urgent={urgentCount > 0}
        class:warn={warnCount > 0 && !urgentCount}
        on:click={() => alertsOpen = !alertsOpen}
        title="Alertas DIAN"
      >
        🔔
        <span class="bell-badge">{badgeCount}</span>
      </button>
    {/if}

    <CallButton />

    <div class="topbar-actions">
      <button class="drawer-toggle" on:click={() => togglePanel('goals')} class:active={sidePanel === 'goals'} title="Metas de ahorro">
        🎯
      </button>
      <button class="drawer-toggle" on:click={() => togglePanel('import')} class:active={sidePanel === 'import'} title="Importar / Exportar">
        ↕️
      </button>
      <button class="drawer-toggle" on:click={() => togglePanel('profiles')} class:active={sidePanel === 'profiles'} title="Perfiles">
        👤
      </button>
      <button
        class="inv-toggle"
        class:enabled={investigadorEnabled}
        on:click={handleToggleInvestigador}
        title={investigadorEnabled ? 'Investigador ON — click para desactivar' : 'Investigador OFF — click para activar'}
      >
        🔍 {investigadorEnabled ? 'ON' : 'OFF'}
      </button>
      <button class="drawer-toggle" on:click={toggleDrawer} class:active={drawerOpen}>
        {#if drawerOpen}✕{:else}📊{/if}
        <span class="drawer-toggle-label">{drawerOpen ? 'cerrar' : 'transacciones'}</span>
      </button>
    </div>
  </header>

  <!-- Alerts panel (below topbar) -->
  {#if alertsOpen && activeAlerts.length > 0}
    <div class="alerts-panel">
      <AlertBanner alerts={activeAlerts} on:dismissed={handleAlertDismissed} />
    </div>
  {/if}

  <main class="main">
    <Chat on:sent={refresh} />
  </main>

  {#if drawerOpen}
    <TransactionDrawer
      {transactions}
      {stats}
      {budgets}
      loading={loadingTx}
      on:close={toggleDrawer}
      on:delete={handleDelete}
    />
  {/if}

  {#if sidePanel !== 'none'}
    <div class="side-panel">
      <button class="panel-close" on:click={() => sidePanel = 'none'}>✕</button>
      {#if sidePanel === 'goals'}
        <SavingsGoals />
      {:else if sidePanel === 'import'}
        <ImportExport />
      {:else if sidePanel === 'profiles'}
        <div class="panel-section">
          <h2 style="font-size:1rem;color:#e2e8f0;margin:0 0 12px">Perfiles familiares</h2>
          <ProfileSwitcher />
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .app {
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Topbar ── */
  .topbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 10;
  }

  .logo {
    display: flex;
    align-items: baseline;
    gap: 5px;
    flex-shrink: 0;
  }

  .logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 700;
    color: #fff;
    font-style: italic;
  }

  .logo-emoji { font-size: 16px; }

  .logo-tag {
    font-size: 10px;
    color: var(--green);
    background: var(--green-glow);
    border: 1px solid var(--green-dim);
    padding: 1px 6px;
    border-radius: 3px;
    letter-spacing: 0.08em;
  }

  /* ── Quick stats ── */
  .quick-stats {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    flex: 1;
  }

  .qs-exp { color: var(--amber); }
  .qs-inc { color: var(--green); }
  .qs-sep { color: var(--border); }
  .qs-label {
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }

  /* ── Alert bell ── */
  .alert-bell {
    position: relative;
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 14px;
    cursor: pointer;
    flex-shrink: 0;
    transition: border-color 0.15s;
  }

  .alert-bell.urgent { border-color: rgba(248,113,113,0.5); }
  .alert-bell.warn   { border-color: rgba(251,191,36,0.4); }
  .alert-bell:hover  { border-color: var(--green-dim); }

  .bell-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: var(--red);
    color: #fff;
    font-size: 9px;
    font-family: 'JetBrains Mono', monospace;
    min-width: 16px;
    height: 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 3px;
    line-height: 1;
  }

  .alert-bell.warn .bell-badge { background: var(--amber); color: var(--bg, #0a0f0a); }

  /* ── Alerts panel ── */
  .alerts-panel {
    padding: 8px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    z-index: 9;
  }

  /* ── Drawer toggle ── */
  .drawer-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    font-family: inherit;
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    flex-shrink: 0;
    transition: border-color 0.15s, color 0.15s;
  }

  .drawer-toggle:hover { border-color: var(--green-dim); color: var(--text); }
  .drawer-toggle.active { border-color: var(--green-dim); color: var(--green); }

  .drawer-toggle-label {
    font-size: 11px;
    letter-spacing: 0.05em;
  }

  .topbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .inv-toggle {
    background: none;
    border: 1px solid var(--border);
    color: var(--text-dim);
    font-size: 11px;
    padding: 5px 8px;
    border-radius: 6px;
    cursor: pointer;
    flex-shrink: 0;
    transition: border-color 0.15s, color 0.15s;
  }

  .inv-toggle.enabled {
    border-color: rgba(34, 197, 94, 0.4);
    color: var(--green);
  }

  @media (max-width: 480px) {
    .drawer-toggle-label { display: none; }
    .quick-stats { display: none; }
  }

  /* ── Main ── */
  .main {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  /* ── Side panel ── */
  .side-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(380px, 100vw);
    background: #0f172a;
    border-left: 1px solid var(--border);
    padding: 56px 16px 16px;
    overflow-y: auto;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .panel-close {
    position: absolute;
    top: 14px;
    right: 14px;
    background: none;
    border: 1px solid var(--border);
    color: var(--text-dim);
    border-radius: 6px;
    width: 28px;
    height: 28px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .panel-section { padding: 4px 0; }
</style>
