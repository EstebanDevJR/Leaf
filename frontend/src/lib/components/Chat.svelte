<script lang="ts">
  import { createTransaction, extractReceipt, formatCOP, sendChatStream, TOOL_LABELS } from '$lib/api';
  import type { ReceiptData } from '$lib/api';
  import ReceiptConfirm from './ReceiptConfirm.svelte';
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { marked } from 'marked';

  marked.setOptions({ breaks: true });

  function renderMd(text: string): string {
    const raw = marked.parse(text) as string;
    return raw.replace(/<a href=/g, '<a target="_blank" rel="noopener" href=');
  }

  let gsapReady: Promise<{ gsap: typeof import('gsap').gsap }> | null = null;
  if (typeof window !== 'undefined') {
    gsapReady = import('gsap').then(m => ({ gsap: m.gsap }));
  }

  function animateIn(node: Element) {
    gsapReady?.then(({ gsap }) => {
      gsap.from(node, { opacity: 0, y: 12, duration: 0.28, ease: 'power2.out' });
    });
    return {};
  }

  export let disabled = false;

  const dispatch = createEventDispatcher<{ sent: void }>();

  let sessionId: string | null = null;
  let textareaEl: HTMLTextAreaElement;

  onMount(() => {
    sessionId = localStorage.getItem('leaf_session_id');
  });

  export function focusInput() {
    textareaEl?.focus();
  }

  function newConversation() {
    sessionId = null;
    localStorage.removeItem('leaf_session_id');
    messages = [{
      id: uid(), kind: 'leaf', content: '¡Hola! Soy Leaf 🌿. ¿En qué te puedo ayudar hoy?',
      steps: [], pending: false, ts: new Date(),
    }];
  }

  interface ToolStep {
    tool: string;
    input: Record<string, unknown>;
    output?: string;
    status: 'running' | 'done';
  }

  type Message =
    | { id: number; kind: 'user'; content: string; imageUrl?: string; ts: Date }
    | { id: number; kind: 'leaf'; content: string; steps: ToolStep[]; pending: boolean; ts: Date }
    | { id: number; kind: 'receipt'; receipt: ReceiptData; imageUrl: string; ts: Date };

  let nextId = 1;
  const uid = () => nextId++;

  let messages: Message[] = [{
    id: uid(), kind: 'leaf',
    content: '¡Hola! Soy Leaf 🌿. Cuéntame qué gasté, qué ingresó, o sube la foto de un recibo.',
    steps: [], pending: false, ts: new Date(),
  }];

  const MAX_VISIBLE = 40;
  let visibleCount = MAX_VISIBLE;

  $: visibleMessages = messages.slice(Math.max(0, messages.length - visibleCount));
  $: hiddenCount = Math.max(0, messages.length - visibleCount);

  async function loadMore() {
    const el = messagesEl;
    const prevHeight = el?.scrollHeight ?? 0;
    visibleCount = Math.min(visibleCount + MAX_VISIBLE, messages.length);
    await tick();
    if (el) el.scrollTop += el.scrollHeight - prevHeight;
  }

  let input = '';
  let loading = false;
  let messagesEl: HTMLDivElement;
  let fileInput: HTMLInputElement;

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    messages = [...messages, { id: uid(), kind: 'user', content: text, ts: new Date() }];
    input = '';
    autoResize();
    loading = true;
    await pushLeafPending();

    try {
      for await (const event of sendChatStream(text, sessionId ?? undefined)) {
        if      (event.type === 'session')     { sessionId = event.session_id; localStorage.setItem('leaf_session_id', sessionId); }
        else if (event.type === 'chunk')       chunkLeaf(event.content);
        else if (event.type === 'tool_call')   addStep(event.tool, event.input);
        else if (event.type === 'tool_result') resolveStep(event.tool, event.output);
        else if (event.type === 'response')    { finalizeLeaf(event.content); dispatch('sent'); }
        else if (event.type === 'done')        dispatch('sent');
        else if (event.type === 'error')       finalizeLeaf('Error: ' + event.message);
      }
    } catch {
      finalizeLeaf('No puedo conectarme al backend. ¿Está corriendo Leaf?');
    } finally {
      loading = false;
      await tick();
      scrollBottom();
    }
  }

  function pushLeafPending() {
    messages = [...messages, { id: uid(), kind: 'leaf', content: '', steps: [], pending: true, ts: new Date() }];
    return tick().then(scrollBottom);
  }

  function lastLeaf() {
    const m = messages[messages.length - 1];
    return m?.kind === 'leaf' ? m : null;
  }

  function addStep(tool: string, inp: Record<string, unknown>) {
    const m = lastLeaf(); if (!m) return;
    m.steps = [...m.steps, { tool, input: inp, status: 'running' }];
    messages = [...messages];
    tick().then(scrollBottom);
  }

  function resolveStep(tool: string, output: string) {
    const m = lastLeaf(); if (!m) return;
    const step = [...m.steps].reverse().find(s => s.tool === tool && s.status === 'running');
    if (step) { step.output = output; step.status = 'done'; }
    messages = [...messages];
  }

  function chunkLeaf(token: string) {
    const m = lastLeaf(); if (!m) return;
    m.content = (m.content ?? '') + token;
    m.pending = false;
    messages = [...messages];
    tick().then(scrollBottom);
  }

  function finalizeLeaf(content: string) {
    const m = lastLeaf(); if (!m) return;
    if (!m.content) m.content = content;
    m.pending = false;
    messages = [...messages];
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  function autoResize() {
    if (!textareaEl) return;
    textareaEl.style.height = 'auto';
    textareaEl.style.height = Math.min(textareaEl.scrollHeight, 140) + 'px';
  }

  async function handleFile(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (!file) return;
    const imageUrl = URL.createObjectURL(file);
    messages = [...messages, { id: uid(), kind: 'user', content: '', imageUrl, ts: new Date() }];
    loading = true;
    await pushLeafPending();
    addStep('extract_receipt', { file: file.name });
    await tick(); scrollBottom();

    try {
      const receipt = await extractReceipt(file);
      resolveStep('extract_receipt', `${receipt.items?.length ?? 0} items · ${formatCOP(receipt.total)}`);
      finalizeLeaf('');
      messages = [...messages, { id: uid(), kind: 'receipt', receipt, imageUrl, ts: new Date() }];
    } catch (err: unknown) {
      finalizeLeaf(`No pude leer el recibo: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      loading = false;
      if (fileInput) fileInput.value = '';
      await tick(); scrollBottom();
    }
  }

  async function confirmReceipt(receipt: ReceiptData) {
    loading = true;
    messages = messages.filter(m => m.kind !== 'receipt');
    await pushLeafPending();
    try {
      const tx = await createTransaction({
        amount: receipt.total,
        description: receipt.merchant ? `Compra en ${receipt.merchant}` : 'Compra (recibo)',
        category: receipt.category,
        type: 'expense',
        merchant: receipt.merchant ?? undefined,
      });
      const items = receipt.items?.map(i => `${i.name} ${formatCOP(i.amount)}`).join(', ');
      finalizeLeaf(`Registrado ✓ — ${formatCOP(tx.amount)} en ${tx.category} (ID: ${tx.id})${items ? '\n' + items : ''}`);
      dispatch('sent');
    } catch { finalizeLeaf('No pude registrar el recibo. Intenta de nuevo.'); }
    finally { loading = false; }
  }

  function cancelReceipt() {
    messages = messages.filter(m => m.kind !== 'receipt');
    messages = [...messages, { id: uid(), kind: 'leaf', content: 'Entendido, no se registró nada.', steps: [], pending: false, ts: new Date() }];
  }

  function scrollBottom() {
    if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function fmtTime(d: Date) {
    return d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
  }

  function summarizeInput(inp: Record<string, unknown>): string {
    return Object.entries(inp).filter(([, v]) => v != null).map(([k, v]) => {
      if (k === 'amount' && typeof v === 'number') return formatCOP(v);
      if (k === 'image_base64') return '[imagen]';
      return String(v);
    }).join(' · ');
  }
</script>

<div class="chat">

  <!-- Messages -->
  <div class="scroll-area" bind:this={messagesEl}>
    <div class="messages-inner">

      {#if hiddenCount > 0}
        <button class="load-more" on:click={loadMore}>
          ↑ {hiddenCount} mensaje{hiddenCount > 1 ? 's' : ''} anterior{hiddenCount > 1 ? 'es' : ''}
        </button>
      {/if}

      {#each visibleMessages as msg (msg.id)}

        {#if msg.kind === 'user'}
          <div class="row row-user" use:animateIn>
            <div class="user-bubble">
              {#if msg.imageUrl}
                <img src={msg.imageUrl} alt="recibo" class="bubble-img" />
              {/if}
              {#if msg.content}
                <p class="user-text">{msg.content}</p>
              {/if}
              <span class="msg-time">{fmtTime(msg.ts)}</span>
            </div>
          </div>

        {:else if msg.kind === 'leaf'}
          <div class="row row-leaf" use:animateIn>
            <div class="leaf-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z"/>
              </svg>
            </div>
            <div class="leaf-body">

              {#if msg.steps.length > 0}
                <div class="steps-wrap">
                  {#each msg.steps as step}
                    <div class="step-chip" class:running={step.status === 'running'}>
                      <div class="step-chip-head">
                        {#if step.status === 'running'}
                          <span class="step-spinner"></span>
                        {:else}
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="10" height="10" style="color: var(--green)">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                        {/if}
                        <span class="step-name">{TOOL_LABELS[step.tool] ?? step.tool}</span>
                        {#if step.input && Object.keys(step.input).length > 0}
                          <span class="step-args">{summarizeInput(step.input)}</span>
                        {/if}
                      </div>
                      {#if step.output && step.status === 'done'}
                        <div class="step-result">{step.output}</div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}

              {#if msg.pending && !msg.steps.length}
                <div class="typing-dots">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
              {:else if msg.content}
                <div class="leaf-bubble">
                  <div class="leaf-text md-body">{@html renderMd(msg.content)}</div>
                  <span class="msg-time">{fmtTime(msg.ts)}</span>
                </div>
              {:else if msg.pending}
                <div class="leaf-bubble">
                  <p class="leaf-text dim">procesando...</p>
                </div>
              {/if}

            </div>
          </div>

        {:else if msg.kind === 'receipt'}
          <div class="row row-leaf" use:animateIn>
            <div class="leaf-avatar">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M12 2C8 5 3 10 3 16c0 5 4 7 7 7 0-7 5-11 11-12C19 6 16 2 12 2z"/>
              </svg>
            </div>
            <ReceiptConfirm
              data={msg.receipt}
              imageUrl={msg.imageUrl}
              on:confirm={(e) => confirmReceipt(e.detail)}
              on:cancel={cancelReceipt}
            />
          </div>
        {/if}

      {/each}

    </div>
  </div>

  <!-- Input bar -->
  <div class="input-area">
    <div class="input-wrap" class:focused={false}>

      <div class="input-actions-top">
        <button class="action-btn" title="Nueva conversación" on:click={newConversation} {disabled}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" width="14" height="14">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          Nueva conversación
        </button>
      </div>

      <textarea
        bind:this={textareaEl}
        bind:value={input}
        on:keydown={handleKey}
        on:input={autoResize}
        placeholder="gasté 80mil en el Éxito en comida..."
        rows="1"
        {disabled}
      ></textarea>

      <div class="input-footer">
        <div class="input-left-btns">
          <button
            class="icon-action-btn"
            title="Subir foto de recibo"
            on:click={() => fileInput.click()}
            {disabled}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" width="16" height="16">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <input
            bind:this={fileInput}
            type="file"
            accept="image/*"
            style="display:none"
            on:change={handleFile}
          />
          {#if loading}
            <span class="loading-label">
              <span class="status-dot"></span>
              Pensando...
            </span>
          {/if}
        </div>
        <button
          class="send-btn"
          on:click={send}
          disabled={!input.trim() || loading || disabled}
          title="Enviar (Enter)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" width="16" height="16">
            <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
          </svg>
        </button>
      </div>

    </div>
    <p class="input-hint">Enter para enviar · Shift+Enter nueva línea</p>
  </div>

</div>

<style>
  /* ── Layout ── */
  .chat {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: transparent;
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  .messages-inner {
    padding: 20px 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* Load more */
  .load-more {
    align-self: center;
    background: rgba(255,255,255,0.6);
    border: 1px solid rgba(74,124,89,0.20);
    color: var(--text-dim);
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    padding: 5px 14px;
    border-radius: 20px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .load-more:hover { background: rgba(255,255,255,0.85); color: var(--green); }

  /* ── Message rows ── */
  .row { display: flex; gap: 10px; align-items: flex-start; }
  .row-user { justify-content: flex-end; }
  .row-leaf { justify-content: flex-start; }

  /* Leaf avatar */
  .leaf-avatar {
    width: 28px; height: 28px;
    border-radius: 9px;
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
    box-shadow: 0 2px 0 #2c5038, 0 4px 10px rgba(74,124,89,0.30);
  }

  /* User bubble */
  .user-bubble {
    max-width: 80%;
    background: linear-gradient(145deg, rgba(74,124,89,0.16), rgba(74,124,89,0.10));
    border: 1px solid rgba(74,124,89,0.22);
    border-radius: 18px 18px 4px 18px;
    padding: 11px 14px 8px;
    backdrop-filter: blur(8px);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .user-text {
    font-size: 13px;
    line-height: 1.55;
    color: var(--text);
    white-space: pre-wrap;
    margin: 0;
  }

  .bubble-img {
    max-width: 220px;
    max-height: 160px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid rgba(74,124,89,0.18);
  }

  .msg-time {
    font-size: 10px;
    color: var(--text-dim);
    align-self: flex-end;
    opacity: 0.7;
  }

  /* Leaf body */
  .leaf-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: 86%;
  }

  /* Leaf bubble */
  .leaf-bubble {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(255,255,255,0.88);
    border-radius: 4px 18px 18px 18px;
    padding: 11px 14px 8px;
    backdrop-filter: blur(12px);
    box-shadow: 0 2px 12px rgba(74,124,89,0.07);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .leaf-text {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text);
    margin: 0;
  }

  .leaf-text.dim { color: var(--text-dim); font-style: italic; }

  /* ── Tool steps ── */
  .steps-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 2px;
  }

  .step-chip {
    background: rgba(255,255,255,0.60);
    border: 1px solid rgba(74,124,89,0.16);
    border-radius: 10px;
    padding: 7px 10px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    font-size: 11px;
    backdrop-filter: blur(8px);
  }

  .step-chip.running { border-color: rgba(74,124,89,0.28); }

  .step-chip-head {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .step-spinner {
    width: 10px; height: 10px;
    border: 1.5px solid rgba(74,124,89,0.25);
    border-top-color: var(--green);
    border-radius: 50%;
    display: inline-block;
    animation: spin 0.8s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .step-name { color: var(--green-dark); font-weight: 500; }

  .step-args {
    color: var(--text-dim);
    font-size: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }

  .step-result {
    margin-left: 16px;
    color: var(--text-mid);
    font-size: 10px;
    font-style: italic;
  }

  /* ── Typing dots ── */
  .typing-dots {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 10px 14px;
    background: rgba(255,255,255,0.65);
    border: 1px solid rgba(255,255,255,0.88);
    border-radius: 4px 18px 18px 18px;
    width: fit-content;
  }

  .dot {
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    animation: bounce 1.2s infinite;
  }

  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce {
    0%,80%,100% { transform: translateY(0); opacity: 0.35; }
    40%          { transform: translateY(-5px); opacity: 1; }
  }

  /* ── Input area ── */
  .input-area {
    padding: 10px 14px 14px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .input-wrap {
    background: rgba(255,255,255,0.78);
    border: 1px solid rgba(255,255,255,0.92);
    border-radius: 18px;
    padding: 10px 12px 8px;
    backdrop-filter: blur(16px);
    box-shadow: 0 4px 20px rgba(74,124,89,0.08), inset 0 1px 0 rgba(255,255,255,0.95);
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .input-wrap:focus-within {
    border-color: rgba(74,124,89,0.35);
    box-shadow: 0 4px 20px rgba(74,124,89,0.12), 0 0 0 3px rgba(74,124,89,0.06), inset 0 1px 0 rgba(255,255,255,0.95);
  }

  .input-actions-top {
    display: flex;
    gap: 6px;
    margin-bottom: 2px;
  }

  .action-btn {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    border-radius: 8px;
    border: 1px solid rgba(74,124,89,0.18);
    background: rgba(74,124,89,0.07);
    color: var(--text-dim);
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .action-btn:hover:not(:disabled) { background: rgba(74,124,89,0.14); color: var(--green-dark); }

  textarea {
    flex: 1;
    background: none;
    border: none;
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    line-height: 1.55;
    resize: none;
    outline: none;
    min-height: 22px;
    max-height: 140px;
    overflow-y: auto;
  }

  textarea::placeholder { color: var(--text-dim); }

  .input-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .input-left-btns {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .icon-action-btn {
    width: 28px; height: 28px;
    border-radius: 8px;
    border: 1px solid rgba(74,124,89,0.15);
    background: rgba(74,124,89,0.06);
    color: var(--text-dim);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .icon-action-btn:hover:not(:disabled) { background: rgba(74,124,89,0.14); color: var(--green); }

  .loading-label {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: var(--text-dim);
    font-style: italic;
  }

  .status-dot {
    width: 5px; height: 5px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%,100% { opacity: 0.3; transform: scale(0.8); }
    50%      { opacity: 1; transform: scale(1); }
  }

  /* 3D Send button */
  .send-btn {
    width: 34px; height: 34px;
    border-radius: 50%;
    border: none;
    background: linear-gradient(145deg, #6db87e, #4a7c59);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
    box-shadow:
      0 3px 0 var(--green-dark),
      0 5px 14px rgba(44,80,56,0.35);
    transform: translateY(0);
    transition: transform 0.12s ease, box-shadow 0.12s ease;
  }

  .send-btn:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow:
      0 5px 0 var(--green-dark),
      0 9px 20px rgba(44,80,56,0.40);
  }

  .send-btn:active:not(:disabled) {
    transform: translateY(2px);
    box-shadow:
      0 1px 0 var(--green-dark),
      0 2px 6px rgba(44,80,56,0.20);
  }

  .send-btn:disabled { opacity: 0.35; cursor: not-allowed; box-shadow: none; }

  .input-hint {
    font-size: 10px;
    color: var(--text-dim);
    text-align: center;
    opacity: 0.6;
    letter-spacing: 0.03em;
  }

  /* ── Markdown ── */
  :global(.md-body) { font-size: 13px; line-height: 1.65; color: var(--text); }
  :global(.md-body p) { margin: 0 0 6px; }
  :global(.md-body p:last-child) { margin-bottom: 0; }
  :global(.md-body strong) { color: var(--green-dark); font-weight: 600; }
  :global(.md-body em) { color: var(--text-mid); font-style: italic; }
  :global(.md-body ul), :global(.md-body ol) { margin: 4px 0 6px 18px; padding: 0; display: flex; flex-direction: column; gap: 2px; }
  :global(.md-body li) { font-size: 13px; }
  :global(.md-body h1), :global(.md-body h2), :global(.md-body h3) { font-size: 14px; font-weight: 600; color: var(--green-dark); margin: 8px 0 3px; font-family: 'Playfair Display', serif; }
  :global(.md-body code) { background: rgba(74,124,89,0.10); border: 1px solid rgba(74,124,89,0.18); border-radius: 4px; padding: 1px 5px; font-size: 12px; font-family: 'JetBrains Mono', monospace; color: var(--green-dark); }
  :global(.md-body pre) { background: rgba(74,124,89,0.07); border: 1px solid rgba(74,124,89,0.14); border-radius: 8px; padding: 10px 12px; overflow-x: auto; font-size: 12px; margin: 6px 0; }
  :global(.md-body pre code) { background: none; border: none; padding: 0; }
  :global(.md-body a) { color: var(--green); text-decoration: underline; text-decoration-color: rgba(74,124,89,0.4); }
  :global(.md-body blockquote) { border-left: 2px solid rgba(74,124,89,0.35); margin: 4px 0; padding: 2px 10px; color: var(--text-mid); font-style: italic; }
  :global(.md-body hr) { border: none; border-top: 1px solid rgba(74,124,89,0.15); margin: 8px 0; }
  :global(.md-body table) { width: 100%; border-collapse: collapse; font-size: 12px; margin: 6px 0; }
  :global(.md-body th) { background: rgba(74,124,89,0.10); padding: 6px 10px; border: 1px solid rgba(74,124,89,0.15); font-weight: 600; color: var(--green-dark); }
  :global(.md-body td) { padding: 5px 10px; border: 1px solid rgba(74,124,89,0.10); }
</style>
