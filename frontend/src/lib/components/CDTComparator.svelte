<script lang="ts">
  import { formatCOP } from '$lib/api';

  const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';
  const TERMS = [3, 6, 12, 24];

  let monto = $state(5_000_000);
  let plazo = $state(12);
  let loading = $state(false);
  let result = $state<null | {
    is_live: boolean;
    source_date: string;
    plazo_meses: number;
    monto: number;
    retencion_pct: number;
    inflacion_pct: number;
    banks: Array<{
      bank: string;
      rate_ea: number;
      tasa_neta_ea: number;
      tasa_real_ea: number;
      beats_inflation: boolean;
      rendimiento_bruto: number;
      retencion: number;
      rendimiento_neto: number;
      monto_final: number;
    }>;
    best: { bank: string; tasa_neta_ea: number; rendimiento_neto: number; monto_final: number } | null;
  }>(null);
  let error = $state('');

  async function compare() {
    loading = true;
    error = '';
    result = null;
    try {
      const res = await fetch(`${API_URL}/health/cdt-comparison?monto=${monto}&plazo=${plazo}`);
      if (!res.ok) throw new Error('Error al consultar tasas');
      result = await res.json();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error desconocido';
    } finally {
      loading = false;
    }
  }
</script>

<div class="cdt">
  <div class="cdt-header">
    <span class="cdt-icon">💎</span>
    <div>
      <h2 class="cdt-title">Comparador de CDT</h2>
      <p class="cdt-sub">Rentabilidad real después de retención (7%) vs inflación (5.5%)</p>
    </div>
  </div>

  <!-- Inputs -->
  <div class="inputs">
    <div class="input-group">
      <label class="input-lbl">Monto a invertir (COP)</label>
      <div class="input-wrap">
        <span class="prefix">$</span>
        <input
          type="number"
          min="0"
          step="500000"
          bind:value={monto}
          class="num-input"
          placeholder="5000000"
        />
      </div>
    </div>

    <div class="input-group">
      <label class="input-lbl">Plazo</label>
      <div class="term-btns">
        {#each TERMS as t}
          <button
            class="term-btn"
            class:active={plazo === t}
            onclick={() => plazo = t}
          >{t} meses</button>
        {/each}
      </div>
    </div>
  </div>

  <button class="compare-btn" onclick={compare} disabled={loading}>
    {loading ? 'Consultando...' : 'Comparar tasas'}
  </button>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if result}
    <!-- Best option highlight -->
    {#if result.best}
      <div class="best-card">
        <div class="best-badge">Mejor opción hoy</div>
        <div class="best-bank">{result.best.bank}</div>
        <div class="best-rate">{result.banks[0]?.tasa_neta_ea.toFixed(2)}% neta EA</div>
        {#if monto > 0}
          <div class="best-return">
            Recibirías: <strong>{formatCOP(result.best.monto_final)}</strong>
            <span class="best-gain"> (+{formatCOP(result.best.rendimiento_neto)} neto)</span>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Info bar -->
    <div class="info-bar">
      <span>
        {result.is_live ? '🟢 Fuente: SFC · ' : '🟡 Referencia · '}
        {result.source_date}
      </span>
      <span>Retención: {result.retencion_pct}% · Inflación: {result.inflacion_pct}%</span>
    </div>

    <!-- Bank table -->
    <div class="bank-list">
      {#each result.banks as bank, i}
        <div class="bank-row" class:top={i === 0} class:no-beat={!bank.beats_inflation}>
          <div class="bank-rank">#{i + 1}</div>
          <div class="bank-info">
            <div class="bank-name">{bank.bank}</div>
            <div class="bank-rates">
              <span class="rate-gross">{bank.rate_ea.toFixed(1)}% bruta</span>
              <span class="sep">→</span>
              <span class="rate-net" class:positive={bank.beats_inflation}>{bank.tasa_neta_ea.toFixed(2)}% neta</span>
              <span class="rate-real" class:beats={bank.beats_inflation} class:no-beats={!bank.beats_inflation}>
                {bank.beats_inflation ? `+${bank.tasa_real_ea.toFixed(2)}% real` : `${bank.tasa_real_ea.toFixed(2)}% real`}
              </span>
            </div>
          </div>
          {#if monto > 0}
            <div class="bank-return">
              <div class="return-final">{formatCOP(bank.monto_final)}</div>
              <div class="return-gain">+{formatCOP(bank.rendimiento_neto)}</div>
              <div class="return-ret">-{formatCOP(bank.retencion)} ret.</div>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <p class="disclaimer">
      ⚠️ Tasas reportadas por cada entidad a la Superfinanciera (SFC). Retención en la fuente: 7%.
      Las tasas varían según monto y condiciones. Verifica directamente con cada banco.
    </p>
  {/if}
</div>

<style>
  .cdt {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 0;
  }

  .cdt-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .cdt-icon { font-size: 28px; }

  .cdt-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .cdt-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin: 0;
  }

  .inputs {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .input-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .input-lbl {
    font-size: 11px;
    color: var(--text-dim);
  }

  .input-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 12px;
  }

  .prefix { color: var(--text-dim); font-size: 12px; }

  .num-input {
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

  .term-btns {
    display: flex;
    gap: 6px;
  }

  .term-btn {
    flex: 1;
    padding: 7px 0;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
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

  .compare-btn {
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

  .compare-btn:disabled { opacity: 0.6; cursor: wait; }
  .compare-btn:not(:disabled):hover { opacity: 0.9; }

  .error {
    font-size: 12px;
    color: var(--red);
    text-align: center;
    margin: 0;
  }

  .best-card {
    background: rgba(74,222,128,0.06);
    border: 1px solid rgba(74,222,128,0.25);
    border-radius: 12px;
    padding: 14px 16px;
    position: relative;
  }

  .best-badge {
    position: absolute;
    top: -9px;
    left: 12px;
    background: #3a6b3a;
    color: #e8f5e8;
    font-size: 9px;
    padding: 2px 10px;
    border-radius: 6px;
    font-weight: 600;
  }

  .best-bank {
    font-size: 14px;
    font-weight: 700;
    color: var(--text);
  }

  .best-rate {
    font-size: 20px;
    font-weight: 800;
    color: #4ade80;
    font-family: 'Inter', sans-serif;
    margin: 2px 0;
  }

  .best-return {
    font-size: 13px;
    color: var(--text-mid);
  }

  .best-gain {
    color: #4ade80;
    font-weight: 600;
  }

  .info-bar {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: var(--text-dim);
    padding: 4px 0;
  }

  .bank-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .bank-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    transition: border-color 0.15s;
  }

  .bank-row.top { border-color: rgba(74,222,128,0.3); }
  .bank-row.no-beat { opacity: 0.75; }

  .bank-rank {
    font-size: 11px;
    color: var(--text-dim);
    min-width: 20px;
  }

  .bank-info { flex: 1; min-width: 0; }

  .bank-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bank-rates {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-wrap: wrap;
    margin-top: 2px;
  }

  .rate-gross { font-size: 11px; color: var(--text-dim); }
  .sep { font-size: 11px; color: var(--text-dim); }

  .rate-net {
    font-size: 11px;
    color: var(--text-mid);
    font-weight: 600;
  }

  .rate-net.positive { color: #4ade80; }

  .rate-real {
    font-size: 10px;
    padding: 1px 5px;
    border-radius: 4px;
    font-weight: 600;
  }

  .rate-real.beats { background: rgba(74,222,128,0.12); color: #4ade80; }
  .rate-real.no-beats { background: rgba(248,113,113,0.1); color: #f87171; }

  .bank-return {
    text-align: right;
    flex-shrink: 0;
  }

  .return-final {
    font-size: 12px;
    font-weight: 700;
    color: var(--text);
    font-family: 'Inter', sans-serif;
  }

  .return-gain {
    font-size: 10px;
    color: #4ade80;
    font-weight: 600;
  }

  .return-ret {
    font-size: 10px;
    color: var(--text-dim);
  }

  .disclaimer {
    font-size: 10px;
    color: var(--text-dim);
    line-height: 1.4;
    margin: 0;
  }
</style>
