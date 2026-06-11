import re

def refactor_text(text: str) -> str:
    """
    Replaces Jago-related names with Makmur-related names.
    Uses case-sensitive word boundaries to avoid replacing lowercase adjectives like 'jago'.
    """
    if not text:
        return text

    # Competitor domains and emails
    text = re.sub(r"jago\.com", "makmur.com", text, flags=re.IGNORECASE)
    
    # Order matters: replace longer specific names first
    # 1. JagoID
    text = re.sub(r"\bJagoID\b", "MakmurID", text)
    text = re.sub(r"\bJAGOID\b", "MAKMURID", text)
    
    # 2. Bank Jago
    text = re.sub(r"\bBank Jago\b", "Bank Makmur", text)
    text = re.sub(r"\bBANK JAGO\b", "BANK MAKMUR", text)
    
    # 3. Jago
    text = re.sub(r"\bJago\b", "Makmur", text)
    text = re.sub(r"\bJAGO\b", "MAKMUR", text)
    
    return text

def refactor_faq(articles: list[dict]) -> list[dict]:
    """
    Refactors a list of Q&A dictionaries.
    """
    return [
        {
            "question": refactor_text(art["question"]),
            "answer": refactor_text(art["answer"])
        }
        for art in articles
    ]
