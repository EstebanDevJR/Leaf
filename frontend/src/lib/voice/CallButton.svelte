<script lang="ts">
  import { onDestroy } from 'svelte';
  import { VoiceHandler, type VoiceState } from './WebRTCHandler';

  let state: VoiceState = 'idle';
  let transcript = '';
  let response = '';
  let errorMsg = '';

  const handler = new VoiceHandler({
    onStateChange: (s) => { state = s; },
    onTranscript:  (t) => { transcript = t; },
    onResponse:    (r) => { response = r; errorMsg = ''; },
    onError:       (e) => { errorMsg = e; },
  });

  onDestroy(() => handler.disconnect());

  async function handleClick() {
    errorMsg = '';

    if (state === 'idle') {
      try {
        await handler.connect();
        await handler.startRecording();
      } catch (e) {
        errorMsg = 'No se pudo acceder al micrófono.';
        state = 'idle';
      }
      return;
    }

    if (state === 'ready') {
      try {
        await handler.startRecording();
      } catch {
        errorMsg = 'No se pudo acceder al micrófono.';
      }
      return;
    }

    if (state === 'recording') {
      handler.stopRecording();
      return;
    }
  }

  function endCall() {
    handler.disconnect();
    transcript = '';
    response = '';
    errorMsg = '';
  }

  const labels: Record<VoiceState, string> = {
    idle:        'Hablar con Leaf',
    connecting:  'Conectando…',
    ready:       'Hablar',
    recording:   'Detener',
    processing:  'Procesando…',
    playing:     'Escuchando…',
    error:       'Reintentar',
  };

  const icons: Record<VoiceState, string> = {
    idle:        '🎙️',
    connecting:  '⏳',
    ready:       '🎙️',
    recording:   '⏹️',
    processing:  '⏳',
    playing:     '🔊',
    error:       '⚠️',
  };
</script>

<div class="voice-widget">
  {#if state === 'idle'}
    <button class="call-btn idle" on:click={handleClick}>
      <span class="call-icon">{icons[state]}</span>
      <span class="call-label">{labels[state]}</span>
    </button>
  {:else}
    <div class="call-session">
      <div class="session-header">
        <span class="session-icon">{icons[state]}</span>
        <span class="session-state">{labels[state]}</span>
        <button class="end-call" on:click={endCall} title="Terminar llamada">✕</button>
      </div>

      {#if state === 'recording'}
        <div class="waveform" aria-label="Grabando…">
          {#each Array(5) as _, i}
            <span class="bar" style="--delay:{i * 0.12}s"></span>
          {/each}
        </div>
      {/if}

      {#if transcript}
        <div class="bubble you">
          <span class="bubble-label">Tú</span>
          <p>{transcript}</p>
        </div>
      {/if}

      {#if response}
        <div class="bubble leaf">
          <span class="bubble-label">Leaf</span>
          <p>{response}</p>
        </div>
      {/if}

      {#if errorMsg}
        <p class="error-msg">{errorMsg}</p>
      {/if}

      <button
        class="call-btn"
        class:recording={state === 'recording'}
        class:disabled={state === 'processing' || state === 'playing' || state === 'connecting'}
        disabled={state === 'processing' || state === 'playing' || state === 'connecting'}
        on:click={handleClick}
      >
        <span class="call-icon">{icons[state]}</span>
        <span class="call-label">{labels[state]}</span>
      </button>
    </div>
  {/if}
</div>

<style>
  .voice-widget {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .call-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--surface2, #1e293b);
    border: 1px solid var(--green-dim, rgba(34,197,94,0.3));
    color: var(--green, #22c55e);
    font-family: inherit;
    font-size: 13px;
    padding: 8px 16px;
    border-radius: 8px;
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    flex-shrink: 0;
  }

  .call-btn:hover:not(:disabled) {
    border-color: var(--green, #22c55e);
    background: var(--green-glow, rgba(34,197,94,0.08));
  }

  .call-btn.idle {
    padding: 6px 14px;
  }

  .call-btn.recording {
    border-color: rgba(248,113,113,0.6);
    color: #f87171;
    animation: pulse-border 1.2s ease-in-out infinite;
  }

  .call-btn.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @keyframes pulse-border {
    0%, 100% { border-color: rgba(248,113,113,0.6); }
    50%       { border-color: rgba(248,113,113,1); }
  }

  .call-icon { font-size: 16px; }

  /* Session container */
  .call-session {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 280px;
    background: var(--surface, #111827);
    border: 1px solid var(--border, rgba(255,255,255,0.08));
    border-radius: 12px;
    padding: 14px;
  }

  .session-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .session-icon { font-size: 18px; }

  .session-state {
    flex: 1;
    font-size: 12px;
    color: var(--text-dim, #94a3b8);
    letter-spacing: 0.05em;
  }

  .end-call {
    background: none;
    border: 1px solid var(--border, rgba(255,255,255,0.08));
    color: var(--text-dim, #94a3b8);
    border-radius: 6px;
    width: 22px;
    height: 22px;
    cursor: pointer;
    font-size: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .end-call:hover { border-color: #f87171; color: #f87171; }

  /* Waveform animation */
  .waveform {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    height: 28px;
  }

  .bar {
    display: block;
    width: 4px;
    background: var(--green, #22c55e);
    border-radius: 2px;
    animation: wave 0.8s ease-in-out infinite alternate;
    animation-delay: var(--delay, 0s);
    height: 8px;
  }

  @keyframes wave {
    from { height: 4px;  opacity: 0.5; }
    to   { height: 24px; opacity: 1; }
  }

  /* Conversation bubbles */
  .bubble {
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
    line-height: 1.5;
  }

  .bubble p { margin: 0; }

  .bubble-label {
    display: block;
    font-size: 10px;
    letter-spacing: 0.05em;
    margin-bottom: 3px;
    opacity: 0.6;
  }

  .bubble.you {
    background: var(--surface2, #1e293b);
    border: 1px solid var(--border, rgba(255,255,255,0.08));
    color: var(--text, #e2e8f0);
  }

  .bubble.leaf {
    background: var(--green-glow, rgba(34,197,94,0.08));
    border: 1px solid var(--green-dim, rgba(34,197,94,0.3));
    color: var(--green, #22c55e);
  }

  .error-msg {
    font-size: 11px;
    color: #f87171;
    margin: 0;
  }
</style>
