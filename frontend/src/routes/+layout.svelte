<script lang="ts">
</script>

<svelte:head>
  <title>Leaf 🌿</title>
  <link
    href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=JetBrains+Mono:wght@300;400;500&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<slot />

<style>
  :global(*) {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  :global(:root) {
    --bg: #0a0f0a;
    --surface: #111811;
    --surface2: #162016;
    --border: #1e2e1e;
    --green: #4ade80;
    --green-dim: #22543d;
    --green-glow: rgba(74, 222, 128, 0.08);
    --amber: #fbbf24;
    --blue: #60a5fa;
    --red: #f87171;
    --text: #d1fae5;
    --text-dim: #6b7280;
    --text-mid: #9ca3af;

    /* Category palette */
    --cat-comida:          #4ade80;
    --cat-transporte:      #60a5fa;
    --cat-vivienda:        #a78bfa;
    --cat-salud:           #34d399;
    --cat-entretenimiento: #f472b6;
    --cat-ropa:            #fbbf24;
    --cat-servicios:       #fb923c;
    --cat-otro:            #94a3b8;
  }

  :global(body) {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.7;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* Custom scrollbar — all scroll areas */
  :global(::-webkit-scrollbar) { width: 4px; height: 4px; }
  :global(::-webkit-scrollbar-track) { background: transparent; }
  :global(::-webkit-scrollbar-thumb) {
    background: var(--border);
    border-radius: 4px;
  }
  :global(::-webkit-scrollbar-thumb:hover) { background: var(--green-dim); }
  :global(*) { scrollbar-width: thin; scrollbar-color: var(--border) transparent; }

  :global(body::before) {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(74, 222, 128, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(74, 222, 128, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }

  :global(#svelte) {
    position: relative;
    z-index: 1;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
</style>
