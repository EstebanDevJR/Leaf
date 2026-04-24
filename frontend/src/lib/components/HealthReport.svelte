<script lang="ts">
  import { onMount } from 'svelte';
  import { formatCOP } from '$lib/api';

  const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';

  interface HealthData {
    month: string;
    month_label: string;
    score: number;
    strengths: string[];
    improvements: string[];
    benchmark: string;
    next_month_goal: string;
    details: {
      savings_rate: number;
      coverage_months: number;
      active_goals: number;
      budget_violations: number;
      month_income: number;
      month_expenses: number;
    };
  }

  let data = $state<HealthData | null>(null);
  let loading = $state(true);
  let error = $state('');

  onMount(async () => {
    try {
      const res = await fetch(`${API_URL}/health/report`);
      if (!res.ok) throw new Error('Error al generar informe');
      data = await res.json();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error desconocido';
    } finally {
      loading = false;
    }
  });

  const scoreColor = $derived(
    data
      ? data.score >= 80 ? '#4ade80'
        : data.score >= 60 ? '#fbbf24'
        : '#f87171'
      : '#94a3b8'
  );

  const scoreLabel = $derived(
    data
      ? data.score >= 80 ? 'Excelente 🏆'
        : data.score >= 60 ? 'Bueno ✅'
        : data.score >= 40 ? 'Regular ⚠️'
        : 'Necesita atención 🚨'
      : ''
  );

  // Arc path for score gauge (SVG)
  const ARC_R = 54;
  const arcPath = $derived(() => {
    if (!data) return '';
    const pct = data.score / 100;
    const startAngle = -Math.PI * 0.75;
    const endAngle = startAngle + pct * Math.PI * 1.5;
    const x1 = 70 + ARC_R * Math.cos(startAngle);
    const y1 = 70 + ARC_R * Math.sin(startAngle);
    const x2 = 70 + ARC_R * Math.cos(endAngle);
    const y2 = 70 + ARC_R * Math.sin(endAngle);
    const large = pct > 0.667 ? 1 : 0;
    return `M ${x1} ${y1} A ${ARC_R} ${ARC_R} 0 ${large} 1 ${x2} ${y2}`;
  });
</script>

<div class="health">
  <div class="health-header">
    <span class="health-icon">🌿</span>
    <div>
      <h2 class="health-title">Salud Financiera</h2>
      <p class="health-sub">{data ? data.month_label : 'Cargando...'}</p>
    </div>
  </div>

  {#if loading}
    <div class="loading">Calculando tu score...</div>
  {:else if error}
    <div class="error-msg">{error}</div>
  {:else if data}

    <!-- Score gauge -->
    <div class="gauge-wrap">
      <svg viewBox="0 0 140 90" class="gauge-svg">
        <!-- Track -->
        <path
          d="M {70 + ARC_R * Math.cos(-Math.PI * 0.75)} {70 + ARC_R * Math.sin(-Math.PI * 0.75)}
             A {ARC_R} {ARC_R} 0 1 1
             {70 + ARC_R * Math.cos(-Math.PI * 0.75 + Math.PI * 1.5)} {70 + ARC_R * Math.sin(-Math.PI * 0.75 + Math.PI * 1.5)}"
          fill="none"
          stroke="#1d221d"
          stroke-width="10"
          stroke-linecap="round"
        />
        <!-- Fill -->
        {#if data.score > 0}
          <path
            d={arcPath()}
            fill="none"
            stroke={scoreColor}
            stroke-width="10"
            stroke-linecap="round"
          />
        {/if}
        <!-- Score number -->
        <text x="70" y="62" text-anchor="middle" class="gauge-num" style="fill:{scoreColor}">
          {data.score}
        </text>
        <text x="70" y="75" text-anchor="middle" class="gauge-sub">/100</text>
      </svg>
      <div class="score-label" style="color:{scoreColor}">{scoreLabel}</div>
    </div>

    <!-- Stats row -->
    <div class="stats-row">
      <div class="stat-chip">
        <span class="stat-val">{data.details.savings_rate.toFixed(1)}%</span>
        <span class="stat-lbl">tasa ahorro</span>
      </div>
      <div class="stat-chip">
        <span class="stat-val">{data.details.coverage_months.toFixed(1)}m</span>
        <span class="stat-lbl">fondo emerg.</span>
      </div>
      <div class="stat-chip">
        <span class="stat-val">{data.details.active_goals}</span>
        <span class="stat-lbl">metas activas</span>
      </div>
      <div class="stat-chip" class:warn={data.details.budget_violations > 0}>
        <span class="stat-val">{data.details.budget_violations}</span>
        <span class="stat-lbl">pres. excedidos</span>
      </div>
    </div>

    <!-- Strengths -->
    {#if data.strengths.length > 0}
      <div class="section">
        <div class="section-title">Fortalezas</div>
        <div class="items-list">
          {#each data.strengths as s}
            <div class="item strength">
              <span class="item-dot green"></span>
              <span>{s}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Improvements -->
    {#if data.improvements.length > 0}
      <div class="section">
        <div class="section-title">Áreas de mejora</div>
        <div class="items-list">
          {#each data.improvements as imp}
            <div class="item improvement">
              <span class="item-dot yellow"></span>
              <span>{imp}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Benchmark + next goal -->
    <div class="benchmark-card">
      <div class="benchmark-text">📊 {data.benchmark}</div>
    </div>

    <div class="next-goal">
      <div class="next-lbl">Meta del próximo mes</div>
      <div class="next-text">{data.next_month_goal}</div>
    </div>

  {/if}
</div>

<style>
  .health {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 0;
  }

  .health-header { display: flex; align-items: center; gap: 12px; }
  .health-icon { font-size: 28px; }

  .health-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .health-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin: 0;
    text-transform: capitalize;
  }

  .loading, .error-msg {
    font-size: 12px;
    color: var(--text-dim);
    text-align: center;
    padding: 24px;
  }

  .error-msg { color: var(--red); }

  /* Gauge */
  .gauge-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .gauge-svg { width: 160px; height: 100px; }

  .gauge-num {
    font-family: 'Inter', sans-serif;
    font-size: 28px;
    font-weight: 800;
  }

  .gauge-sub {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    fill: #5a6a5a;
  }

  .score-label {
    font-size: 14px;
    font-weight: 700;
    font-family: 'Inter', sans-serif;
  }

  /* Stats row */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }

  .stat-chip {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .stat-chip.warn { border-color: rgba(248,113,113,0.3); }

  .stat-val {
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
    font-family: 'Inter', sans-serif;
  }

  .stat-lbl {
    font-size: 9px;
    color: var(--text-dim);
    line-height: 1.2;
  }

  /* Sections */
  .section { display: flex; flex-direction: column; gap: 6px; }

  .section-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .items-list { display: flex; flex-direction: column; gap: 5px; }

  .item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 12px;
    color: var(--text-mid);
    line-height: 1.4;
  }

  .item-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 4px;
  }

  .item-dot.green { background: #4ade80; }
  .item-dot.yellow { background: #fbbf24; }

  /* Benchmark */
  .benchmark-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
  }

  .benchmark-text {
    font-size: 12px;
    color: var(--text-mid);
    line-height: 1.4;
  }

  /* Next goal */
  .next-goal {
    background: rgba(74,222,128,0.06);
    border: 1px solid rgba(74,222,128,0.2);
    border-radius: 10px;
    padding: 10px 14px;
  }

  .next-lbl {
    font-size: 10px;
    color: var(--text-dim);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .next-text {
    font-size: 12px;
    color: var(--text);
    line-height: 1.4;
  }
</style>
