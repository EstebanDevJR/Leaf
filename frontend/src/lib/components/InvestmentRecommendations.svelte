<script lang="ts">
  import { onMount } from 'svelte';
  import { formatCOP, getInvestments } from '$lib/api';
  import type { InvestmentsData } from '$lib/api';

  const TERMS = [3, 6, 12, 24];

  let data = $state<InvestmentsData | null>(null);
  let loading = $state(true);
  let error = $state('');
  let selectedTerm = $state(12);
  let investAmount = $state(1_000_000);

  onMount(async () => {
    try {
      data = await getInvestments();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error al cargar tasas';
    } finally {
      loading = false;
    }
  });

  const ranked = $derived(
    data
      ? [...data.banks]
          .map(b => ({ ...b, rate: b.rates[selectedTerm] ?? b.best_rate }))
          .sort((a, b) => b.rate - a.rate)
      : []
  );

  function calcReturn(rate: number, term: number, amount: number): number {
    return amount * (rate / 100) * (term / 12);
  }

  const inflationReturn = $derived(
    data ? calcReturn(data.inflation_rate, selectedTerm, investAmount) : 0
  );
</script>

<div class="inv">
  <div class="inv-header">
    <span class="inv-icon">📊</span>
    <div>
      <h2 class="inv-title">Inversiones CDT</h2>
      <p class="inv-sub">
        {#if data}
          Tasas {data.is_live ? 'actualizadas' : 'de referencia'} · BanRep {data.banrep_rate}% · Inflación {data.inflation_rate}%
        {:else}
          Cargando tasas...
        {/if}
      </p>
    </div>
  </div>

  {#if loading}
    <div class="loading">Consultando tasas...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if data}
    <!-- Term selector -->
    <div class="term-row">
      {#each TERMS as t}
        <button
          class="term-btn"
          class:active={selectedTerm === t}
          onclick={() => selectedTerm = t}
        >
          {t} meses
        </button>
      {/each}
    </div>

    <!-- Amount input -->
    <div class="amount-row">
      <span class="amount-lbl">Simula tu rendimiento con:</span>
      <div class="amount-input-wrap">
        <span class="prefix">$</span>
        <input
          type="number"
          min="100000"
          step="100000"
          bind:value={investAmount}
          class="amount-input"
        />
        <span class="suffix">COP</span>
      </div>
    </div>

    <!-- Banks table -->
    <div class="banks-list">
      {#each ranked as bank, i}
        {@const ret = calcReturn(bank.rate, selectedTerm, investAmount)}
        {@const beatsInflation = bank.rate > (data?.inflation_rate ?? 0)}
        <div class="bank-row" class:top={i === 0}>
          {#if i === 0}
            <span class="badge">Mejor tasa</span>
          {/if}
          <div class="bank-info">
            <span class="bank-name">{bank.bank}</span>
            <span class="bank-rate" class:inflation-beat={beatsInflation}>
              {bank.rate.toFixed(1)}% EA
              {#if beatsInflation}<span class="beat-tag">↑ inflación</span>{/if}
            </span>
          </div>
          <div class="bank-return">
            {#if investAmount > 0}
              <span class="return-val">+{formatCOP(ret)}</span>
              <span class="return-lbl">rendimiento</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <!-- Inflation comparison -->
    {#if investAmount > 0}
      <div class="inflation-note">
        <span>📉 Con inflación ({data.inflation_rate}%): perderías {formatCOP(inflationReturn)} en poder adquisitivo</span>
      </div>
    {/if}

    <!-- Risk profiles -->
    <div class="profiles-section">
      <div class="profiles-title">Perfiles de riesgo</div>
      <div class="profiles-grid">
        <div class="profile-card">
          <div class="profile-name">🛡️ Conservador</div>
          <div class="profile-desc">CDT + TES — bajo riesgo, retorno predecible</div>
        </div>
        <div class="profile-card">
          <div class="profile-name">⚖️ Moderado</div>
          <div class="profile-desc">Fondos renta fija + CDT</div>
        </div>
        <div class="profile-card">
          <div class="profile-name">🚀 Agresivo</div>
          <div class="profile-desc">Renta variable + ETF colombianos</div>
        </div>
      </div>
    </div>

    <p class="disclaimer">
      ⚠️ Tasas educativas de referencia. Verifica directamente con cada entidad antes de invertir.
    </p>
  {/if}
</div>

<style>
  .inv {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 0;
  }

  .inv-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .inv-icon { font-size: 28px; }

  .inv-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .inv-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin: 0;
  }

  .loading, .error {
    font-size: 12px;
    color: var(--text-dim);
    text-align: center;
    padding: 20px;
  }

  .error { color: var(--red); }

  .term-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .term-btn {
    padding: 6px 14px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .term-btn.active {
    border-color: var(--green-dim);
    color: var(--text);
  }

  .amount-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .amount-lbl {
    font-size: 11px;
    color: var(--text-dim);
  }

  .amount-input-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 12px;
  }

  .prefix, .suffix {
    color: var(--text-dim);
    font-size: 12px;
    flex-shrink: 0;
  }

  .amount-input {
    flex: 1;
    background: none;
    border: none;
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 600;
    outline: none;
    min-width: 0;
  }

  .banks-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .bank-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    position: relative;
    transition: border-color 0.15s;
  }

  .bank-row.top {
    border-color: rgba(74,222,128,0.3);
    background: rgba(74,222,128,0.05);
  }

  .badge {
    position: absolute;
    top: -8px;
    left: 10px;
    background: #3a6b3a;
    color: #e8f5e8;
    font-size: 9px;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
  }

  .bank-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .bank-name {
    font-size: 13px;
    color: var(--text);
    font-weight: 500;
  }

  .bank-rate {
    font-size: 12px;
    color: var(--text-dim);
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .bank-rate.inflation-beat { color: #4ade80; }

  .beat-tag {
    font-size: 9px;
    background: rgba(74,222,128,0.15);
    color: #4ade80;
    padding: 1px 5px;
    border-radius: 4px;
  }

  .bank-return {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 1px;
  }

  .return-val {
    font-size: 13px;
    font-weight: 700;
    color: #4ade80;
    font-family: 'Inter', sans-serif;
  }

  .return-lbl {
    font-size: 9px;
    color: var(--text-dim);
  }

  .inflation-note {
    font-size: 11px;
    color: var(--text-dim);
    padding: 8px 12px;
    background: rgba(248,113,113,0.06);
    border: 1px solid rgba(248,113,113,0.12);
    border-radius: 8px;
  }

  .profiles-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .profiles-title {
    font-size: 11px;
    color: var(--text-dim);
    font-weight: 600;
  }

  .profiles-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 6px;
  }

  .profile-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px;
  }

  .profile-name {
    font-size: 11px;
    color: var(--text);
    font-weight: 600;
    margin-bottom: 2px;
  }

  .profile-desc {
    font-size: 10px;
    color: var(--text-dim);
    line-height: 1.3;
  }

  .disclaimer {
    font-size: 10px;
    color: var(--text-dim);
    margin: 0;
    line-height: 1.4;
  }
</style>
