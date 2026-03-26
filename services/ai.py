"""
Artificial Intelligence & Machine Learning Service.
Provides heuristic text analysis, cosine similarity mathematics, and dynamic SLA deadline prediction.
This module is isolated to ensure data-processing workload doesn't intermingle with routing logic.
"""
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
    "Sanitation": {
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
    "Water Supply": {
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
    "Electricity": {
        "light",
        "pole",
        "wire",
        "shock",
        "electricity",
        "power",
        "street lamp",
        "bijli",
    },
    "Roads & Transport": {
        "road",
        "pothole",
        "broken",
        "construction",
        "bridge",
        "asphalt",
        "damage",
        "sadak",
    },
    "Parks & Recreation": {
        "park",
        "bench",
        "playground",
        "tree",
        "grass",
        "garden",
    },
    "Public Health": {
        "hospital",
        "ambulance",
        "disease",
        "fever",
        "mosquito",
        "dengue",
        "dawa",
    },
}

CATEGORY_TO_DEPARTMENT = {
    # Exact canonical names
    "Sanitation": "Sanitation",
    "Water Supply": "Water Supply",
    "Electricity": "Electricity",
    "Roads & Transport": "Roads & Transport",
    "Parks & Recreation": "Parks & Recreation",
    "Public Health": "Public Health",
    "General": "General Administration",
    # Common short-form / alias names
    "Water": "Water Supply",
    "water supply": "Water Supply",
    "Roads": "Roads & Transport",
    "Transport": "Roads & Transport",
    "Roads and Transport": "Roads & Transport",
    "Health": "Public Health",
    "Parks": "Parks & Recreation",
    "Recreation": "Parks & Recreation",
    "Electric": "Electricity",
    "Power": "Electricity",
    "Sewage": "Water Supply",
    "Drainage": "Water Supply",
    "Garbage": "Sanitation",
    "Waste": "Sanitation",
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
    """
    Cleans and tokenizes input text by forcing lowercase, extracting alphanumeric words,
    and filtering out common English stop words.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def vectorize(text: str) -> Counter:
    """
    Converts a raw string into a frequency map (Counter) of its valid tokens.
    """
    return Counter(tokenize(text))


def cosine_similarity(a: str, b: str) -> float:
    """
    Calculates the text similarity between two strings using Cosine Similarity over Term Frequency.
    Returns a float between 0.0 (completely different) and 1.0 (exact match).
    """
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
    """
    Estimates the urgency of a complaint by scanning for critical keywords.
    Returns the severity level (1-5) and a human-readable label (Low/Medium/High).
    """
    merged = f"{title} {description}".lower()

    if _contains_phrase(merged, HIGH_URGENCY_KEYWORDS):
        return 5, "High"
    if _contains_phrase(merged, MEDIUM_URGENCY_KEYWORDS):
        return 3, "Medium"
    return 1, "Low"


def predict_category(title: str, description: str) -> Tuple[str, float]:
    """
    Predicts the appropriate civic category for a complaint using a weighted keyword-matching heuristic.
    Returns the predicted category name and a confidence score multiplier (0.0 to 1.0).
    """
    merged = f"{title} {description}".lower()
    tokens = set(tokenize(merged))

    best_match = "General"
    highest_score = 0.0

    # Words that strongly indicate a specific category get a 2.0x multiplier
    # Standard words get a 1.0x multiplier
    STRONG_INDICATORS = {
        "pothole",
        "garbage",
        "water",
        "electricity",
        "police",
        "hospital",
    }

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for token in tokens & keywords:
            score += 2.0 if token in STRONG_INDICATORS else 1.0

        if score > highest_score:
            highest_score = score
            best_match = category

    # Calculate confidence based on score
    confidence = round(min(1.0, highest_score / 3.0), 2) if highest_score > 0 else 0.0

    # Enforce minimum confidence threshold (0.40)
    if confidence < 0.40:
        return "General", confidence

    return best_match, confidence


def calculate_impact_score(
    reports_count: int, priority: int, upvotes: int = 0
) -> float:
    """
    Calculates the dynamic 'Impact Score' out of 100 for a complaint.
    It heavily weights the internal severity/priority (0-50 pts) and duplicate links (12 pts/link),
    then applies a logarithmic multiplier based on community upvotes.
    """
    # Upvotes act as a dynamic community multiplier for impact score
    upvotes = upvotes or 0
    base_score = reports_count * 12 + priority * 10
    community_multiplier = 1.0 + (math.log(upvotes + 1) * 0.15)
    score = min(100.0, base_score * community_multiplier)
    return round(score, 2)


def predict_resolution_deadline(
    db, category: str, ward: str, priority: int
) -> float:
    """
    Predicts the number of hours a department will take to resolve a complaint based on:
    1. The category of the complaint.
    2. The geographic region (ward).
    3. The historical average resolution time of `Closed` or `Resolved` tickets for that combo.
    Fallback: A static SLA matrix if there's insufficient data (< 3 tickets).
    """
    from models import Complaint
    from datetime import timezone

    # Fallback static SLA matrix (in hours)
    # 5: Emergency (24h), 4: Critical (48h), 3: Urgent (7 days), 2: High (14 days), 1: Standard (30 days)
    fallback_slas = {
        5: 24,
        4: 48,
        3: 168,
        2: 336,
        1: 720
    }
    
    baseline_hours = fallback_slas.get(priority, 720)

    # 1. Fetch historical resolved/closed complaints in this exact ward and category
    historical_tickets = (
        db.query(Complaint)
        .filter(
            Complaint.category == category,
            Complaint.ward == ward,
            Complaint.status.in_(["Resolved", "Closed"]),
            Complaint.resolved_at.isnot(None),
            Complaint.is_merged.is_(False)
        )
        .all()
    )

    # 2. Insufficient data check
    if len(historical_tickets) < 3:
        return float(baseline_hours)

    # 3. Calculate average resolution time
    total_seconds = 0.0
    for ticket in historical_tickets:
        created = ticket.created_at
        resolved = ticket.resolved_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        
        diff = (resolved - created).total_seconds()
        total_seconds += diff
        
    avg_seconds = total_seconds / len(historical_tickets)
    avg_hours = avg_seconds / 3600.0
    
    # 4. Apply ML dampening heuristics
    # We do not want to allow extremely lazy departments to be given mathematically infinite SLA windows.
    # We cap the ML "slack" expansion to strictly +50% of the maximum baseline SLA.
    # Conversely, if they are incredibly fast, we tighten the SLA by up to -50% to demand peak performance.

    max_slack_hours = baseline_hours * 1.5
    min_tight_hours = baseline_hours * 0.5
    
    predicted_hours = max(min_tight_hours, min(avg_hours, max_slack_hours))
    
    return predicted_hours
