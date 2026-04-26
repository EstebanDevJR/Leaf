<script lang="ts">
  import { fly } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';
  import Stats from './Stats.svelte';
  import TransactionList from './TransactionList.svelte';
  import type { Budget, Stats as StatsType, Transaction } from '$lib/api';

  export let transactions: Transaction[] = [];
  export let stats: StatsType | null = null;
  export let budgets: Budget[] = [];
  export let loading = false;

  const dispatch = createEventDispatcher<{ close: void; delete: number }>();
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="overlay" on:click={() => dispatch('close')}></div>

<aside class="drawer" transition:fly={{ x: 420, duration: 220, opacity: 1 }}>
  <div class="drawer-header">
    <span class="drawer-title">transacciones</span>
    <button class="close-btn" on:click={() => dispatch('close')}>✕</button>
  </div>

  <div class="stats-wrap">
    <Stats {stats} {budgets} {loading} />
  </div>

  <div class="list-wrap">
    <TransactionList
      {transactions}
      {loading}
      on:delete={(e) => dispatch('delete', e.detail)}
    />
  </div>
</aside>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(22, 34, 25, 0.35);
    backdrop-filter: blur(4px);
    z-index: 50;
  }

  .drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 420px;
    max-width: 95vw;
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(32px) saturate(200%);
    -webkit-backdrop-filter: blur(32px) saturate(200%);
    border-left: 1px solid rgba(255, 255, 255, 0.92);
    box-shadow: -8px 0 48px rgba(52, 100, 68, 0.14);
    z-index: 51;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(74, 124, 89, 0.12);
    background: rgba(255, 255, 255, 0.40);
    flex-shrink: 0;
  }

  .drawer-title {
    font-size: 10px;
    color: var(--green);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    font-weight: 600;
  }

  .close-btn {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    border: 1px solid rgba(74, 124, 89, 0.18);
    background: rgba(255, 255, 255, 0.60);
    color: var(--text-dim);
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    transition: background 0.15s, color 0.15s;
  }

  .close-btn:hover { background: rgba(192, 80, 80, 0.10); color: var(--red); }

  .stats-wrap {
    flex-shrink: 0;
    border-bottom: 1px solid rgba(74, 124, 89, 0.10);
  }

  .list-wrap {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
</style>
