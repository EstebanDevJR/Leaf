<script lang="ts">
  import { onMount } from 'svelte';
  import {
    getSavingsGoals, createSavingsGoal, updateSavingsGoal, deleteSavingsGoal,
    formatCOP, type SavingsGoal
  } from '$lib/api';

  let goals: SavingsGoal[] = $state([]);
  let loading = $state(true);
  let showForm = $state(false);
  let depositGoalId = $state<number | null>(null);
  let depositAmount = $state('');

  let form = $state({
    name: '', target_amount: '', monthly_contribution: '',
    current_amount: '0', inflation_rate: '5.5',
  });

  onMount(async () => {
    await loadGoals();
  });

  async function loadGoals() {
    loading = true;
    try { goals = await getSavingsGoals(); } finally { loading = false; }
  }

  async function handleCreate() {
    if (!form.name || !form.target_amount) return;
    await createSavingsGoal({
      name: form.name,
      target_amount: parseFloat(form.target_amount),
      monthly_contribution: parseFloat(form.monthly_contribution || '0'),
      current_amount: parseFloat(form.current_amount || '0'),
      inflation_rate: parseFloat(form.inflation_rate || '5.5'),
      profile_id: 'default',
    });
    form = { name: '', target_amount: '', monthly_contribution: '', current_amount: '0', inflation_rate: '5.5' };
    showForm = false;
    await loadGoals();
  }

  async function handleDeposit(id: number) {
    const amount = parseFloat(depositAmount);
    if (!amount || amount <= 0) return;
    await updateSavingsGoal(id, { current_amount: (goals.find(g => g.id === id)?.current_amount ?? 0) + amount });
    depositGoalId = null;
    depositAmount = '';
    await loadGoals();
  }

  async function handleDelete(id: number) {
    await deleteSavingsGoal(id);
    await loadGoals();
  }

  function monthsToGoal(g: SavingsGoal): number | null {
    if (g.monthly_contribution <= 0) return null;
    const monthlyInflation = Math.pow(1 + g.inflation_rate / 100, 1 / 12) - 1;
    let balance = g.current_amount;
    let realTarget = g.target_amount;
    let months = 0;
    while (balance < realTarget && months < 600) {
      balance += g.monthly_contribution;
      realTarget *= 1 + monthlyInflation;
      months++;
    }
    return months;
  }
</script>

<div class="savings-goals">
  <div class="sg-header">
    <h2>Metas de Ahorro</h2>
    <button class="btn-add" onclick={() => showForm = !showForm}>
      {showForm ? '✕ Cancelar' : '+ Nueva Meta'}
    </button>
  </div>

  {#if showForm}
    <form class="goal-form" onsubmit={(e) => { e.preventDefault(); handleCreate(); }}>
      <input placeholder="Nombre de la meta" bind:value={form.name} required />
      <input type="number" placeholder="Monto objetivo (COP)" bind:value={form.target_amount} min="1" required />
      <input type="number" placeholder="Ahorro mensual (COP)" bind:value={form.monthly_contribution} min="0" />
      <input type="number" placeholder="Ya ahorrado (COP)" bind:value={form.current_amount} min="0" />
      <div class="form-row">
        <label>Inflación estimada:</label>
        <input type="number" bind:value={form.inflation_rate} step="0.1" min="0" max="50" />
        <span>% EA</span>
      </div>
      <button type="submit" class="btn-create">Crear Meta</button>
    </form>
  {/if}

  {#if loading}
    <div class="loading">Cargando metas...</div>
  {:else if goals.length === 0}
    <div class="empty">No tienes metas activas. ¡Crea una para empezar!</div>
  {:else}
    <div class="goals-list">
      {#each goals as goal (goal.id)}
        {@const pct = Math.min(100, (goal.current_amount / goal.target_amount) * 100)}
        {@const months = monthsToGoal(goal)}
        <div class="goal-card">
          <div class="goal-top">
            <span class="goal-name">{goal.name}</span>
            <button class="btn-delete" onclick={() => handleDelete(goal.id)} title="Eliminar">✕</button>
          </div>

          <div class="progress-bar">
            <div class="progress-fill" style="width: {pct}%"></div>
          </div>
          <div class="progress-labels">
            <span>{formatCOP(goal.current_amount)}</span>
            <span class="pct">{pct.toFixed(0)}%</span>
            <span>{formatCOP(goal.target_amount)}</span>
          </div>

          <div class="goal-meta">
            {#if goal.monthly_contribution > 0}
              <span>{formatCOP(goal.monthly_contribution)}/mes</span>
            {/if}
            {#if months !== null}
              <span class="eta">ETA: {months} meses</span>
            {/if}
            <span class="inflation">inflación {goal.inflation_rate}%</span>
          </div>

          {#if depositGoalId === goal.id}
            <div class="deposit-row">
              <input type="number" placeholder="Monto a depositar" bind:value={depositAmount} min="1" autofocus />
              <button onclick={() => handleDeposit(goal.id)}>Confirmar</button>
              <button onclick={() => { depositGoalId = null; depositAmount = ''; }}>✕</button>
            </div>
          {:else}
            <button class="btn-deposit" onclick={() => { depositGoalId = goal.id; depositAmount = ''; }}>
              + Agregar aporte
            </button>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .savings-goals { display: flex; flex-direction: column; gap: 12px; }
  .sg-header { display: flex; justify-content: space-between; align-items: center; }
  h2 { font-size: 1rem; font-weight: 600; color: #e2e8f0; margin: 0; }
  .btn-add { background: #22c55e; color: #000; border: none; border-radius: 6px; padding: 6px 12px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
  .goal-form { background: #1a2332; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
  .goal-form input { background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0; padding: 7px 10px; font-size: 0.85rem; }
  .form-row { display: flex; align-items: center; gap: 8px; color: #94a3b8; font-size: 0.8rem; }
  .form-row input { width: 70px; }
  .btn-create { background: #22c55e; color: #000; font-weight: 700; border: none; border-radius: 6px; padding: 8px; cursor: pointer; }
  .goals-list { display: flex; flex-direction: column; gap: 10px; }
  .goal-card { background: #1a2332; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 8px; }
  .goal-top { display: flex; justify-content: space-between; align-items: center; }
  .goal-name { font-weight: 600; color: #e2e8f0; font-size: 0.9rem; }
  .btn-delete { background: none; border: none; color: #475569; cursor: pointer; font-size: 0.8rem; padding: 0 4px; }
  .btn-delete:hover { color: #ef4444; }
  .progress-bar { background: #0f172a; border-radius: 99px; height: 8px; overflow: hidden; }
  .progress-fill { background: linear-gradient(90deg, #22c55e, #16a34a); height: 100%; border-radius: 99px; transition: width 0.4s ease; }
  .progress-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: #64748b; }
  .pct { color: #22c55e; font-weight: 600; }
  .goal-meta { display: flex; gap: 10px; flex-wrap: wrap; font-size: 0.75rem; color: #64748b; }
  .eta { color: #60a5fa; }
  .inflation { color: #f59e0b; }
  .deposit-row { display: flex; gap: 6px; }
  .deposit-row input { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0; padding: 6px 8px; font-size: 0.8rem; }
  .deposit-row button { background: #22c55e; color: #000; font-weight: 600; border: none; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.8rem; }
  .deposit-row button:last-child { background: #334155; color: #94a3b8; }
  .btn-deposit { background: #0f172a; border: 1px dashed #334155; color: #64748b; border-radius: 6px; padding: 6px; font-size: 0.78rem; cursor: pointer; text-align: center; }
  .btn-deposit:hover { border-color: #22c55e; color: #22c55e; }
  .loading, .empty { color: #64748b; font-size: 0.85rem; text-align: center; padding: 20px; }
</style>
