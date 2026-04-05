import os
import json
import re
from collections import Counter


def generate_caption(clip_text: str, language: str, duration: float) -> dict:
    """
    Generate social media caption for a clip using Groq API (free tier).
    Falls back to template-based extraction if GROQ_API_KEY is not set or API fails.

    Returns:
        {"hook": str, "caption": str, "hashtags": [str]}
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("  No GROQ_API_KEY — using template fallback for caption")
        return _template_fallback(clip_text)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        lang_str = "Bahasa Indonesia" if language == "id" else "English"
        prompt = (
            f"You are a social media content creator. Based on this {duration:.0f}-second "
            f"video transcript, write engaging content in {lang_str}.\n\n"
            f"Transcript: {clip_text[:800]}\n\n"
            f"Respond ONLY with a valid JSON object (no markdown, no explanation):\n"
            '{{"hook": "<one punchy sentence max 15 words>", '
            '"caption": "<2-3 sentences max 120 words>", '
            '"hashtags": ["word1","word2","word3","word4","word5"]}}'
        )

        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=350,
            temperature=0.7,
        )
        raw = res.choices[0].message.content.strip()
        print(f"  Groq caption raw response: {raw[:200]}")

        # Extract JSON even if model adds extra surrounding text
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            # Normalise hashtags — strip leading # if model included them
            data["hashtags"] = [h.lstrip("#") for h in data.get("hashtags", [])]
            return data

        return _template_fallback(clip_text)

    except Exception as e:
        print(f"  Caption generation failed: {e}. Using template fallback.")
        return _template_fallback(clip_text)


def _template_fallback(clip_text: str) -> dict:
    """Simple extraction-based fallback — no external API needed."""
    sentences = [s.strip() for s in clip_text.replace("\n", " ").split(".") if len(s.strip()) > 20]

    hook = sentences[0][:120] if sentences else clip_text[:120]
    caption = ". ".join(sentences[1:3]).strip() if len(sentences) > 1 else clip_text[:200]
    if caption and not caption.endswith("."):
        caption += "."

    # Top-5 content words as hashtags
    stop = {"yang", "dan", "di", "ke", "dari", "untuk", "dengan", "adalah", "ini", "itu",
            "the", "and", "for", "that", "this", "with", "have", "you", "are", "was",
            "not", "but", "they", "from", "your", "more", "will", "been", "than"}
    words = [w.lower().strip(".,!?\"'") for w in clip_text.split() if len(w) > 4]
    content_words = [w for w in words if w not in stop and w.isalpha()]
    top_words = [w for w, _ in Counter(content_words).most_common(5)]

    return {"hook": hook, "caption": caption, "hashtags": top_words}
