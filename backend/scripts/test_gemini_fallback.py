import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.llm_classifier import chat_with_retry, call_gemini_api
from app.config import settings

async def test_direct_gemini():
    print("Testing direct Gemini API call...")
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with only 'OK' if you can read this."}
        ]
        result = await call_gemini_api(messages, temperature=0.0)
        print("Gemini direct response:", result.strip())
        assert "ok" in result.lower(), "Expected response to contain 'ok'"
        print("Direct Gemini API test PASSED!")
    except Exception as e:
        print("Direct Gemini API test FAILED:", e)
        raise e

async def test_groq_fallback():
    print("\nTesting Groq 429 Rate Limit Fallback to Gemini...")
    # Create a mock Groq client
    mock_client = MagicMock()
    # Mock create to raise an exception containing "rate limit 429"
    mock_client.chat.completions.create = AsyncMock(side_effect=ValueError("Rate limit 429 exceeded on Groq client"))
    
    try:
        messages = [
            {"role": "system", "content": "You are a fallback test helper."},
            {"role": "user", "content": "Reply with only 'FALLBACK_OK' if you can read this."}
        ]
        completion = await chat_with_retry(
            mock_client,
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.0
        )
        content = completion.choices[0].message.content
        print("Wrapped completion content:", content.strip())
        assert "fallback_ok" in content.lower(), "Expected response to contain 'fallback_ok'"
        print("Fallback test PASSED!")
    except Exception as e:
        print("Fallback test FAILED:", e)
        raise e

async def main():
    if not settings.google_api_key or settings.google_api_key == "your_google_key":
        print("Error: GOOGLE_API_KEY is not set in configuration settings.")
        return
    await test_direct_gemini()
    await test_groq_fallback()

if __name__ == "__main__":
    asyncio.run(main())
