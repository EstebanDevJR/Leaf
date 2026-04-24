<script lang="ts">
</script>

<svelte:head>
  <title>Leaf</title>
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,700;1,700&family=JetBrains+Mono:wght@300;400;500&display=swap"
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
    --bg:          #111311;
    --surface:     #181c18;
    --surface2:    #1d221d;
    --surface3:    #232923;
    --border:      #232923;
    --border-light: #2d342d;

    --green:       #5aaa5a;
    --green-bright:#4ade80;
    --green-dim:   #2d4a2d;
    --green-glow:  rgba(90, 170, 90, 0.14);
    --green-nav:   rgba(90, 170, 90, 0.16);

    --amber: #fbbf24;
    --blue:  #60a5fa;
    --red:   #f87171;

    --text:     #f0f0ef;
    --text-mid: #9aaa9a;
    --text-dim: #5a6a5a;

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
    font-family: 'Inter', 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  :global(::-webkit-scrollbar) { width: 4px; height: 4px; }
  :global(::-webkit-scrollbar-track) { background: transparent; }
  :global(::-webkit-scrollbar-thumb) { background: var(--border); border-radius: 4px; }
  :global(::-webkit-scrollbar-thumb:hover) { background: var(--green-dim); }
  :global(*) { scrollbar-width: thin; scrollbar-color: var(--border) transparent; }

  :global(#svelte) {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
</style>
