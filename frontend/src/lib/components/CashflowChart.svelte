<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Chart as ChartType } from 'chart.js';
  import { formatCOP } from '$lib/api';

  interface MonthData {
    label: string;
    income: number;
    expenses: number;
  }

  let { data }: { data: MonthData[] } = $props();

  let canvas: HTMLCanvasElement;
  let chart: ChartType | null = null;

  onMount(async () => {
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    buildChart(Chart);
  });

  $effect(() => {
    if (chart && data) {
      chart.data.labels = data.map(d => d.label);
      chart.data.datasets[0].data = data.map(d => d.income);
      chart.data.datasets[1].data = data.map(d => d.expenses);
      chart.update();
    }
  });

  function buildChart(Chart: typeof import('chart.js').Chart) {
    chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: data.map(d => d.label),
        datasets: [
          {
            label: 'Ingresos',
            data: data.map(d => d.income),
            backgroundColor: 'rgba(34, 197, 94, 0.7)',
            borderColor: '#22c55e',
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: 'Gastos',
            data: data.map(d => d.expenses),
            backgroundColor: 'rgba(248, 113, 113, 0.7)',
            borderColor: '#f87171',
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#94a3b8', font: { size: 11 } },
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${formatCOP(ctx.parsed.y)}`,
            },
          },
        },
        scales: {
          x: { ticks: { color: '#64748b' }, grid: { color: '#1e293b' } },
          y: {
            ticks: {
              color: '#64748b',
              callback: v => `$${(Number(v) / 1_000_000).toFixed(1)}M`,
            },
            grid: { color: '#1e293b' },
          },
        },
      },
    });
  }

  onDestroy(() => { chart?.destroy(); });
</script>

<div class="chart-wrapper">
  <h3>Cashflow — Últimos 6 meses</h3>
  <div class="canvas-box">
    <canvas bind:this={canvas}></canvas>
  </div>
</div>

<style>
  .chart-wrapper { background: #1a2332; border-radius: 12px; padding: 16px; }
  h3 { font-size: 0.85rem; color: #94a3b8; margin: 0 0 12px; font-weight: 500; }
  .canvas-box { height: 180px; position: relative; }
</style>
