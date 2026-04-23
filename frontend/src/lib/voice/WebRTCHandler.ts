/**
 * VoiceHandler — records audio via MediaRecorder, sends it over WebSocket,
 * and plays back synthesized audio from the Leaf voice pipeline.
 *
 * Protocol: see backend/api/routes/voice_webrtc.py
 */

export type VoiceState = 'idle' | 'connecting' | 'ready' | 'recording' | 'processing' | 'playing' | 'error';

export interface VoiceHandlerCallbacks {
  onStateChange?: (state: VoiceState) => void;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
  onError?: (message: string) => void;
}

const WS_URL = `${typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws'}://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000/voice/ws`;

export class VoiceHandler {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private callbacks: VoiceHandlerCallbacks;
  private _state: VoiceState = 'idle';

  constructor(callbacks: VoiceHandlerCallbacks = {}) {
    this.callbacks = callbacks;
  }

  get state(): VoiceState {
    return this._state;
  }

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

      ws.onopen = () => {
        this.ws = ws;
        this.setState('ready');
        resolve();
      };

      ws.onerror = () => {
        this.setState('error');
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = () => {
        if (this._state !== 'idle') this.setState('idle');
        this.ws = null;
      };

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

        case 'audio':
          this.setState('playing');
          this._playBase64Audio(msg.data).finally(() => {
            if (this._state === 'playing') this.setState('ready');
          });
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

  private async _playBase64Audio(b64: string): Promise<void> {
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const ctx = new AudioContext();
    const buffer = await ctx.decodeAudioData(bytes.buffer);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    return new Promise((resolve) => {
      source.onended = () => {
        ctx.close();
        resolve();
      };
      source.start();
    });
  }

  async startRecording(): Promise<void> {
    if (this._state !== 'ready') return;
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      await this.connect();
    }

    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioChunks = [];

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    };

    this.mediaRecorder.start(100);
    this.setState('recording');
  }

  stopRecording(): void {
    if (this._state !== 'recording' || !this.mediaRecorder) return;

    this.mediaRecorder.onstop = async () => {
      this.setState('processing');

      // Stop all mic tracks
      this.stream?.getTracks().forEach((t) => t.stop());
      this.stream = null;

      const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType });

      // Convert to ArrayBuffer → base64 and send
      const arrayBuffer = await blob.arrayBuffer();
      const b64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'audio', data: b64 }));
      } else {
        this.setState('error');
        this.callbacks.onError?.('Conexión perdida. Intenta de nuevo.');
      }
    };

    this.mediaRecorder.stop();
  }

  disconnect(): void {
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.mediaRecorder = null;
    this.ws?.close();
    this.ws = null;
    this.setState('idle');
  }
}
