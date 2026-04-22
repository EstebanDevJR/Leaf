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
    background: rgba(0, 0, 0, 0.5);
    z-index: 50;
  }

  .drawer {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 400px;
    max-width: 95vw;
    background: var(--surface);
    border-left: 1px solid var(--border);
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
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .drawer-title {
    font-size: 10px;
    color: var(--green);
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 16px;
    padding: 4px 6px;
    border-radius: 3px;
    line-height: 1;
    transition: color 0.15s;
  }

  .close-btn:hover { color: var(--text); }

  .stats-wrap {
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
  }

  .list-wrap {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
</style>
