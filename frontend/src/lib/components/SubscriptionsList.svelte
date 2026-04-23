<script lang="ts">
  import { onMount } from 'svelte';
  import { formatCOP } from '$lib/api';

  const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';

  interface Subscription {
    name: string;
    category: string;
    amount_per_payment: number;
    monthly_cost: number;
    frequency: string;
    occurrences: number;
    last_payment: string;
    days_since_last: number;
    potentially_unused: boolean;
  }

  interface SubData {
    subscriptions: Subscription[];
    total_monthly: number;
    total_annual: number;
    potentially_unused: Subscription[];
    savings_potential_monthly: number;
    savings_potential_annual: number;
    count: number;
  }

  let data = $state<SubData | null>(null);
  let loading = $state(true);
  let error = $state('');
  let tab = $state<'all' | 'unused'>('all');

  onMount(async () => {
    try {
      const res = await fetch(`${API_URL}/subscriptions/`);
      if (!res.ok) throw new Error('Error al cargar suscripciones');
      data = await res.json();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error desconocido';
    } finally {
      loading = false;
    }
  });

  const list = $derived(
    data
      ? (tab === 'unused' ? data.potentially_unused : data.subscriptions)
      : []
  );

  function daysLabel(days: number): string {
    if (days === 0) return 'hoy';
    if (days === 1) return 'ayer';
    if (days < 7) return `hace ${days} días`;
    if (days < 30) return `hace ${Math.floor(days / 7)} semanas`;
    return `hace ${Math.floor(days / 30)} meses`;
  }
</script>

<div class="subs">
  <div class="subs-header">
    <span class="subs-icon">🔄</span>
    <div>
      <h2 class="subs-title">Suscripciones activas</h2>
      <p class="subs-sub">Detectadas en tus últimos 90 días de transacciones</p>
    </div>
  </div>

  {#if loading}
    <div class="loading">Analizando transacciones...</div>
  {:else if error}
    <div class="error-msg">{error}</div>
  {:else if data}
    <!-- Summary cards -->
    <div class="summary-row">
      <div class="sum-card">
        <div class="sum-val">{formatCOP(data.total_monthly)}</div>
        <div class="sum-lbl">/{" "}mes total</div>
      </div>
      <div class="sum-card">
        <div class="sum-val">{formatCOP(data.total_annual)}</div>
        <div class="sum-lbl">/año total</div>
      </div>
      {#if data.savings_potential_monthly > 0}
        <div class="sum-card savings">
          <div class="sum-val positive">{formatCOP(data.savings_potential_monthly)}</div>
          <div class="sum-lbl">ahorro posible/mes</div>
        </div>
      {/if}
    </div>

    {#if data.savings_potential_annual > 0}
      <div class="savings-banner">
        ⚠️ Tienes <strong>{data.potentially_unused.length} suscripción(es) posiblemente sin usar</strong>.
        Cancelarlas = {formatCOP(data.savings_potential_annual)}/año ahorrado.
      </div>
    {/if}

    <!-- Tabs -->
    <div class="tabs">
      <button class="tab" class:active={tab === 'all'} onclick={() => tab = 'all'}>
        Todas ({data.count})
      </button>
      {#if data.potentially_unused.length > 0}
        <button class="tab" class:active={tab === 'unused'} onclick={() => tab = 'unused'}>
          ⚠️ Sin usar ({data.potentially_unused.length})
        </button>
      {/if}
    </div>

    <!-- List -->
    {#if list.length === 0}
      <div class="empty">
        {tab === 'unused' ? 'No hay suscripciones sin usar detectadas' : 'No se detectaron suscripciones recurrentes'}
      </div>
    {:else}
      <div class="sub-list">
        {#each list as sub}
          <div class="sub-row" class:unused={sub.potentially_unused}>
            <div class="sub-icon">
              {sub.potentially_unused ? '⚠️' : '✅'}
            </div>
            <div class="sub-info">
              <div class="sub-name">{sub.name}</div>
              <div class="sub-meta">
                {sub.frequency} · {daysLabel(sub.days_since_last)}
                {sub.potentially_unused ? ' — posiblemente sin uso' : ''}
              </div>
            </div>
            <div class="sub-cost">
              <div class="sub-monthly">{formatCOP(sub.monthly_cost)}/mes</div>
              <div class="sub-annual">{formatCOP(sub.monthly_cost * 12)}/año</div>
            </div>
          </div>
        {/each}
      </div>
    {/if}

    <p class="note">
      💡 Detección basada en pagos recurrentes. Una suscripción se marca como "sin usar" si no tuvo pagos en más de 45 días.
    </p>
  {/if}
</div>

<style>
  .subs {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 0;
  }

  .subs-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .subs-icon { font-size: 28px; }

  .subs-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .subs-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin: 0;
  }

  .loading, .error-msg, .empty {
    font-size: 12px;
    color: var(--text-dim);
    text-align: center;
    padding: 20px;
  }

  .error-msg { color: var(--red); }

  .summary-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .sum-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    text-align: center;
  }

  .sum-card.savings {
    border-color: rgba(74,222,128,0.2);
    background: rgba(74,222,128,0.05);
  }

  .sum-val {
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    font-family: 'Inter', sans-serif;
  }

  .sum-val.positive { color: #4ade80; }

  .sum-lbl {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 2px;
  }

  .savings-banner {
    font-size: 12px;
    color: #fbbf24;
    background: rgba(251,191,36,0.07);
    border: 1px solid rgba(251,191,36,0.2);
    border-radius: 8px;
    padding: 10px 12px;
    line-height: 1.4;
  }

  .tabs {
    display: flex;
    gap: 6px;
  }

  .tab {
    flex: 1;
    padding: 7px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .tab.active {
    border-color: var(--green-dim);
    color: var(--text);
  }

  .sub-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .sub-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    transition: border-color 0.15s;
  }

  .sub-row.unused {
    border-color: rgba(251,191,36,0.25);
    background: rgba(251,191,36,0.04);
  }

  .sub-icon { font-size: 16px; flex-shrink: 0; }

  .sub-info { flex: 1; min-width: 0; }

  .sub-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub-meta {
    font-size: 11px;
    color: var(--text-dim);
    margin-top: 1px;
  }

  .sub-cost {
    text-align: right;
    flex-shrink: 0;
  }

  .sub-monthly {
    font-size: 13px;
    font-weight: 700;
    color: var(--text);
    font-family: 'Inter', sans-serif;
  }

  .sub-annual {
    font-size: 10px;
    color: var(--text-dim);
  }

  .note {
    font-size: 10px;
    color: var(--text-dim);
    line-height: 1.4;
    margin: 0;
  }
</style>
