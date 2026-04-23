<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Chart as ChartType } from 'chart.js';
  import { formatCOP } from '$lib/api';

  interface MonthData {
    label: string;
    income: number;
    expenses: number;
  }

  let {
    data,
    showIncome = false,
  }: { data: MonthData[]; showIncome?: boolean } = $props();

  let canvas: HTMLCanvasElement;
  let chart: ChartType | null = null;

  onMount(async () => {
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    buildChart(Chart);
  });

  $effect(() => {
    if (!chart || !data) return;
    chart.data.labels = data.map(d => d.label);
    chart.data.datasets[0].data = data.map(d => d.expenses);
    if (showIncome && chart.data.datasets[1]) {
      chart.data.datasets[1].data = data.map(d => d.income);
    }
    chart.update('none');
  });

  function buildChart(Chart: typeof import('chart.js').Chart) {
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

    const gradientGreen = ctx.createLinearGradient(0, 0, 0, 240);
    gradientGreen.addColorStop(0, 'rgba(74, 222, 128, 0.28)');
    gradientGreen.addColorStop(0.65, 'rgba(74, 222, 128, 0.05)');
    gradientGreen.addColorStop(1, 'rgba(74, 222, 128, 0.00)');

    const gradientBlue = ctx.createLinearGradient(0, 0, 0, 240);
    gradientBlue.addColorStop(0, 'rgba(96, 165, 250, 0.22)');
    gradientBlue.addColorStop(1, 'rgba(96, 165, 250, 0.00)');

    const datasets: import('chart.js').ChartDataset<'line'>[] = [
      {
        label: 'Gastos',
        data: data.map(d => d.expenses),
        borderColor: '#4ade80',
        borderWidth: 2.5,
        backgroundColor: gradientGreen,
        fill: true,
        tension: 0.42,
        pointRadius: data.length > 6 ? 3 : 5,
        pointHoverRadius: 7,
        pointBackgroundColor: '#4ade80',
        pointBorderColor: '#141714',
        pointBorderWidth: 2,
      },
    ];

    if (showIncome) {
      datasets.push({
        label: 'Ingresos',
        data: data.map(d => d.income),
        borderColor: '#60a5fa',
        borderWidth: 2,
        backgroundColor: gradientBlue,
        fill: true,
        tension: 0.42,
        pointRadius: data.length > 6 ? 3 : 5,
        pointHoverRadius: 7,
        pointBackgroundColor: '#60a5fa',
        pointBorderColor: '#141714',
        pointBorderWidth: 2,
      });
    }

    chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.map(d => d.label),
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: showIncome,
            labels: {
              color: '#5a6a5a',
              font: { size: 11, family: 'Inter' },
              boxWidth: 10,
              padding: 10,
            },
          },
          tooltip: {
            backgroundColor: '#1d221d',
            borderColor: '#2d342d',
            borderWidth: 1,
            titleColor: '#5a6a5a',
            bodyColor: '#f0f0ef',
            padding: 10,
            cornerRadius: 8,
            callbacks: {
              label: (ctx: { dataset: { label?: string }; parsed: { y: number | null } }) =>
                ` ${ctx.dataset.label}: ${formatCOP(ctx.parsed.y ?? 0)}`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#5a6a5a', font: { size: 11, family: 'Inter' } },
            grid: { color: 'rgba(255,255,255,0.03)' },
            border: { display: false },
          },
          y: {
            ticks: {
              color: '#5a6a5a',
              font: { size: 11, family: 'Inter' },
              callback: (v: number | string) => {
                const n = Number(v);
                return n >= 1_000_000
                  ? `${(n / 1_000_000).toFixed(1)}M`
                  : `${(n / 1_000).toFixed(0)}k`;
              },
              maxTicksLimit: 5,
            },
            grid: { color: 'rgba(255,255,255,0.03)' },
            border: { display: false },
          },
        },
      },
    });
  }

  onDestroy(() => { chart?.destroy(); });
</script>

<div class="wrap">
  <canvas bind:this={canvas}></canvas>
</div>

<style>
  .wrap {
    width: 100%;
    height: 100%;
    min-height: 160px;
  }
  canvas { display: block; }
</style>
