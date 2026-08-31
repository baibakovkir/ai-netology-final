import re


def extractive_summary(text: str, max_sentences: int) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?…])\s+", text) if part.strip()]
    if not sentences:
        return text.strip()[:500]
    return " ".join(sentences[:max_sentences])
