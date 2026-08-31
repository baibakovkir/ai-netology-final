import re


class EmptyModelResponseError(ValueError):
    pass


def clean_summary(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = re.sub(r"^(summary|резюме|краткое содержание)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = cleaned.strip(" \t\n\"'")
    if not cleaned:
        raise EmptyModelResponseError("LLM returned an empty summary")
    return cleaned
