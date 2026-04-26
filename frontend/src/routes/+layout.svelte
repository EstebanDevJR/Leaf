<script lang="ts">
  import { onMount } from 'svelte';

  onMount(async () => {
    const { gsap } = await import('gsap');
    const container = document.getElementById('leaf-particles');
    if (!container) return;

    const path = 'M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z';

    const createLeaf = (delay = 0) => {
      const el = document.createElement('div');
      const size = 10 + Math.random() * 14;
      el.innerHTML = `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="currentColor"><path d="${path}"/></svg>`;
      el.style.cssText = `position:absolute;left:${Math.random() * 100}%;bottom:-30px;color:rgba(74,124,89,${0.07 + Math.random() * 0.10});pointer-events:none;`;
      container.appendChild(el);

      gsap.fromTo(el,
        { y: 0, x: 0, rotation: Math.random() * 40 - 20, opacity: 0 },
        {
          y: -(window.innerHeight + 50),
          x: (Math.random() - 0.5) * 200,
          rotation: `+=${Math.random() * 300 - 150}`,
          opacity: 1,
          duration: 18 + Math.random() * 10,
          delay,
          ease: 'none',
          onComplete: () => { el.remove(); createLeaf(); },
        }
      );
    };

    // Only 6 particles — enough for visual effect without GPU cost
    for (let i = 0; i < 6; i++) createLeaf(i * 1.5);
  });
</script>

<svelte:head>
  <title>Leaf — Finanzas Personales</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,600;0,700;1,600;1,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
</svelte:head>

<div class="leaf-bg" aria-hidden="true">
  <div class="blob b1"></div>
  <div class="blob b2"></div>
  <div class="blob b3"></div>
  <div id="leaf-particles"></div>
</div>

<slot />

<style>
  :global(*) { margin: 0; padding: 0; box-sizing: border-box; }

  :global(:root) {
    /* ── Glass surfaces ── */
    --glass:        rgba(255, 255, 255, 0.56);
    --glass-mid:    rgba(255, 255, 255, 0.70);
    --glass-strong: rgba(255, 255, 255, 0.82);
    --glass-border: rgba(255, 255, 255, 0.90);
    --glass-shadow: 0 8px 32px rgba(52, 100, 68, 0.10), inset 0 1px 0 rgba(255,255,255,0.88);
    --glass-blur:   blur(28px) saturate(200%);

    /* ── Legacy surface vars (used by Stats/TransactionList) ── */
    --surface:      rgba(255, 255, 255, 0.56);
    --surface2:     rgba(255, 255, 255, 0.72);
    --surface3:     rgba(255, 255, 255, 0.88);
    --border:       rgba(74, 124, 89, 0.18);
    --border-light: rgba(74, 124, 89, 0.30);

    /* ── Nature greens ── */
    --green:        #4a7c59;
    --green-dark:   #2c5038;
    --green-light:  #6db87e;
    --green-bright: #6db87e;
    --green-dim:    rgba(74, 124, 89, 0.22);
    --green-pale:   rgba(74, 124, 89, 0.09);
    --green-nav:    rgba(74, 124, 89, 0.13);
    --green-glow:   rgba(109, 184, 126, 0.45);

    /* ── Accents ── */
    --amber:        #b8892e;
    --amber-light:  #d4a840;
    --red:          #c05050;
    --blue:         #4878aa;

    /* ── Text ── */
    --text:         #162219;
    --text-mid:     #3d5c47;
    --text-dim:     #6a8870;

    /* ── Category palette ── */
    --cat-comida:          #4a9a4a;
    --cat-transporte:      #4a78aa;
    --cat-vivienda:        #7060aa;
    --cat-salud:           #2a9870;
    --cat-entretenimiento: #b84878;
    --cat-ropa:            #b88828;
    --cat-servicios:       #b86028;
    --cat-otro:            #6a7868;
  }

  :global(body) {
    /* Static gradient — no background-attachment:fixed to avoid repaint on scroll */
    background: linear-gradient(150deg, #bdd8b2 0%, #cce0c2 30%, #d8e8cc 60%, #e0e8d0 100%);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 13px;
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  :global(::-webkit-scrollbar)       { width: 5px; height: 5px; }
  :global(::-webkit-scrollbar-track) { background: transparent; }
  :global(::-webkit-scrollbar-thumb) { background: rgba(74,124,89,0.22); border-radius: 4px; }
  :global(::-webkit-scrollbar-thumb:hover) { background: rgba(74,124,89,0.42); }
  :global(*) { scrollbar-width: thin; scrollbar-color: rgba(74,124,89,0.22) transparent; }

  :global(#svelte) { height: 100vh; display: flex; flex-direction: column; position: relative; }

  /* ── Animated background blobs ── */
  .leaf-bg {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
  }

  .blob {
    position: absolute;
    /* Single cheap blur, promoted to own GPU layer */
    filter: blur(55px);
    transform: translateZ(0);
    border-radius: 50%;
    /* No morphing border-radius — that forces repaints */
  }

  .b1 {
    width: 600px; height: 600px;
    background: radial-gradient(ellipse, rgba(168, 220, 148, 0.55) 0%, transparent 70%);
    top: -220px; left: -140px;
    animation: drift1 28s ease-in-out infinite;
  }

  .b2 {
    width: 520px; height: 520px;
    background: radial-gradient(ellipse, rgba(195, 230, 165, 0.45) 0%, transparent 70%);
    bottom: -200px; right: -100px;
    animation: drift2 34s ease-in-out infinite;
  }

  .b3 {
    width: 400px; height: 400px;
    background: radial-gradient(ellipse, rgba(228, 212, 158, 0.32) 0%, transparent 70%);
    top: 28%; left: 40%;
    animation: drift3 22s ease-in-out infinite;
  }

  /* Simple translate-only animations — compositor thread, no repaint */
  @keyframes drift1 {
    0%,100% { transform: translateZ(0) translate(0, 0); }
    50%     { transform: translateZ(0) translate(40px, 35px); }
  }

  @keyframes drift2 {
    0%,100% { transform: translateZ(0) translate(0, 0); }
    50%     { transform: translateZ(0) translate(-45px, -35px); }
  }

  @keyframes drift3 {
    0%,100% { transform: translateZ(0) translate(-50%, 0); opacity: 0.8; }
    50%     { transform: translateZ(0) translate(-50%, -25px); opacity: 0.55; }
  }

  #leaf-particles { position: absolute; inset: 0; overflow: hidden; }
</style>
