<script lang="ts">
  const API_URL = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';

  const QUICK_CONCEPTS = [
    { key: 'CDT',                 label: 'CDT',                icon: '🏦' },
    { key: 'UVT',                 label: 'UVT',                icon: '📏' },
    { key: 'GMF',                 label: 'GMF 4×1000',         icon: '💸' },
    { key: 'retencion',           label: 'Retención',          icon: '✂️' },
    { key: 'inflacion',           label: 'Inflación',          icon: '📈' },
    { key: 'interes compuesto',   label: 'Interés compuesto',  icon: '🔁' },
    { key: 'fondo de emergencia', label: 'Fondo emergencia',   icon: '🛡️' },
    { key: 'TES',                 label: 'TES',                icon: '🏛️' },
    { key: 'ETF',                 label: 'ETF',                icon: '🌐' },
    { key: 'FOGAFIN',             label: 'FOGAFÍN',            icon: '🔒' },
    { key: 'pension',             label: 'Pensión',            icon: '👴' },
    { key: 'patrimonio neto',     label: 'Patrimonio neto',    icon: '💰' },
    { key: 'diversificacion',     label: 'Diversificación',    icon: '⚖️' },
    { key: 'presupuesto',         label: 'Presupuesto 50/30/20', icon: '📊' },
    { key: 'tasa ea',             label: 'Tasa EA',            icon: '🔢' },
    { key: 'SMMLV',               label: 'SMMLV',              icon: '💼' },
  ];

  let customQuery = $state('');
  let explanation = $state('');
  let notFound = $state(false);
  let available = $state<string[]>([]);
  let loading = $state(false);
  let error = $state('');
  let selectedConcept = $state('');

  async function explain(concept: string) {
    loading = true;
    error = '';
    explanation = '';
    notFound = false;
    selectedConcept = concept;
    try {
      const res = await fetch(`${API_URL}/health/explain?concept=${encodeURIComponent(concept)}`);
      if (!res.ok) throw new Error('Error al consultar');
      const data = await res.json() as { found: boolean; explanation: string; available?: string[] };
      if (data.found) {
        explanation = data.explanation;
      } else {
        notFound = true;
        available = data.available ?? [];
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Error desconocido';
    } finally {
      loading = false;
    }
  }

  function handleSearch() {
    if (customQuery.trim()) explain(customQuery.trim());
  }
</script>

<div class="explainer">
  <div class="explainer-header">
    <span class="explainer-icon">📚</span>
    <div>
      <h2 class="explainer-title">Diccionario Financiero</h2>
      <p class="explainer-sub">Conceptos explicados en lenguaje simple con contexto colombiano</p>
    </div>
  </div>

  <!-- Search -->
  <div class="search-row">
    <input
      type="text"
      placeholder="Busca un concepto (CDT, retención, ETF...)"
      bind:value={customQuery}
      class="search-input"
      onkeydown={(e) => { if (e.key === 'Enter') handleSearch(); }}
    />
    <button class="search-btn" onclick={handleSearch} disabled={loading || !customQuery.trim()}>
      Explicar
    </button>
  </div>

  <!-- Quick pills -->
  <div class="pills-wrap">
    {#each QUICK_CONCEPTS as c}
      <button
        class="pill"
        class:active={selectedConcept === c.key}
        onclick={() => explain(c.key)}
      >
        <span>{c.icon}</span>
        <span>{c.label}</span>
      </button>
    {/each}
  </div>

  {#if loading}
    <div class="loading">Consultando...</div>
  {:else if error}
    <div class="error-msg">{error}</div>
  {:else if notFound}
    <div class="not-found">
      <p>No encontré "{selectedConcept}". Prueba con:</p>
      <div class="pills-wrap">
        {#each available.slice(0, 8) as a}
          <button class="pill" onclick={() => explain(a)}>{a}</button>
        {/each}
      </div>
    </div>
  {:else if explanation}
    <div class="result-card">
      <pre class="result-text">{explanation}</pre>
    </div>
  {:else}
    <div class="hint">Selecciona un concepto o escribe el tuyo para aprender más</div>
  {/if}
</div>

<style>
  .explainer {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 4px 0;
  }

  .explainer-header { display: flex; align-items: center; gap: 12px; }
  .explainer-icon { font-size: 28px; }

  .explainer-title {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 2px;
  }

  .explainer-sub {
    font-size: 11px;
    color: var(--text-dim);
    margin: 0;
  }

  .search-row { display: flex; gap: 8px; }

  .search-input {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 9px 14px;
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus { border-color: var(--green-dim); }
  .search-input::placeholder { color: var(--text-dim); }

  .search-btn {
    padding: 9px 16px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text-mid);
    font-family: inherit;
    font-size: 13px;
    cursor: pointer;
    white-space: nowrap;
    transition: border-color 0.15s, color 0.15s;
  }

  .search-btn:not(:disabled):hover { border-color: var(--green-dim); color: var(--text); }
  .search-btn:disabled { opacity: 0.5; cursor: default; }

  .pills-wrap { display: flex; flex-wrap: wrap; gap: 6px; }

  .pill {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 20px;
    color: var(--text-dim);
    font-family: inherit;
    font-size: 11px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }

  .pill:hover, .pill.active { border-color: var(--green-dim); color: var(--text); }

  .loading, .hint {
    font-size: 12px;
    color: var(--text-dim);
    text-align: center;
    padding: 20px;
  }

  .error-msg {
    font-size: 12px;
    color: var(--red);
    text-align: center;
    padding: 12px;
  }

  .not-found {
    font-size: 12px;
    color: var(--text-dim);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .not-found p { margin: 0; }

  .result-card {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    max-height: 420px;
    overflow-y: auto;
  }

  .result-text {
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    color: var(--text);
    white-space: pre-wrap;
    line-height: 1.65;
    margin: 0;
  }
</style>
