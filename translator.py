from googletrans import Translator

translator = Translator()

async def detect_language(text: str) -> str:
    result = translator.detect(text)
    return result.lang

async def translate_text(text: str, dest_lang: str) -> str:
    result = translator.translate(text, dest=dest_lang)
    return result.text