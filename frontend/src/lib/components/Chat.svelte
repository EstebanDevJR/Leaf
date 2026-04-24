<script lang="ts">
  import { createTransaction, extractReceipt, formatCOP, sendChatStream, TOOL_LABELS } from '$lib/api';
  import type { ReceiptData } from '$lib/api';
  import ReceiptConfirm from './ReceiptConfirm.svelte';
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { marked } from 'marked';

  // Configurar marked: links en nueva pestaña, sin encabezados gigantes
  marked.setOptions({ breaks: true });

  function renderMd(text: string): string {
    const raw = marked.parse(text) as string;
    // Abrir links externos en nueva pestaña
    return raw.replace(/<a href=/g, '<a target="_blank" rel="noopener" href=');
  }

  // Preload GSAP once so animations are instant on first message
  let gsapReady: Promise<{ gsap: typeof import('gsap').gsap }> | null = null;
  if (typeof window !== 'undefined') {
    gsapReady = import('gsap').then(m => ({ gsap: m.gsap }));
  }

  function animateIn(node: Element) {
    gsapReady?.then(({ gsap }) => {
      gsap.from(node, { opacity: 0, y: 14, duration: 0.32, ease: 'power2.out' });
    });
    return {};
  }

  export let disabled = false;

  const dispatch = createEventDispatcher<{ sent: void }>();

  // ── Session ────────────────────────────────────────────────────────────────
  let sessionId: string | null = null;

  onMount(() => {
    sessionId = localStorage.getItem('leaf_session_id');
  });

  function newConversation() {
    sessionId = null;
    localStorage.removeItem('leaf_session_id');
    messages = [
      {
        id: uid(),
        kind: 'leaf',
        content: '¡Hola! Soy Leaf 🌿. ¿En qué te puedo ayudar?',
        steps: [],
        pending: false,
        ts: new Date(),
      },
    ];
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

  let messages: Message[] = [
    {
      id: uid(),
      kind: 'leaf',
      content: '¡Hola! Soy Leaf 🌿. Cuéntame qué gasté, qué ingresó, o sube la foto de un recibo.',
      steps: [],
      pending: false,
      ts: new Date(),
    },
  ];

  // ── Message limit ──────────────────────────────────────────────────────────
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

  // ── State ──────────────────────────────────────────────────────────────────
  let input = '';
  let loading = false;
  let messagesEl: HTMLDivElement;
  let fileInput: HTMLInputElement;

  // ── Chat streaming ─────────────────────────────────────────────────────────

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    messages = [...messages, { id: uid(), kind: 'user', content: text, ts: new Date() }];
    input = '';
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

  function addStep(tool: string, input: Record<string, unknown>) {
    const m = lastLeaf(); if (!m) return;
    m.steps = [...m.steps, { tool, input, status: 'running' }];
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
    // Only overwrite if we got nothing from streaming chunks
    if (!m.content) m.content = content;
    m.pending = false;
    messages = [...messages];
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  }

  // ── OCR ────────────────────────────────────────────────────────────────────

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

  // ── Helpers ────────────────────────────────────────────────────────────────

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

  <!-- ── Messages ─────────────────────────────────────────────────── -->
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
            <div class="bubble bubble-user">
              {#if msg.imageUrl}
                <img src={msg.imageUrl} alt="recibo" class="bubble-img" />
              {/if}
              {#if msg.content}
                <p class="bubble-text">{msg.content}</p>
              {/if}
              <span class="bubble-time">{fmtTime(msg.ts)}</span>
            </div>
          </div>

        {:else if msg.kind === 'leaf'}
          <div class="row row-leaf" use:animateIn>
            <div class="avatar">🌿</div>
            <div class="leaf-body">
              {#if msg.steps.length > 0}
                <div class="steps">
                  {#each msg.steps as step}
                    <div class="step" class:running={step.status === 'running'}>
                      <div class="step-line">
                        <span class="step-icon">{step.status === 'running' ? '⚙' : '✓'}</span>
                        <span class="step-name">{TOOL_LABELS[step.tool] ?? step.tool}</span>
                        <span class="step-args">{summarizeInput(step.input)}</span>
                      </div>
                      {#if step.output && step.status === 'done'}
                        <div class="step-result">{step.output}</div>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}

              {#if msg.pending && !msg.steps.length}
                <div class="typing">
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </div>
              {:else if msg.content}
                <div class="bubble-text leaf-text md-body">{@html renderMd(msg.content)}</div>
              {:else if msg.pending}
                <p class="bubble-text dim">procesando...</p>
              {/if}

              <span class="bubble-time">{fmtTime(msg.ts)}</span>
            </div>
          </div>

        {:else if msg.kind === 'receipt'}
          <div class="row row-leaf" use:animateIn>
            <div class="avatar">🌿</div>
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

  <!-- ── Input ─────────────────────────────────────────────────────── -->
  <div class="input-bar">
    <div class="input-inner">
      <button class="icon-btn" title="Nueva conversación" on:click={newConversation} {disabled}>✦</button>
      <button class="icon-btn" title="Subir foto de recibo" on:click={() => fileInput.click()} {disabled}>
        📎
      </button>
      <input
        bind:this={fileInput}
        type="file"
        accept="image/*"
        style="display:none"
        on:change={handleFile}
      />
      <textarea
        bind:value={input}
        on:keydown={handleKey}
        placeholder="gasté 80mil en el Éxito en comida..."
        rows="1"
        {disabled}
      ></textarea>
      <button class="send-btn" on:click={send} disabled={!input.trim() || loading || disabled}>
        {loading ? '…' : '↑'}
      </button>
    </div>
    {#if loading}
      <div class="status-line">
        <span class="status-dot"></span> leaf está pensando...
      </div>
    {/if}
  </div>

</div>

<style>
  /* ── Layout ── */
  .chat {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--bg);
  }

  .scroll-area {
    flex: 1;
    overflow-y: auto;
    scroll-behavior: smooth;
  }

  .messages-inner {
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  /* ── Load more ── */
  .load-more {
    align-self: center;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text-dim);
    font-family: inherit;
    font-size: 11px;
    padding: 6px 16px;
    border-radius: 20px;
    cursor: pointer;
    letter-spacing: 0.04em;
    transition: border-color 0.15s, color 0.15s;
  }

  .load-more:hover { border-color: var(--green-dim); color: var(--green); }

  /* ── Rows ── */
  .row {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  .row-user { justify-content: flex-end; }
  .row-leaf { justify-content: flex-start; }

  /* ── Avatar ── */
  .avatar {
    font-size: 18px;
    flex-shrink: 0;
    margin-top: 2px;
    width: 28px;
    text-align: center;
  }

  /* ── User bubble ── */
  .bubble {
    max-width: 65%;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .bubble-user {
    background: rgba(74, 222, 128, 0.1);
    border: 1px solid var(--green-dim);
    padding: 12px 16px;
    border-radius: 18px 18px 4px 18px;
  }

  /* ── Leaf body ── */
  .leaf-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-width: 75%;
  }

  /* ── Text ── */
  .bubble-text {
    font-size: 14px;
    line-height: 1.65;
    white-space: pre-wrap;
    margin: 0;
    color: var(--text);
  }

  .bubble-user .bubble-text { color: #fff; }
  .leaf-text { color: var(--text); }
  .bubble-text.dim { color: var(--text-dim); font-style: italic; }

  .bubble-time {
    font-size: 10px;
    color: var(--text-dim);
    align-self: flex-end;
  }

  .bubble-img {
    max-width: 260px;
    max-height: 180px;
    object-fit: cover;
    border-radius: 8px;
    border: 1px solid var(--border);
  }

  /* ── Steps ── */
  .steps {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 11px;
  }

  .step { display: flex; flex-direction: column; gap: 2px; }

  .step-line {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-wrap: wrap;
  }

  .step-icon {
    font-size: 11px;
    width: 13px;
    flex-shrink: 0;
  }

  .step.running .step-icon {
    display: inline-block;
    animation: spin 1.5s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .step-name { color: var(--green); }

  .step-args {
    color: var(--text-dim);
    font-size: 10px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 260px;
  }

  .step-result {
    margin-left: 20px;
    color: var(--text-mid);
    font-size: 10px;
    font-style: italic;
  }

  /* ── Typing dots ── */
  .typing {
    display: flex;
    gap: 5px;
    align-items: center;
    padding: 8px 0 4px;
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
    0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
    40% { transform: translateY(-5px); opacity: 1; }
  }

  /* ── Input bar ── */
  .input-bar {
    padding: 12px 20px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }

  .input-inner {
    width: 100%;
    max-width: 720px;
    display: flex;
    align-items: flex-end;
    gap: 8px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 10px 12px;
    transition: border-color 0.15s;
  }

  .input-inner:focus-within { border-color: var(--green-dim); }

  .icon-btn {
    background: none;
    border: none;
    color: var(--text-dim);
    font-size: 17px;
    cursor: pointer;
    padding: 2px 4px;
    flex-shrink: 0;
    transition: color 0.15s;
    line-height: 1;
  }

  .icon-btn:hover:not(:disabled) { color: var(--amber); }
  .icon-btn:first-child:hover:not(:disabled) { color: var(--green); }

  textarea {
    flex: 1;
    background: none;
    border: none;
    color: var(--text);
    font-family: inherit;
    font-size: 14px;
    line-height: 1.5;
    resize: none;
    outline: none;
    max-height: 120px;
    overflow-y: auto;
  }

  textarea::placeholder { color: var(--text-dim); }

  .send-btn {
    background: var(--green-dim);
    border: 1px solid var(--green);
    color: var(--green);
    font-family: inherit;
    font-size: 16px;
    font-weight: 700;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    cursor: pointer;
    flex-shrink: 0;
    transition: background 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }

  .send-btn:hover:not(:disabled) { background: rgba(74, 222, 128, 0.25); }
  .send-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  /* ── Status line ── */
  .status-line {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    color: var(--text-dim);
    letter-spacing: 0.05em;
  }

  .status-dot {
    width: 5px; height: 5px;
    background: var(--green);
    border-radius: 50%;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }

  /* ── Mobile ── */
  @media (max-width: 600px) {
    .messages-inner { padding: 20px 12px; }
    .bubble, .leaf-body { max-width: 90%; }
  }

  /* ── Markdown body ── */
  :global(.md-body) { font-size: 14px; line-height: 1.65; color: var(--text); }
  :global(.md-body p)  { margin: 0 0 6px; }
  :global(.md-body p:last-child) { margin-bottom: 0; }
  :global(.md-body strong) { color: var(--green); font-weight: 600; }
  :global(.md-body em)     { color: var(--text-dim); font-style: italic; }
  :global(.md-body ul), :global(.md-body ol) {
    margin: 4px 0 6px 18px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  :global(.md-body li) { font-size: 13.5px; }
  :global(.md-body h1), :global(.md-body h2), :global(.md-body h3) {
    font-size: 14px;
    font-weight: 600;
    color: var(--green);
    margin: 8px 0 2px;
  }
  :global(.md-body code) {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1px 5px;
    font-size: 12px;
    font-family: monospace;
  }
  :global(.md-body pre) {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 12px;
    overflow-x: auto;
    font-size: 12px;
    margin: 6px 0;
  }
  :global(.md-body pre code) { background: none; border: none; padding: 0; }
  :global(.md-body a) { color: var(--green); text-decoration: underline; }
  :global(.md-body blockquote) {
    border-left: 2px solid var(--green-dim);
    margin: 4px 0;
    padding: 2px 10px;
    color: var(--text-dim);
    font-style: italic;
  }
  :global(.md-body hr) { border: none; border-top: 1px solid var(--border); margin: 8px 0; }
</style>
