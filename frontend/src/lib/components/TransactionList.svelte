<script lang="ts">
  import { onMount } from 'svelte';
  import type { Transaction } from '$lib/api';
  import { CATEGORY_COLORS, formatCOP } from '$lib/api';
  import { createEventDispatcher } from 'svelte';

  export let transactions: Transaction[] = [];
  export let loading = false;

  const dispatch = createEventDispatcher<{ delete: number }>();

  let listEl: HTMLElement;

  const ICONS: Record<string, string> = {
    comida: '🍽️', transporte: '🚌', vivienda: '🏠',
    salud: '🏥', entretenimiento: '🎬', ropa: '👕',
    servicios: '⚡', salario: '💼', freelance: '💻',
    ventas: '🛒', inversiones: '📈', otro: '📌',
  };

  function catColor(category: string) {
    return CATEGORY_COLORS[category] ?? '#94a3b8';
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
  }

  onMount(async () => {
    if (!listEl || transactions.length === 0) return;
    const { gsap } = await import('gsap');
    gsap.from(listEl.querySelectorAll('.tx-item'), {
      opacity: 0,
      x: -12,
      stagger: 0.04,
      duration: 0.35,
      ease: 'power2.out',
      clearProps: 'all',
    });
  });
</script>

<div class="tx-list">
  <div class="tx-header">
    <span class="section-label">recientes</span>
    {#if transactions.length > 0}
      <span class="tx-count">{transactions.length}</span>
    {/if}
  </div>

  {#if loading}
    <div class="skeleton-list">
      {#each Array(5) as _}
        <div class="skeleton-item"></div>
      {/each}
    </div>
  {:else if transactions.length === 0}
    <div class="empty">
      <span class="empty-icon">💬</span>
      <span>Habla con Leaf para registrar tu primer gasto.</span>
    </div>
  {:else}
    <div class="tx-items" bind:this={listEl}>
      {#each transactions as tx (tx.id)}
        {@const color = catColor(tx.category)}
        <div class="tx-item" style="--cat: {color}">
          <div class="tx-accent"></div>
          <div class="tx-icon">{ICONS[tx.category] ?? '📌'}</div>
          <div class="tx-info">
            <span class="tx-desc">{tx.description}</span>
            <span class="tx-meta">
              {tx.category}{#if tx.merchant} · {tx.merchant}{/if} · {formatDate(tx.date)}
            </span>
          </div>
          <div class="tx-right">
            <span
              class="tx-amount"
              class:expense={tx.type === 'expense'}
              class:income={tx.type === 'income'}
            >
              {tx.type === 'expense' ? '−' : '+'}{formatCOP(tx.amount)}
            </span>
            <button
              class="tx-del"
              on:click={() => dispatch('delete', tx.id)}
              title="Eliminar"
            >×</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .tx-list {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  .tx-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px 10px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .section-label {
    font-size: 9px;
    color: var(--green);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .tx-count {
    font-size: 10px;
    color: var(--text-dim);
    background: var(--surface2);
    border: 1px solid var(--border);
    padding: 1px 7px;
    border-radius: 10px;
  }

  .tx-items {
    overflow-y: auto;
    flex: 1;
  }

  /* ── Transaction item ── */
  .tx-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px 10px 14px;
    border-bottom: 1px solid var(--border);
    position: relative;
    transition: background 0.15s;
    cursor: default;
  }

  .tx-item:hover { background: rgba(255,255,255,0.02); }

  /* Colored left accent line */
  .tx-accent {
    position: absolute;
    left: 0;
    top: 8px;
    bottom: 8px;
    width: 2px;
    border-radius: 1px;
    background: var(--cat);
    opacity: 0.7;
  }

  .tx-item:hover .tx-accent { opacity: 1; }

  .tx-icon {
    font-size: 16px;
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--surface2);
    border-radius: 6px;
    border: 1px solid var(--border);
  }

  .tx-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .tx-desc {
    font-size: 12px;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tx-meta {
    font-size: 10px;
    color: var(--text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .tx-right {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .tx-amount {
    font-size: 12px;
    font-weight: 500;
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
  }

  .tx-amount.expense { color: var(--red); }
  .tx-amount.income  { color: var(--green); }

  .tx-del {
    background: none;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 15px;
    padding: 0 3px;
    line-height: 1;
    opacity: 0;
    transition: opacity 0.15s, color 0.15s;
  }

  .tx-item:hover .tx-del { opacity: 1; }
  .tx-del:hover { color: var(--red); }

  /* ── Skeleton ── */
  .skeleton-list { padding: 8px 0; }
  .skeleton-item {
    height: 48px;
    margin: 4px 16px;
    border-radius: 6px;
    background: var(--surface2);
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  /* ── Empty ── */
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 40px 20px;
    color: var(--text-dim);
    font-size: 11px;
    text-align: center;
    line-height: 1.6;
  }

  .empty-icon { font-size: 28px; opacity: 0.4; }
</style>
