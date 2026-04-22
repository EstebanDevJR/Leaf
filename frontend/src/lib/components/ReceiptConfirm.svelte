<script lang="ts">
  import type { ReceiptData } from '$lib/api';
  import { formatCOP } from '$lib/api';
  import { createEventDispatcher } from 'svelte';

  export let data: ReceiptData;
  export let imageUrl: string;

  const dispatch = createEventDispatcher<{ confirm: ReceiptData; cancel: void }>();

  let category = data.category ?? 'comida';
  let merchant = data.merchant ?? '';

  const CATEGORIES = [
    'comida', 'transporte', 'vivienda', 'salud',
    'entretenimiento', 'ropa', 'servicios', 'otro',
  ];
</script>

<div class="receipt-card">
  <div class="receipt-header">
    <span class="receipt-icon">📄</span>
    <div>
      <div class="receipt-title">Recibo detectado</div>
      <div class="receipt-sub">Confirma antes de registrar</div>
    </div>
  </div>

  {#if imageUrl}
    <img src={imageUrl} alt="Recibo" class="receipt-img" />
  {/if}

  <div class="receipt-fields">
    <div class="field">
      <label for="merchant">Comercio</label>
      <input id="merchant" bind:value={merchant} placeholder="nombre del establecimiento" />
    </div>
    <div class="field">
      <label for="category">Categoría</label>
      <select id="category" bind:value={category}>
        {#each CATEGORIES as cat}
          <option value={cat}>{cat}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if data.items?.length}
    <div class="items-list">
      {#each data.items as item}
        <div class="item-row">
          <span class="item-name">{item.name}</span>
          <span class="item-amount">{formatCOP(item.amount)}</span>
        </div>
      {/each}
    </div>
  {/if}

  <div class="receipt-total">
    <span>Total</span>
    <span class="total-amount">{formatCOP(data.total)}</span>
  </div>

  <div class="receipt-actions">
    <button class="btn-cancel" on:click={() => dispatch('cancel')}>cancelar</button>
    <button
      class="btn-confirm"
      on:click={() => dispatch('confirm', { ...data, category, merchant: merchant || null })}
    >
      registrar gasto
    </button>
  </div>
</div>

<style>
  .receipt-card {
    background: var(--surface2);
    border: 1px solid rgba(251, 191, 36, 0.25);
    border-radius: 6px;
    padding: 16px;
    max-width: 320px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .receipt-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .receipt-icon { font-size: 20px; }

  .receipt-title {
    font-size: 12px;
    color: #fff;
    font-weight: 500;
  }

  .receipt-sub {
    font-size: 10px;
    color: var(--text-dim);
  }

  .receipt-img {
    width: 100%;
    max-height: 120px;
    object-fit: cover;
    border-radius: 4px;
    border: 1px solid var(--border);
  }

  .receipt-fields {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  label {
    font-size: 9px;
    color: var(--text-dim);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  input, select {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: inherit;
    font-size: 12px;
    padding: 6px 8px;
    border-radius: 3px;
  }

  input:focus, select:focus {
    outline: none;
    border-color: var(--green-dim);
  }

  select option { background: var(--surface2); }

  .items-list {
    border: 1px solid var(--border);
    border-radius: 3px;
    overflow: hidden;
  }

  .item-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 10px;
    font-size: 11px;
    border-bottom: 1px solid var(--border);
  }

  .item-row:last-child { border-bottom: none; }

  .item-name { color: var(--text-mid); }
  .item-amount { color: var(--text); }

  .receipt-total {
    display: flex;
    justify-content: space-between;
    padding: 8px 0 0;
    border-top: 1px solid var(--border);
    font-size: 12px;
  }

  .total-amount {
    color: var(--amber);
    font-weight: 500;
  }

  .receipt-actions {
    display: flex;
    gap: 8px;
  }

  button {
    flex: 1;
    padding: 8px;
    border-radius: 3px;
    font-family: inherit;
    font-size: 11px;
    letter-spacing: 0.05em;
    cursor: pointer;
  }

  .btn-cancel {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-dim);
  }

  .btn-cancel:hover { border-color: var(--red); color: var(--red); }

  .btn-confirm {
    background: rgba(251, 191, 36, 0.1);
    border: 1px solid rgba(251, 191, 36, 0.4);
    color: var(--amber);
  }

  .btn-confirm:hover { background: rgba(251, 191, 36, 0.2); }
</style>
