/**
 * VoiceHandler — records audio via MediaRecorder with VAD, sends over WebSocket,
 * plays back streaming audio chunks from the Leaf voice pipeline.
 */

export type VoiceState = 'idle' | 'connecting' | 'ready' | 'recording' | 'processing' | 'playing' | 'error';

export interface VoiceHandlerCallbacks {
  onStateChange?: (state: VoiceState) => void;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
  onError?: (message: string) => void;
}

const WS_URL = `${typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'}://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000/voice/ws`;

const SILENCE_THRESHOLD = 8;   // 0–255 average frequency energy
const SILENCE_DURATION_MS = 1200; // auto-stop after 1.2s of silence

export class VoiceHandler {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private callbacks: VoiceHandlerCallbacks;
  private _state: VoiceState = 'idle';

  // Audio playback queue
  private _audioQueue: string[] = [];
  private _audioPlaying = false;
  private _currentAudio: HTMLAudioElement | null = null;

  // VAD
  private _vadContext: AudioContext | null = null;
  private _vadAnalyser: AnalyserNode | null = null;
  private _vadTimer: ReturnType<typeof setTimeout> | null = null;
  private _silenceStart: number | null = null;

  constructor(callbacks: VoiceHandlerCallbacks = {}) {
    this.callbacks = callbacks;
  }

  get state(): VoiceState { return this._state; }

  private setState(s: VoiceState) {
    this._state = s;
    this.callbacks.onStateChange?.(s);
  }

  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.setState('connecting');
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(WS_URL);
      ws.binaryType = 'blob';
      ws.onopen = () => { this.ws = ws; this.setState('ready'); resolve(); };
      ws.onerror = () => { this.setState('error'); reject(new Error('WebSocket connection failed')); };
      ws.onclose = () => { if (this._state !== 'idle') this.setState('idle'); this.ws = null; };
      ws.onmessage = (event) => this._handleMessage(event);
    });
  }

  private _handleMessage(event: MessageEvent) {
    try {
      const msg = JSON.parse(event.data as string) as Record<string, string>;
      switch (msg.type) {
        case 'transcript':
          this.callbacks.onTranscript?.(msg.text);
          break;
        case 'response':
          this.callbacks.onResponse?.(msg.text);
          break;
        case 'audio_chunk':
          if (this._state === 'processing') this.setState('playing');
          this._enqueueAudio(msg.data);
          break;
        case 'error':
          this.callbacks.onError?.(msg.message);
          this.setState('ready');
          break;
        case 'done':
          if (this._state === 'processing') this.setState('ready');
          break;
      }
    } catch {
      // ignore malformed frames
    }
  }

  // ── Audio queue ────────────────────────────────────────────────────────────

  private _enqueueAudio(b64: string) {
    this._audioQueue.push(b64);
    if (!this._audioPlaying) void this._playNext();
  }

  private async _playNext(): Promise<void> {
    if (this._audioQueue.length === 0) {
      this._audioPlaying = false;
      if (this._state === 'playing') this.setState('ready');
      return;
    }
    this._audioPlaying = true;
    const b64 = this._audioQueue.shift()!;
    await this._playBase64Audio(b64);
    void this._playNext();
  }

  private async _playBase64Audio(b64: string): Promise<void> {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    this._currentAudio = audio;
    return new Promise((resolve) => {
      const cleanup = () => { URL.revokeObjectURL(url); if (this._currentAudio === audio) this._currentAudio = null; resolve(); };
      audio.onended = cleanup;
      audio.onerror = cleanup;
      void audio.play().catch(() => cleanup());
    });
  }

  // ── VAD ───────────────────────────────────────────────────────────────────

  private _startVAD() {
    if (!this.stream) return;
    this._vadContext = new AudioContext();
    const source = this._vadContext.createMediaStreamSource(this.stream);
    this._vadAnalyser = this._vadContext.createAnalyser();
    this._vadAnalyser.fftSize = 256;
    source.connect(this._vadAnalyser);
    this._silenceStart = null;
    this._checkSilence();
  }

  private _checkSilence() {
    if (this._state !== 'recording' || !this._vadAnalyser) return;
    const data = new Uint8Array(this._vadAnalyser.frequencyBinCount);
    this._vadAnalyser.getByteFrequencyData(data);
    const level = data.reduce((a, b) => a + b, 0) / data.length;
    if (level < SILENCE_THRESHOLD) {
      if (!this._silenceStart) this._silenceStart = Date.now();
      else if (Date.now() - this._silenceStart > SILENCE_DURATION_MS) {
        this._stopVAD();
        this.stopRecording();
        return;
      }
    } else {
      this._silenceStart = null;
    }
    this._vadTimer = setTimeout(() => this._checkSilence(), 80);
  }

  private _stopVAD() {
    if (this._vadTimer) { clearTimeout(this._vadTimer); this._vadTimer = null; }
    this._vadContext?.close().catch(() => {});
    this._vadContext = null;
    this._vadAnalyser = null;
    this._silenceStart = null;
  }

  // ── Recording ─────────────────────────────────────────────────────────────

  async startRecording(): Promise<void> {
    if (this._state !== 'ready') return;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) await this.connect();

    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioChunks = [];

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus' : 'audio/webm';

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) this.audioChunks.push(e.data); };
    this.mediaRecorder.start(100);
    this.setState('recording');
    this._startVAD();
  }

  stopRecording(): void {
    if (this._state !== 'recording' || !this.mediaRecorder) return;
    this._stopVAD();

    this.mediaRecorder.onstop = async () => {
      this.setState('processing');
      this.stream?.getTracks().forEach((t) => t.stop());
      this.stream = null;

      const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType });
      const arrayBuffer = await blob.arrayBuffer();
      const b64 = this._arrayBufferToBase64(arrayBuffer);

      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'audio', data: b64 }));
      } else {
        this.setState('error');
        this.callbacks.onError?.('Conexión perdida. Intenta de nuevo.');
      }
    };
    this.mediaRecorder.stop();
  }

  private _arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    const chunkSize = 0x8000;
    let binary = '';
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunkSize)));
    }
    return btoa(binary);
  }

  disconnect(): void {
    this._stopVAD();
    this._audioQueue = [];
    this._audioPlaying = false;
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    if (this._currentAudio) { this._currentAudio.pause(); this._currentAudio = null; }
    this.mediaRecorder = null;
    this.ws?.close();
    this.ws = null;
    this.setState('idle');
  }
}
