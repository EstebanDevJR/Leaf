<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { dismissAlert } from '$lib/api';
  import type { AlertItem } from '$lib/api';

  export let alerts: AlertItem[] = [];

  const dispatch = createEventDispatcher<{ dismissed: number }>();

  let expanded: number | null = null;

  const SEVERITY_ICON: Record<string, string> = {
    urgent: '🔴',
    warn:   '🟡',
    info:   '💡',
  };

  const TYPE_LABEL: Record<string, string> = {
    income_threshold: 'Obligación tributaria',
    deadline_30d:     'Declaración de renta',
    deadline_7d:      'Declaración de renta',
    gmf_monthly:      'GMF 4×1000',
    retention:        'Retención',
  };

  async function handleDismiss(id: number) {
    await dismissAlert(id);
    dispatch('dismissed', id);
  }
</script>

{#if alerts.length > 0}
  <div class="alerts-bar">
    {#each alerts as alert (alert.id)}
      <div
        class="alert-chip"
        class:urgent={alert.severity === 'urgent'}
        class:warn={alert.severity === 'warn'}
        class:info={alert.severity === 'info'}
      >
        <button
          class="chip-main"
          on:click={() => expanded = expanded === alert.id ? null : alert.id}
        >
          <span class="chip-icon">{SEVERITY_ICON[alert.severity] ?? '💡'}</span>
          <span class="chip-label">{TYPE_LABEL[alert.type] ?? alert.type}</span>
          <span class="chip-msg">{alert.message}</span>
          <span class="chip-arrow">{expanded === alert.id ? '▲' : '▼'}</span>
        </button>
        <button class="chip-dismiss" on:click={() => handleDismiss(alert.id)} title="Descartar">✕</button>
      </div>

      {#if expanded === alert.id}
        <div class="alert-detail"
          class:urgent={alert.severity === 'urgent'}
          class:warn={alert.severity === 'warn'}
        >
          <pre class="detail-text">{alert.detail}</pre>
        </div>
      {/if}
    {/each}
  </div>
{/if}

<style>
  .alerts-bar {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
  }

  .alert-chip {
    display: flex;
    align-items: stretch;
    border-radius: 5px;
    overflow: hidden;
    border: 1px solid var(--border);
    font-size: 11px;
  }

  .alert-chip.urgent { border-color: rgba(248,113,113,0.4); background: rgba(248,113,113,0.05); }
  .alert-chip.warn   { border-color: rgba(251,191,36,0.35); background: rgba(251,191,36,0.04); }
  .alert-chip.info   { border-color: rgba(96,165,250,0.3);  background: rgba(96,165,250,0.04); }

  .chip-main {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 10px;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    min-width: 0;
  }

  .chip-icon { font-size: 12px; flex-shrink: 0; }

  .chip-label {
    font-size: 9px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    flex-shrink: 0;
    white-space: nowrap;
  }

  .chip-msg {
    color: var(--text);
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .chip-arrow {
    font-size: 8px;
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .chip-dismiss {
    background: none;
    border: none;
    border-left: 1px solid var(--border);
    color: var(--text-dim);
    padding: 0 10px;
    cursor: pointer;
    font-size: 12px;
    flex-shrink: 0;
    transition: color 0.15s, background 0.15s;
  }

  .chip-dismiss:hover { color: var(--red); background: rgba(248,113,113,0.06); }

  /* Detail panel */
  .alert-detail {
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 5px 5px;
    margin-top: -2px;
  }

  .alert-detail.urgent { border-color: rgba(248,113,113,0.3); background: rgba(248,113,113,0.04); }
  .alert-detail.warn   { border-color: rgba(251,191,36,0.3);  background: rgba(251,191,36,0.04); }

  .detail-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-mid);
    line-height: 1.7;
    white-space: pre-wrap;
    margin: 0;
  }
</style>
