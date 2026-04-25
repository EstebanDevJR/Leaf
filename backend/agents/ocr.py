"""Agente OCR — moondream lee el texto, gemma4 estructura el JSON."""

from backend.tools.extract_receipt import extract_receipt

OCR_TOOLS = [extract_receipt]
