<script lang="ts">
  import { importCSV, exportExcelUrl, exportPdfUrl } from '$lib/api';

  const BANKS = ['bancolombia', 'davivienda', 'nequi', 'nubank', 'daviplata'];

  let selectedBank = $state('bancolombia');
  let csvFile = $state<File | null>(null);
  let importing = $state(false);
  let importResult = $state<{ imported: number; expenses: number; incomes: number } | null>(null);
  let importError = $state('');

  async function handleImport() {
    if (!csvFile) return;
    importing = true;
    importResult = null;
    importError = '';
    try {
      importResult = await importCSV(csvFile, selectedBank);
    } catch (e: unknown) {
      importError = e instanceof Error ? e.message : 'Error de importación';
    } finally {
      importing = false;
    }
  }
</script>

<div class="import-export">
  <h2>Importar / Exportar</h2>

  <!-- Import CSV -->
  <section class="card">
    <h3>📥 Importar CSV bancario</h3>
    <p class="hint">Descarga el extracto de tu banco en formato CSV y súbelo aquí.</p>

    <div class="bank-selector">
      {#each BANKS as bank}
        <button
          class="bank-btn"
          class:active={selectedBank === bank}
          onclick={() => selectedBank = bank}
        >
          {bank.charAt(0).toUpperCase() + bank.slice(1)}
        </button>
      {/each}
    </div>

    <label class="file-label">
      <input
        type="file"
        accept=".csv"
        onchange={(e) => { csvFile = (e.target as HTMLInputElement).files?.[0] ?? null; }}
      />
      {csvFile ? csvFile.name : 'Seleccionar archivo CSV'}
    </label>

    <button class="btn-import" onclick={handleImport} disabled={!csvFile || importing}>
      {importing ? 'Importando...' : 'Importar transacciones'}
    </button>

    {#if importResult}
      <div class="result success">
        ✅ <strong>{importResult.imported}</strong> transacciones importadas
        ({importResult.expenses} gastos, {importResult.incomes} ingresos)
      </div>
    {/if}
    {#if importError}
      <div class="result error">❌ {importError}</div>
    {/if}
  </section>

  <!-- Export -->
  <section class="card">
    <h3>📤 Exportar reporte</h3>
    <div class="export-buttons">
      <a class="btn-export excel" href={exportExcelUrl()} download>
        📊 Descargar Excel
      </a>
      <a class="btn-export pdf" href={exportPdfUrl()} download>
        📄 Descargar PDF
      </a>
      <a class="btn-export pdf contador" href={exportPdfUrl(undefined, undefined, 'contador')} download>
        🧮 PDF Modo Contador
      </a>
    </div>
  </section>
</div>

<style>
  .import-export { display: flex; flex-direction: column; gap: 14px; }
  h2 { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin: 0; }
  .card { background: #1a2332; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 10px; }
  h3 { font-size: 0.88rem; font-weight: 600; color: #cbd5e1; margin: 0; }
  .hint { font-size: 0.78rem; color: #64748b; margin: 0; }
  .bank-selector { display: flex; flex-wrap: wrap; gap: 6px; }
  .bank-btn { background: #0f172a; border: 1px solid #334155; color: #94a3b8; border-radius: 6px; padding: 5px 10px; font-size: 0.78rem; cursor: pointer; }
  .bank-btn.active { border-color: #22c55e; color: #22c55e; background: #052e16; }
  .file-label { display: block; background: #0f172a; border: 1px dashed #334155; border-radius: 6px; padding: 10px; text-align: center; font-size: 0.8rem; color: #64748b; cursor: pointer; }
  .file-label input[type="file"] { display: none; }
  .btn-import { background: #22c55e; color: #000; font-weight: 700; border: none; border-radius: 6px; padding: 8px; cursor: pointer; font-size: 0.85rem; }
  .btn-import:disabled { opacity: 0.5; cursor: not-allowed; }
  .result { font-size: 0.8rem; padding: 8px 10px; border-radius: 6px; }
  .result.success { background: #052e16; color: #4ade80; }
  .result.error { background: #2d0707; color: #f87171; }
  .export-buttons { display: flex; flex-direction: column; gap: 8px; }
  .btn-export { display: block; text-align: center; border-radius: 6px; padding: 9px; font-size: 0.85rem; font-weight: 600; text-decoration: none; }
  .btn-export.excel { background: #166534; color: #4ade80; }
  .btn-export.pdf { background: #1e3a5f; color: #60a5fa; }
  .btn-export.contador { background: #312e81; color: #a5b4fc; }
</style>
