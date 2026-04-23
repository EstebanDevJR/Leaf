<script lang="ts">
  import { onMount } from 'svelte';
  import { getProfiles, createProfile, type UserProfile } from '$lib/api';

  let profiles: UserProfile[] = $state([]);
  let activeProfile = $state('default');
  let showForm = $state(false);
  let newName = $state('');
  let newColor = $state('#60a5fa');

  let { onProfileChange }: { onProfileChange?: (id: string) => void } = $props();

  onMount(async () => {
    profiles = await getProfiles();
  });

  async function handleCreate() {
    if (!newName.trim()) return;
    const id = newName.toLowerCase().replace(/\s+/g, '_');
    const p = await createProfile({ profile_id: id, name: newName, color: newColor, monthly_income: 0 });
    profiles = [...profiles, p];
    showForm = false;
    newName = '';
  }

  function select(id: string) {
    activeProfile = id;
    onProfileChange?.(id);
  }
</script>

<div class="switcher">
  <div class="profiles-row">
    {#each profiles as p (p.profile_id)}
      <button
        class="profile-btn"
        class:active={activeProfile === p.profile_id}
        style="--color: {p.color}"
        onclick={() => select(p.profile_id)}
        title={p.name}
      >
        <span class="dot" style="background: {p.color}"></span>
        {p.name}
      </button>
    {/each}
    <button class="profile-btn add" onclick={() => showForm = !showForm}>+</button>
  </div>

  {#if showForm}
    <form class="create-form" onsubmit={(e) => { e.preventDefault(); handleCreate(); }}>
      <input placeholder="Nombre del perfil" bind:value={newName} required />
      <input type="color" bind:value={newColor} title="Color del perfil" />
      <button type="submit">Crear</button>
    </form>
  {/if}
</div>

<style>
  .switcher { display: flex; flex-direction: column; gap: 8px; }
  .profiles-row { display: flex; gap: 6px; flex-wrap: wrap; }
  .profile-btn { background: #1a2332; border: 1px solid #334155; color: #94a3b8; border-radius: 20px; padding: 5px 12px; font-size: 0.78rem; cursor: pointer; display: flex; align-items: center; gap: 5px; }
  .profile-btn.active { border-color: var(--color); color: #e2e8f0; }
  .profile-btn.add { border-style: dashed; color: #475569; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .create-form { display: flex; gap: 6px; align-items: center; }
  .create-form input[type="text"], .create-form input:not([type="color"]) { flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #e2e8f0; padding: 5px 8px; font-size: 0.8rem; }
  .create-form button { background: #22c55e; color: #000; font-weight: 700; border: none; border-radius: 6px; padding: 5px 10px; cursor: pointer; font-size: 0.8rem; }
</style>
