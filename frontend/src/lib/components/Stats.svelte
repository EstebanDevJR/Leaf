<script lang="ts">
  import { onMount } from 'svelte';
  import type { Budget, Stats } from '$lib/api';
  import { CATEGORY_COLORS, formatCOP } from '$lib/api';

  export let stats: Stats | null = null;
  export let budgets: Budget[] = [];
  export let loading = false;

  interface BudgetAlert {
    category: string;
    spent: number;
    limit: number;
    pct: number;
    color: string;
  }

  $: budgetAlerts = (() => {
    if (!stats || !budgets.length) return [];
    const spent = stats.expenses_by_category ?? {};
    return budgets
      .map((b): BudgetAlert => ({
        category: b.category,
        spent: spent[b.category] ?? 0,
        limit: b.monthly_limit,
        pct: b.monthly_limit > 0 ? ((spent[b.category] ?? 0) / b.monthly_limit) * 100 : 0,
        color: CATEGORY_COLORS[b.category] ?? '#94a3b8',
      }))
      .filter(a => a.pct >= 70)
      .sort((a, b) => b.pct - a.pct);
  })();

  // ── Donut chart ────────────────────────────────────────────────────────────
  const R = 36;
  const SW = 8;
  const C = 2 * Math.PI * R;
  const VB = 100;
  const CX = VB / 2;

  interface Seg {
    name: string;
    amount: number;
    pct: number;
    color: string;
    dashLength: number;
    dashOffset: number;
  }

  function buildSegments(byCategory: Record<string, number>): Seg[] {
    const entries = Object.entries(byCategory)
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
    const total = entries.reduce((s, [, v]) => s + v, 0);
    if (!total) return [];
    let cum = 0;
    return entries.map(([name, amount]) => {
      const pct = amount / total;
      const dashLength = pct * C;
      const seg: Seg = {
        name, amount,
        pct: pct * 100,
        color: CATEGORY_COLORS[name] ?? '#94a3b8',
        dashLength,
        dashOffset: -cum,
      };
      cum += dashLength;
      return seg;
    });
  }

  $: segments = stats ? buildSegments(stats.expenses_by_category ?? {}) : [];
  $: spendRatio = stats && stats.total_income > 0
    ? Math.min((stats.total_expenses / stats.total_income) * 100, 100)
    : 0;

  const now = new Date();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const today = now.getDate();
  const monthPct = Math.round((today / daysInMonth) * 100);

  // ── DOM refs for GSAP ──────────────────────────────────────────────────────
  let balanceEl: HTMLElement;
  let incomeEl: HTMLElement;
  let expenseEl: HTMLElement;
  let donutEls: SVGCircleElement[] = [];
  let barEls: HTMLElement[] = [];
  let panelEl: HTMLElement;

  // ── GSAP ───────────────────────────────────────────────────────────────────
  onMount(async () => {
    if (!stats) return;
    const { gsap } = await import('gsap');

    // Panel fade-in
    gsap.from(panelEl, { opacity: 0, duration: 0.4, ease: 'power2.out' });

    // Number counters
    function counter(el: HTMLElement | undefined, target: number, prefix = '') {
      if (!el) return;
      const obj = { v: 0 };
      gsap.to(obj, {
        v: target,
        duration: 1.4,
        ease: 'power3.out',
        onUpdate() {
          el.textContent = prefix + formatCOP(Math.round(obj.v));
        },
      });
    }

    counter(balanceEl, stats.balance, stats.balance >= 0 ? '+' : '');
    counter(incomeEl, stats.total_income);
    counter(expenseEl, stats.total_expenses);

    // Donut segments — grow from 0 to target length
    donutEls.forEach((el, i) => {
      if (!el) return;
      const seg = segments[i];
      if (!seg) return;
      const obj = { progress: 0 };
      gsap.to(obj, {
        progress: 1,
        duration: 1,
        delay: 0.4 + i * 0.09,
        ease: 'power3.out',
        onUpdate() {
          const len = obj.progress * seg.dashLength;
          el.setAttribute('stroke-dasharray', `${len} ${C - len}`);
        },
      });
    });

    // Category bars
    barEls.forEach((el, i) => {
      if (!el) return;
      gsap.from(el, {
        scaleX: 0,
        transformOrigin: 'left center',
        duration: 0.9,
        delay: 0.6 + i * 0.07,
        ease: 'power3.out',
      });
    });
  });
</script>

<div class="stats-panel" bind:this={panelEl}>

  {#if loading}
    <div class="skeleton-wrap">
      <div class="skeleton h40"></div>
      <div class="skeleton-row">
        <div class="skeleton h24"></div>
        <div class="skeleton h24"></div>
      </div>
    </div>

  {:else if stats}

    <!-- ── Balance card ── -->
    <div class="balance-card" class:positive={stats.balance >= 0} class:negative={stats.balance < 0}>
      <div class="balance-label">balance mensual</div>
      <div class="balance-value" bind:this={balanceEl}>
        {stats.balance >= 0 ? '+' : ''}{formatCOP(stats.balance)}
      </div>

      <!-- Spend ratio bar -->
      <div class="ratio-row">
        <div class="ratio-track">
          <div
            class="ratio-fill"
            style="width: {spendRatio}%; background: {spendRatio > 85 ? 'var(--red)' : spendRatio > 60 ? 'var(--amber)' : 'var(--green)'}"
          ></div>
        </div>
        <span class="ratio-label">{Math.round(spendRatio)}% del ingreso · día {today}/{daysInMonth}</span>
      </div>
    </div>

    <!-- ── Sub metrics ── -->
    <div class="sub-row">
      <div class="sub-card income-card">
        <span class="sub-label">ingresos</span>
        <span class="sub-value green" bind:this={incomeEl}>{formatCOP(stats.total_income)}</span>
      </div>
      <div class="sub-card expense-card">
        <span class="sub-label">gastos</span>
        <span class="sub-value amber" bind:this={expenseEl}>{formatCOP(stats.total_expenses)}</span>
      </div>
    </div>

    <!-- ── Budget alerts ── -->
    {#if budgetAlerts.length > 0}
      <div class="alerts-section">
        <div class="alerts-label">presupuestos</div>
        {#each budgetAlerts as alert}
          {@const over = alert.pct > 100}
          {@const warn = alert.pct >= 80 && !over}
          <div class="alert-row" class:over class:warn>
            <div class="alert-header">
              <span class="alert-cat">{alert.category}</span>
              <span class="alert-badge" class:over class:warn>
                {over ? '🔴' : '🟡'} {alert.pct.toFixed(0)}%
              </span>
            </div>
            <div class="alert-track">
              <div
                class="alert-fill"
                style="width:{Math.min(alert.pct, 100)}%; background:{over ? 'var(--red)' : warn ? 'var(--amber)' : alert.color}"
              ></div>
            </div>
            <div class="alert-sub">
              {formatCOP(alert.spent)} / {formatCOP(alert.limit)}
              {#if over}
                · excedido {formatCOP(alert.spent - alert.limit)}
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}

    <!-- ── Donut + legend ── -->
    {#if segments.length > 0}
      <div class="chart-section">
        <div class="donut-wrap">
          <svg viewBox="0 0 {VB} {VB}" class="donut-svg">
            <!-- Track -->
            <circle
              cx={CX} cy={CX} r={R}
              fill="none"
              stroke="var(--surface2)"
              stroke-width={SW}
            />
            <!-- Segments (start from top via rotate(-90)) -->
            <g transform="rotate(-90 {CX} {CX})">
              {#each segments as seg, i}
                <circle
                  bind:this={donutEls[i]}
                  cx={CX} cy={CX} r={R}
                  fill="none"
                  stroke={seg.color}
                  stroke-width={SW}
                  stroke-dasharray="0 {C}"
                  stroke-dashoffset={seg.dashOffset}
                  stroke-linecap="butt"
                />
              {/each}
            </g>
            <!-- Center label -->
            <text x={CX} y={CX - 5} text-anchor="middle" class="donut-center-label">gastos</text>
            <text x={CX} y={CX + 9} text-anchor="middle" class="donut-center-value">
              {stats.transaction_count}tx
            </text>
          </svg>
        </div>

        <div class="legend">
          {#each segments as seg}
            <div class="legend-item">
              <span class="legend-dot" style="background:{seg.color}; box-shadow: 0 0 6px {seg.color}66"></span>
              <span class="legend-name">{seg.name}</span>
              <span class="legend-pct" style="color:{seg.color}">{seg.pct.toFixed(0)}%</span>
            </div>
          {/each}
        </div>
      </div>

      <!-- ── Category bars ── -->
      <div class="bars-section">
        <div class="bars-label">distribución</div>
        {#each segments as seg, i}
          <div class="bar-row">
            <div class="bar-header">
              <span class="bar-name">{seg.name}</span>
              <span class="bar-amount" style="color:{seg.color}">{formatCOP(seg.amount)}</span>
            </div>
            <div class="bar-track">
              <div
                bind:this={barEls[i]}
                class="bar-fill"
                style="width:{seg.pct}%; background: linear-gradient(90deg, {seg.color}cc, {seg.color}66)"
              ></div>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="no-data">sin gastos registrados este mes</div>
    {/if}

  {:else}
    <div class="no-data">sin datos · habla con Leaf para empezar</div>
  {/if}

</div>

<style>
  .stats-panel {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ── Balance card ── */
  .balance-card {
    border-radius: 10px;
    padding: 18px 20px 14px;
    position: relative;
    overflow: hidden;
  }

  .balance-card.positive {
    background: linear-gradient(135deg, rgba(74, 222, 128, 0.1) 0%, rgba(74, 222, 128, 0.03) 100%);
    border: 1px solid rgba(74, 222, 128, 0.25);
  }

  .balance-card.negative {
    background: linear-gradient(135deg, rgba(248, 113, 113, 0.1) 0%, rgba(248, 113, 113, 0.03) 100%);
    border: 1px solid rgba(248, 113, 113, 0.25);
  }

  /* Subtle corner glow */
  .balance-card::before {
    content: '';
    position: absolute;
    top: -30px;
    right: -30px;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(74, 222, 128, 0.15) 0%, transparent 70%);
    pointer-events: none;
  }

  .balance-card.negative::before {
    background: radial-gradient(circle, rgba(248, 113, 113, 0.15) 0%, transparent 70%);
  }

  .balance-label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }

  .balance-value {
    font-family: 'Playfair Display', serif;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1;
    margin-bottom: 12px;
    background: linear-gradient(135deg, #4ade80, #86efac);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .balance-card.negative .balance-value {
    background: linear-gradient(135deg, #f87171, #fca5a5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* Ratio bar */
  .ratio-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ratio-track {
    height: 3px;
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
    overflow: hidden;
  }

  .ratio-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .ratio-label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.06em;
  }

  /* ── Sub metrics ── */
  .sub-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .sub-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .income-card { border-color: rgba(74, 222, 128, 0.15); }
  .expense-card { border-color: rgba(251, 191, 36, 0.15); }

  .sub-label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .sub-value {
    font-size: 14px;
    font-weight: 500;
    letter-spacing: -0.01em;
  }

  .sub-value.green { color: var(--green); }
  .sub-value.amber { color: var(--amber); }

  /* ── Budget alerts ── */
  .alerts-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .alerts-label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 2px;
  }

  .alert-row {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .alert-row.warn { border-color: rgba(251, 191, 36, 0.3); }
  .alert-row.over { border-color: rgba(248, 113, 113, 0.3); }

  .alert-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .alert-cat {
    font-size: 11px;
    color: var(--text);
    font-weight: 500;
  }

  .alert-badge {
    font-size: 10px;
    font-weight: 500;
    padding: 1px 7px;
    border-radius: 10px;
  }

  .alert-badge.warn {
    background: rgba(251, 191, 36, 0.12);
    color: var(--amber);
    border: 1px solid rgba(251, 191, 36, 0.2);
  }

  .alert-badge.over {
    background: rgba(248, 113, 113, 0.12);
    color: var(--red);
    border: 1px solid rgba(248, 113, 113, 0.2);
  }

  .alert-track {
    height: 3px;
    background: rgba(255,255,255,0.06);
    border-radius: 2px;
    overflow: hidden;
  }

  .alert-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
  }

  .alert-sub {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.03em;
  }

  /* ── Donut chart ── */
  .chart-section {
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .donut-wrap {
    flex-shrink: 0;
    width: 90px;
    height: 90px;
    position: relative;
  }

  .donut-svg { width: 100%; height: 100%; }

  .donut-center-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 8px;
    fill: var(--text-dim);
    letter-spacing: 0.05em;
  }

  .donut-center-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    fill: var(--text);
    font-weight: 500;
  }

  /* ── Legend ── */
  .legend {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 0;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 10px;
  }

  .legend-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legend-name {
    color: var(--text-mid);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .legend-pct {
    font-size: 10px;
    font-weight: 500;
    flex-shrink: 0;
  }

  /* ── Category bars ── */
  .bars-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .bars-label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 2px;
  }

  .bar-row { display: flex; flex-direction: column; gap: 4px; }

  .bar-header {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
  }

  .bar-name { color: var(--text-mid); }
  .bar-amount { font-weight: 500; }

  .bar-track {
    height: 3px;
    background: var(--surface2);
    border-radius: 2px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 2px;
    min-width: 2px;
  }

  /* ── Skeleton ── */
  .skeleton-wrap { display: flex; flex-direction: column; gap: 10px; }
  .skeleton-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .skeleton {
    background: var(--surface2);
    border-radius: 8px;
    animation: shimmer 1.5s infinite;
  }
  .h40 { height: 80px; }
  .h24 { height: 56px; }

  @keyframes shimmer {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  /* ── No data ── */
  .no-data {
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
    padding: 20px;
    letter-spacing: 0.05em;
  }
</style>
