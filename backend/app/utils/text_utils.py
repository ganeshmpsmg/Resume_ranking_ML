"""
app/utils/text_utils.py
-------------------------
Shared text-cleaning helpers and regex patterns used by the parser,
JD processor, and skill extractor.
"""

import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b"
)
LINKEDIN_REGEX = re.compile(r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+")
GITHUB_REGEX = re.compile(r"(https?://)?(www\.)?github\.com/[A-Za-z0-9_-]+")
EXPERIENCE_YEARS_REGEX = re.compile(
    r"(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Basic whitespace and artifact cleanup for extracted document text."""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\u2022|\u25cf|\u25aa|►|▪", "-", text)
    return text.strip()


def normalize_for_matching(text: str) -> str:
    """Lowercase + collapse whitespace, used for substring skill matching."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9.+#/\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_for_embedding(text: str) -> str:
    """Light cleaning suited for transformer embeddings (preserve semantics)."""
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


BASIC_STOPWORDS = set("""
a an the and or but if while is are was were be been being to of in on for
with as by at from this that these those it its it's he she they them his
her their our your you i we us not no nor so than then too very can will
just should would could may might must shall do does did doing have has
had having here there when where why how all any both each few more most
other some such only own same
""".split())


def tokenize(text: str) -> list[str]:
    text = normalize_for_matching(text)
    tokens = re.findall(r"[a-z0-9][a-z0-9+#./-]*", text)
    return [t for t in tokens if t not in BASIC_STOPWORDS and len(t) > 1]
