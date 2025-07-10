import httpx

async def translate_libre(text: str, source: str = "auto", target: str = "en"):
    async with httpx.AsyncClient() as client:
        response = await client.post("https://libretranslate.de/translate", json={
            "q": text,
            "source": source,
            "target": target,
            "format": "text"
        })

        if response.status_code != 200:
            print(f"⚠️ Ошибка от сервера: {response.status_code}")
            print(f"Ответ сервера: {response.text}")
            return None

        try:
            data = response.json()
            return data["translatedText"]
        except Exception as e:
            print(f"❌ Ошибка при чтении JSON: {e}")
            print("Ответ:", response.text)
            return None
        

import asyncio

async def main():
    result = await translate_libre("огород", source="ru", target="en")
    if result:
        print("Перевод:", result)
    else:
        print("Не удалось получить перевод")

if __name__ == "__main__":
    asyncio.run(main())