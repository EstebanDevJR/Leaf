<script lang="ts">
  import { formatCOP, simulateWhatIf } from '$lib/api';
  import type { WhatIfResult } from '$lib/api';

  const SCENARIOS = [
    { value: 'ahorro_mas',     label: '¿Y si ahorro más?',             icon: '💰' },
    { value: 'gasto_menos',    label: '¿Y si gasto menos?',            icon: '✂️' },
    { value: 'ingreso_mas',    label: '¿Y si gano más?',               icon: '📈' },
    { value: 'categoria_cero', label: '¿Y si elimino un gasto fijo?',  icon: '🚫' },
  ];

  const PROJECTIONS = [
    { key: '1',  label: '1 mes' },
    { key: '3',  label: '3 meses' },
    { key: '6',  label: '6 meses' },
    { key: '12', label: '1 año' },
    { key: '24', label: '2 años' },
    { key: '60', label: '5 años' },
  ];

  let scenario = $state('ahorro_mas');
  let changePct = $state(10);
  let changeAmount = $state(0);
  let useAmount = $state(false);
  let result = $state<WhatIfResult | null>(null);
  let loading = $state(false);
  let error = $state('');

  async function simulate() {
    loading = true;
    error = '';
    result = null;
    try {
      result = await simulateWhatIf({
        scenario,
        change_pct: useAmount ? 0 : changePct,
        change_amount: useAmount ? changeAmount : 0,
      });
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error en la simulación';
    } finally {
      loading = false;
    }
  }
</script>

<div class="sim">
  <div class="sim-header">
    <span class="sim-icon">🔮</span>
    <div>
      <h2 class="sim-title">Simulador What-If</h2>
      <p class="sim-sub">Proyecta el impacto de cambios en tus finanzas</p>
    </div>
  </div>

  <!-- Scenario selector -->
  <div class="scenario-grid">
    {#each SCENARIOS as sc}
      <button
        class="sc-btn"
        class:active={scenario === sc.value}
        onclick={() => { scenario = sc.value; result = null; }}
      >
        <span class="sc-icon">{sc.icon}</span>
        <span class="sc-label">{sc.label}</span>
      </button>
    {/each}
  </div>

  <!-- Amount input -->
  <div class="input-row">
    <div class="toggle-type">
      <button class="type-btn" class:active={!useAmount} onclick={() => useAmount = false}>
        Porcentaje
      </button>
      <button class="type-btn" class:active={useAmount} onclick={() => useAmount = true}>
        Monto fijo
      </button>
    </div>

    {#if !useAmount}
      <div class="slider-wrap">
        <div class="slider-labels">
          <span>1%</span>
          <span class="slider-value">{changePct}%</span>
          <span>50%</span>
        </div>
        <input
          type="range"
          min="1" max="50" step="1"
          bind:value={changePct}
          class="slider"
        />
      </div>
    {:else}
      <div class="amount-wrap">
        <span class="currency-prefix">$</span>
        <input
          type="number"
          min="0"
          step="50000"
          bind:value={changeAmount}
          class="amount-input"
          placeholder="500000"
        />
        <span class="currency-suffix">COP / mes</span>
      </div>
    {/if}
  </div>

  <button class="sim-btn" onclick={simulate} disabled={loading}>
    {loading ? 'Calculando...' : 'Simular escenario'}
  </button>

  {#if error}
    <p class="error-msg">{error}</p>
  {/if}

  <!-- Results -->
  {#if result}
    <div class="results">
      <div class="result-header">
        <span class="result-label">{result.label}</span>
        <span class="result-extra">+{formatCOP(result.monthly_diff)}/mes</span>
      </div>

      <div class="base-row">
        <div class="base-item">
          <span class="base-lbl">Ahorro actual/mes</span>
          <span class="base-val">{formatCOP(result.base_savings)}</span>
        </div>
        <span class="arrow">→</span>
        <div class="base-item">
          <span class="base-lbl">Nuevo ahorro/mes</span>
          <span class="base-val positive">{formatCOP(result.new_savings)}</span>
        </div>
      </div>

      <div class="proj-title">Ahorro acumulado extra vs. sin cambio:</div>
      <div class="proj-grid">
        {#each PROJECTIONS as p}
          {@const proj = result.projections[p.key]}
          {#if proj}
            <div class="proj-card">
              <div class="proj-period">{p.label}</div>
              <div class="proj-extra">+{formatCOP(proj.extra_savings)}</div>
              <div class="proj-total">Total: {formatCOP(proj.total_savings)}</div>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .sim {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 4px 0;
  }

  .sim-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .sim-icon { font-size: 28px; }

  .sim-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .sim-sub {
    font-size: 12px;
    color: var(--text-dim);
    margin: 0;
  }

  .scenario-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .sc-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text-mid);
    font-family: inherit;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s, color 0.15s;
  }

  .sc-btn.active {
    border-color: var(--green-dim);
    color: var(--text);
    background: rgba(90,170,90,0.08);
  }

  .sc-icon { font-size: 16px; flex-shrink: 0; }
  .sc-label { line-height: 1.3; }

  .input-row {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .toggle-type {
    display: flex;
    gap: 6px;
  }

  .type-btn {
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

  .type-btn.active {
    border-color: var(--green-dim);
    color: var(--text);
  }

  .slider-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-dim);
    margin-bottom: 4px;
  }

  .slider-value {
    color: var(--green-bright);
    font-weight: 700;
    font-size: 13px;
  }

  .slider {
    width: 100%;
    accent-color: #4ade80;
    cursor: pointer;
  }

  .amount-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 12px;
  }

  .currency-prefix, .currency-suffix {
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

  .amount-input::placeholder { color: var(--text-dim); }

  .sim-btn {
    padding: 12px;
    background: linear-gradient(135deg, #3a6b3a, #5aaa5a);
    border: none;
    border-radius: 12px;
    color: #e8f5e8;
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .sim-btn:disabled { opacity: 0.6; cursor: wait; }
  .sim-btn:not(:disabled):hover { opacity: 0.9; }

  .error-msg {
    font-size: 12px;
    color: var(--red);
    text-align: center;
    margin: 0;
  }

  .results {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    background: rgba(90,170,90,0.06);
    border: 1px solid rgba(90,170,90,0.15);
    border-radius: 12px;
  }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .result-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }

  .result-extra {
    font-size: 13px;
    color: #4ade80;
    font-weight: 700;
  }

  .base-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .base-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .base-lbl {
    font-size: 10px;
    color: var(--text-dim);
  }

  .base-val {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
    font-family: 'Inter', sans-serif;
  }

  .base-val.positive { color: #4ade80; }

  .arrow {
    color: var(--text-dim);
    font-size: 18px;
    flex-shrink: 0;
  }

  .proj-title {
    font-size: 11px;
    color: var(--text-dim);
  }

  .proj-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .proj-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 8px;
    text-align: center;
  }

  .proj-period {
    font-size: 10px;
    color: var(--text-dim);
    margin-bottom: 4px;
  }

  .proj-extra {
    font-size: 13px;
    font-weight: 700;
    color: #4ade80;
    font-family: 'Inter', sans-serif;
  }

  .proj-total {
    font-size: 10px;
    color: var(--text-dim);
    margin-top: 2px;
  }
</style>
