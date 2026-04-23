"""Telegram bot — interfaz conversacional y notificaciones push del Investigador."""

import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

_bot_task: asyncio.Task | None = None


def _get_token() -> str | None:
    return os.getenv("TELEGRAM_BOT_TOKEN")


async def _run_bot():
    """Starts the Telegram bot with polling. Requires python-telegram-bot."""
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
            "python-telegram-bot no instalado. "
            "Ejecuta: uv add python-telegram-bot. El bot de Telegram no estará disponible."
        )
        return

    token = _get_token()
    if not token:
        logger.info("TELEGRAM_BOT_TOKEN no configurado — bot desactivado.")
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
        result = summarize_month.invoke({"month": "current"})
        await update.message.reply_text(result)

    async def resumen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from backend.tools.generate_insight_report import generate_insight_report
        result = generate_insight_report.invoke({"period_days": 30})
        # Telegram messages max 4096 chars
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)

    async def metas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from backend.tools.savings_goal_tools import list_savings_goals
        result = list_savings_goals.invoke({"profile_id": "default"})
        await update.message.reply_text(result)

    async def alertas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        from sqlmodel import Session, select
        from backend.db.database import engine
        from backend.models.alert import Alert
        with Session(engine) as session:
            active = session.exec(
                select(Alert).where(Alert.dismissed_at.is_(None)).order_by(Alert.triggered_at.desc()).limit(5)
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
        """Routes free text to the Leaf chat agent."""
        user_text = update.message.text
        await update.message.reply_text("⏳ Procesando...")
        try:
            from backend.agents.orchestrator import get_agent
            agent = get_agent()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [{"role": "user", "content": user_text}]},
            )
            messages = result.get("messages", [])
            reply = next(
                (m.content for m in reversed(messages) if hasattr(m, "content") and m.content and m.type == "ai"),
                "No pude procesar tu mensaje."
            )
            await update.message.reply_text(reply[:4000])
        except Exception as e:
            logger.error("Telegram handle_text error: %s", e)
            await update.message.reply_text("Ocurrió un error. Intenta de nuevo.")

    async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Receives a Telegram voice message (OGG), transcribes via Groq, replies with text."""
        await update.message.reply_text("🎤 Escuché tu mensaje, procesando...")
        ogg_path = None
        try:
            # 1. Download the OGG Opus file from Telegram
            voice_file = await ctx.bot.get_file(update.message.voice.file_id)
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                ogg_path = f.name
            await voice_file.download_to_drive(ogg_path)

            # 2. Transcribe — Groq Whisper accepts OGG/Opus natively
            from backend.services.stt_factory import get_stt
            stt = get_stt()
            transcript = await asyncio.to_thread(stt.transcribe, ogg_path)
            if not transcript:
                await update.message.reply_text("No te entendí bien, ¿puedes repetir?")
                return

            logger.info("Voice transcript: %s", transcript)

            # 3. Route to Leaf orchestrator
            from backend.agents.orchestrator import get_agent
            agent = get_agent()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [{"role": "user", "content": transcript}]},
            )
            messages = result.get("messages", [])
            reply_text = next(
                (m.content for m in reversed(messages) if hasattr(m, "content") and m.content and m.type == "ai"),
                "No pude procesar tu mensaje.",
            )

            await update.message.reply_text(reply_text[:4000])

        except Exception as e:
            logger.error("Telegram handle_voice error: %s", e)
            await update.message.reply_text("Ocurrió un error procesando tu voz. Intenta de nuevo.")
        finally:
            if ogg_path and os.path.exists(ogg_path):
                try:
                    os.unlink(ogg_path)
                except OSError:
                    pass

    # ── Build and run ─────────────────────────────────────────────────────────

    app = (
        Application.builder()
        .token(token)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gastos", gastos))
    app.add_handler(CommandHandler("resumen", resumen))
    app.add_handler(CommandHandler("metas", metas))
    app.add_handler(CommandHandler("alertas", alertas))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Telegram bot iniciado con polling")
    await app.run_polling(close_loop=False)


async def send_notification(message: str):
    """Sends a push notification to the configured Telegram chat."""
    try:
        from telegram import Bot
    except ImportError:
        return

    token = _get_token()
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    try:
        bot = Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=message[:4000])
    except Exception as e:
        logger.warning("Telegram send_notification failed: %s", e)


def start_telegram_bot() -> asyncio.Task | None:
    global _bot_task
    if not _get_token():
        logger.info("TELEGRAM_BOT_TOKEN no configurado — bot omitido.")
        return None
    _bot_task = asyncio.create_task(_run_bot())
    return _bot_task


def stop_telegram_bot():
    global _bot_task
    if _bot_task:
        _bot_task.cancel()
        _bot_task = None
