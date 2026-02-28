import math
import re
from collections import Counter
from typing import Iterable, Tuple

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "with",
    "I",
    "my",
    "we",
    "our",
    "there",
    "their",
    "this",
    "these",
}

CATEGORY_KEYWORDS = {
    "Sanitation & SWM": {
        "garbage",
        "trash",
        "waste",
        "clean",
        "sweep",
        "dump",
        "stink",
        "smell",
        "kachra",
        "dustbin",
    },
    "Jal Board / Water Supply": {
        "water",
        "leak",
        "pipe",
        "plumbing",
        "drain",
        "sewage",
        "overflow",
        "pani",
        "tap",
    },
    "Electricity Board (DISCOM)": {
        "light",
        "pole",
        "wire",
        "shock",
        "electricity",
        "power",
        "street lamp",
        "bijli",
    },
    "PWD & Roads": {
        "road",
        "pothole",
        "broken",
        "construction",
        "bridge",
        "asphalt",
        "damage",
        "sadak",
    },
    "Police & Security": {
        "crime",
        "police",
        "robbery",
        "accident",
        "unsafe",
        "dark",
        "theft",
    },
    "Health & Public Welfare": {
        "hospital",
        "ambulance",
        "disease",
        "fever",
        "mosquito",
        "dengue",
        "dawa",
    },
}

HIGH_URGENCY_KEYWORDS = {
    "fire",
    "flood",
    "accident",
    "collapse",
    "injury",
    "electric shock",
    "live wire",
    "sewage overflow",
    "crime",
    "medical",
}

MEDIUM_URGENCY_KEYWORDS = {
    "water",
    "garbage",
    "streetlight",
    "drainage",
    "road damage",
    "pothole",
    "pollution",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def vectorize(text: str) -> Counter:
    return Counter(tokenize(text))


def cosine_similarity(a: str, b: str) -> float:
    vec_a = vectorize(a)
    vec_b = vectorize(b)
    if not vec_a or not vec_b:
        return 0.0

    # Simple Term Frequency weighting (log smoothed)
    def tf(count):
        return 1 + math.log(count) if count > 0 else 0

    intersection = set(vec_a.keys()) & set(vec_b.keys())
    numerator = sum(tf(vec_a[token]) * tf(vec_b[token]) for token in intersection)

    sum_a = sum(tf(count) * tf(count) for count in vec_a.values())
    sum_b = sum(tf(count) * tf(count) for count in vec_b.values())
    denominator = math.sqrt(sum_a) * math.sqrt(sum_b)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _contains_phrase(text: str, phrases: Iterable[str]) -> bool:
    normalized = text.lower()
    return any(phrase in normalized for phrase in phrases)


def predict_priority(title: str, description: str) -> Tuple[int, str]:
    merged = f"{title} {description}".lower()

    if _contains_phrase(merged, HIGH_URGENCY_KEYWORDS):
        return 5, "High"
    if _contains_phrase(merged, MEDIUM_URGENCY_KEYWORDS):
        return 3, "Medium"
    return 1, "Low"


def predict_category(title: str, description: str) -> Tuple[str, float]:
    merged = f"{title} {description}".lower()
    tokens = set(tokenize(merged))

    best_match = "General"
    highest_score = 0.0

    # Words that strongly indicate a specific category get a 2.0x multiplier
    # Standard words get a 1.0x multiplier
    STRONG_INDICATORS = {"pothole", "garbage", "water", "electricity", "police", "hospital"}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for token in (tokens & keywords):
            score += 2.0 if token in STRONG_INDICATORS else 1.0
            
        if score > highest_score:
            highest_score = score
            best_match = category

    # Calculate confidence based on score
    confidence = (
        round(min(1.0, highest_score / 3.0), 2) if highest_score > 0 else 0.0
    )
    
    # Enforce minimum confidence threshold (0.40)
    if confidence < 0.40:
        return "General", confidence
        
    return best_match, confidence


def calculate_impact_score(
    reports_count: int, priority: int, upvotes: int = 0
) -> float:
    # Upvotes act as a dynamic community multiplier for impact score
    upvotes = upvotes or 0
    base_score = reports_count * 12 + priority * 10
    community_multiplier = 1.0 + (math.log(upvotes + 1) * 0.15)
    score = min(100.0, base_score * community_multiplier)
    return round(score, 2)
