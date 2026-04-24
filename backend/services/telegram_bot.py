"""Telegram bot — interfaz conversacional y notificaciones push del Investigador.

Arquitectura:
  El bot corre en un hilo daemon con su propio event loop para evitar conflictos
  con el event loop de uvicorn/FastAPI. python-telegram-bot v21 gestiona señales
  y el ciclo de vida de polling internamente; integrarlo en el loop de FastAPI
  causa que el polling nunca arranque correctamente.

Flujo de voz:
  Usuario envía nota de voz (OGG) → Groq Whisper (STT) → agente principal → gTTS → nota de voz
El investigador puede mandar notas de voz usando send_voice_notification().
"""

import asyncio
import io
import logging
import os
import re
import tempfile
import threading

logger = logging.getLogger(__name__)

_bot_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _strip_markdown(text: str) -> str:
    """Elimina el formato markdown para que el TTS no lea símbolos en voz alta."""
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    text = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\$\s*([\d.,]+)', r'\1 pesos', text)
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _md_to_tg_html(text: str) -> str:
    """Convierte markdown del LLM a HTML de Telegram (parse_mode='HTML').

    Telegram HTML soporta: <b>, <i>, <u>, <s>, <code>, <pre>, <a href>.
    Hay que escapar &, < y > del texto original antes de insertar las etiquetas.
    """
    import html as html_mod
    # 1. Escapar caracteres especiales HTML del contenido original
    text = html_mod.escape(text)
    # 2. Bloques de código (``` ... ```) → <pre><code>
    text = re.sub(r'```[a-z]*\n?([\s\S]*?)```', r'<pre><code>\1</code></pre>', text)
    # 3. Negrita: **texto** → <b>texto</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
    # 4. Itálica: *texto* → <i>texto</i>  (después de negrita para no interferir)
    text = re.sub(r'\*([^*\n]+?)\*', r'<i>\1</i>', text)
    # 5. Itálica con guión bajo: _texto_ → <i>texto</i>
    text = re.sub(r'_([^_\n]+?)_', r'<i>\1</i>', text)
    # 6. Código inline: `código` → <code>código</code>
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # 7. Encabezados: ## Título → <b>Título</b>
    text = re.sub(r'^#{1,6}\s+(.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    # 8. Links: [texto](url) → <a href="url">texto</a>
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', text)
    # 9. Líneas horizontales → salto de línea doble
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '\n', text, flags=re.MULTILINE)
    return text.strip()


def _get_token() -> str | None:
    from backend.config import settings
    return settings.telegram_bot_token or None


def _build_and_run():
    """Punto de entrada del hilo del bot. Crea su propio event loop."""
    logger.info("Telegram bot: arrancando hilo dedicado...")
    try:
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            filters,
        )
    except ImportError:
        logger.warning(
            "python-telegram-bot no instalado — bot desactivado. "
            "Ejecuta: uv add python-telegram-bot"
        )
        return

    token = _get_token()
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN no configurado — bot omitido.")
        return

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Hola 👋 Soy Leaf 🌿, tu asistente financiero personal.\n\n"
            "Comandos disponibles:\n"
            "/gastos — Gastos del mes\n"
            "/resumen — Resumen financiero\n"
            "/metas — Metas de ahorro\n"
            "/alertas — Alertas activas\n\n"
            "O simplemente escríbeme lo que necesitas."
        )

    async def gastos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from backend.tools.summarize_month import summarize_month
        result = await asyncio.to_thread(summarize_month.invoke, {"month": "current"})
        await update.message.reply_text(_md_to_tg_html(result)[:4096], parse_mode="HTML")

    async def resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from backend.tools.generate_insight_report import generate_insight_report
        result = await asyncio.to_thread(generate_insight_report.invoke, {"period_days": 30})
        html_result = _md_to_tg_html(result)
        for chunk in [html_result[i:i+4096] for i in range(0, len(html_result), 4096)]:
            await update.message.reply_text(chunk, parse_mode="HTML")

    async def metas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from backend.tools.savings_goal_tools import list_savings_goals
        result = await asyncio.to_thread(list_savings_goals.invoke, {"profile_id": "default"})
        await update.message.reply_text(_md_to_tg_html(result)[:4096], parse_mode="HTML")

    async def alertas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from sqlmodel import Session, select
        from backend.db.database import engine
        from backend.models.alert import Alert
        with Session(engine) as session:
            active = session.exec(
                select(Alert).where(Alert.dismissed_at.is_(None))
                .order_by(Alert.triggered_at.desc()).limit(5)
            ).all()
        if not active:
            await update.message.reply_text("✅ Sin alertas activas.")
            return
        lines = [f"🔔 Alertas activas ({len(active)}):\n"]
        for a in active:
            icon = "🚨" if a.severity == "urgent" else "⚠️" if a.severity == "warn" else "ℹ️"
            lines.append(f"{icon} {a.message}")
        await update.message.reply_text("\n".join(lines))

    async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Texto libre → agente Leaf → respuesta."""
        user_text = update.message.text
        chat_id = str(update.effective_chat.id)
        logger.info("Telegram mensaje recibido de chat %s: %s", chat_id, user_text[:60])
        await update.message.reply_text("⏳ Procesando...")
        try:
            from backend.agents.orchestrator import get_agent
            agent = get_agent()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [{"role": "user", "content": user_text}]},
                {"configurable": {"thread_id": f"telegram_{chat_id}"}},
            )
            messages = result.get("messages", [])
            reply = next(
                (m.content for m in reversed(messages)
                 if hasattr(m, "content") and m.content and m.type == "ai"),
                "No pude procesar tu mensaje."
            )
            await update.message.reply_text(_md_to_tg_html(reply)[:4096], parse_mode="HTML")
        except Exception as e:
            logger.error("handle_text error: %s", e, exc_info=True)
            await update.message.reply_text("Ocurrió un error. Intenta de nuevo.")

    async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Nota de voz OGG → STT → agente → TTS → nota de voz de respuesta."""
        chat_id = str(update.effective_chat.id)
        logger.info("Telegram nota de voz recibida de chat %s", chat_id)
        await update.message.reply_text("🎤 Escuché tu mensaje, procesando...")
        ogg_path = None
        try:
            voice_file = await ctx.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                ogg_path = f.name
            await voice_file.download_to_drive(ogg_path)

            from backend.services.stt_factory import get_stt
            stt = get_stt()
            transcript = await asyncio.to_thread(stt.transcribe, ogg_path)
            if not transcript:
                await update.message.reply_text("No te entendí bien, ¿puedes repetir?")
                return
            logger.info("Transcript: %s", transcript)

            from backend.agents.orchestrator import get_agent
            agent = get_agent()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [{"role": "user", "content": transcript}]},
                {"configurable": {"thread_id": f"telegram_{chat_id}"}},
            )
            messages = result.get("messages", [])
            reply_text = next(
                (m.content for m in reversed(messages)
                 if hasattr(m, "content") and m.content and m.type == "ai"),
                "No pude procesar tu mensaje.",
            )

            # Responder con nota de voz; fallback a texto si TTS falla
            try:
                from backend.services.voice_tts import VoiceTTS
                tts = VoiceTTS()
                clean_text = _strip_markdown(reply_text)[:500]
                audio_bytes = await asyncio.to_thread(tts.synthesize, clean_text)
                if audio_bytes:
                    buf = io.BytesIO(audio_bytes)
                    buf.name = "response.mp3"
                    await update.message.reply_voice(buf)
                    if len(reply_text) > 500:
                        await update.message.reply_text(_md_to_tg_html(reply_text)[:4096], parse_mode="HTML")
                else:
                    await update.message.reply_text(_md_to_tg_html(reply_text)[:4096], parse_mode="HTML")
            except Exception as tts_err:
                logger.warning("TTS falló, enviando texto: %s", tts_err)
                await update.message.reply_text(_md_to_tg_html(reply_text)[:4096], parse_mode="HTML")

        except Exception as e:
            logger.error("handle_voice error: %s", e, exc_info=True)
            await update.message.reply_text("Ocurrió un error procesando tu voz.")
        finally:
            if ogg_path and os.path.exists(ogg_path):
                try:
                    os.unlink(ogg_path)
                except OSError:
                    pass

    # ── Construir app y arrancar en el event loop de este hilo ────────────────

    async def _main():
        tg_app = Application.builder().token(token).build()
        tg_app.add_handler(CommandHandler("start", start))
        tg_app.add_handler(CommandHandler("gastos", gastos))
        tg_app.add_handler(CommandHandler("resumen", resumen))
        tg_app.add_handler(CommandHandler("metas", metas))
        tg_app.add_handler(CommandHandler("alertas", alertas))
        tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        tg_app.add_handler(MessageHandler(filters.VOICE, handle_voice))

        async with tg_app:
            await tg_app.start()
            await tg_app.updater.start_polling(drop_pending_updates=True)
            logger.info("✅ Telegram bot listo — esperando mensajes.")

            # Esperar hasta que stop_telegram_bot() señalice la parada
            while not _stop_event.is_set():
                await asyncio.sleep(1)

            logger.info("Telegram bot: deteniendo polling...")
            await tg_app.updater.stop()
            await tg_app.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_main())
    except Exception as e:
        logger.error("❌ Telegram bot crash: %s", e, exc_info=True)
    finally:
        loop.close()
        logger.info("Telegram bot: hilo terminado.")


# ── API pública ───────────────────────────────────────────────────────────────

def start_telegram_bot():
    global _bot_thread
    token = _get_token()
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN no configurado — bot omitido.")
        return
    _stop_event.clear()
    _bot_thread = threading.Thread(target=_build_and_run, daemon=True, name="telegram-bot")
    _bot_thread.start()
    logger.info("Telegram bot: hilo arrancado.")


def stop_telegram_bot():
    global _bot_thread
    if _bot_thread and _bot_thread.is_alive():
        logger.info("Telegram bot: señalizando parada...")
        _stop_event.set()
        _bot_thread.join(timeout=8)
    _bot_thread = None


async def send_notification(message: str):
    """Envía notificación de texto al chat configurado en TELEGRAM_CHAT_ID."""
    try:
        from telegram import Bot
    except ImportError:
        return
    from backend.config import settings
    token = _get_token()
    chat_id = settings.telegram_chat_id or None
    if not token or not chat_id:
        return
    try:
        bot = Bot(token=token)
        async with bot:
            await bot.send_message(chat_id=chat_id, text=message[:4000])
    except Exception as e:
        logger.warning("send_notification failed: %s", e)


async def send_voice_notification(message: str):
    """Convierte un mensaje a nota de voz y lo envía al chat del Investigador.
    Recae en texto plano si gTTS falla.
    """
    try:
        from telegram import Bot
    except ImportError:
        return
    from backend.config import settings
    token = _get_token()
    chat_id = settings.telegram_chat_id or None
    if not token or not chat_id:
        return
    try:
        from backend.services.voice_tts import VoiceTTS
        tts = VoiceTTS()
        audio_bytes = await asyncio.to_thread(tts.synthesize, _strip_markdown(message)[:500])
        if not audio_bytes:
            raise ValueError("TTS vacío")
        bot = Bot(token=token)
        async with bot:
            buf = io.BytesIO(audio_bytes)
            buf.name = "insight.mp3"
            await bot.send_voice(chat_id=chat_id, voice=buf)
            if len(message) > 500:
                await bot.send_message(chat_id=chat_id, text=message[:4000])
    except Exception as e:
        logger.warning("send_voice_notification falló (%s), fallback texto.", e)
        await send_notification(message)
