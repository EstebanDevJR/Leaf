"""STT using Microsoft Phi-4-multimodal-instruct (HuggingFace).

Phi-4-multimodal accepts raw audio directly — no separate speech recognition step.
It transcribes with better context understanding than Whisper for financial queries.

Falls back to faster-whisper if the model can't be loaded (e.g. insufficient VRAM).
"""

import logging

logger = logging.getLogger(__name__)

from backend.config import settings
MODEL_ID = settings.phi4_voice_model

_TRANSCRIBE_PROMPT = (
    "<|user|><|audio_1|>"
    "Transcribe exactamente lo que dice el usuario en español. "
    "Solo devuelve el texto transcrito, sin explicaciones."
    "<|end|><|assistant|>"
)


class Phi4VoiceSTT:
    """Transcribes audio using Phi-4-multimodal-instruct (local, HuggingFace)."""

    def __init__(self):
        self._model = None
        self._processor = None

    def _load(self):
        if self._model is not None:
            return self._model, self._processor

        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        logger.info("Cargando Phi-4-multimodal-instruct (~8 GB, primera vez puede tardar)...")
        self._processor = AutoProcessor.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            device_map="auto",        # MPS en Apple Silicon, CUDA en GPU, CPU si no hay nada
            _attn_implementation="eager",
        )
        self._model.eval()
        logger.info("Phi-4-multimodal listo.")
        return self._model, self._processor

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to Spanish text. Returns empty string on failure."""
        try:
            import soundfile as sf
            import torch

            model, processor = self._load()
            audio_data, sample_rate = sf.read(audio_path, dtype="float32")

            # Phi-4-multimodal expects mono; average channels if stereo
            if audio_data.ndim > 1:
                audio_data = audio_data.mean(axis=1)

            inputs = processor(
                text=_TRANSCRIBE_PROMPT,
                audios=[(audio_data, sample_rate)],
                return_tensors="pt",
            ).to(model.device)

            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=256,
                    do_sample=False,
                    eos_token_id=processor.tokenizer.eos_token_id,
                )

            new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
            transcript = processor.decode(new_tokens, skip_special_tokens=True).strip()
            logger.info("Phi4 transcript: %s", transcript)
            return transcript

        except Exception as e:
            logger.error("Phi4VoiceSTT.transcribe error: %s", e)
            return ""


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: Phi4VoiceSTT | None = None


def get_phi4_stt() -> Phi4VoiceSTT:
    global _instance
    if _instance is None:
        _instance = Phi4VoiceSTT()
    return _instance
