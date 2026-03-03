from services.ai import cosine_similarity, predict_category, predict_priority


def test_predict_priority():
    # High Priority
    score, label = predict_priority(
        "Fire in the building", "There is a massive fire and people are trapped."
    )
    assert score == 5
    assert label == "High"

    score, label = predict_priority(
        "Electric shock risk", "Live wire fallen on the street."
    )
    assert score == 5
    assert label == "High"

    # Medium Priority
    score, label = predict_priority(
        "Water supply stopped", "No drinking water for 2 days."
    )
    assert score == 3
    assert label == "Medium"

    score, label = predict_priority("Pothole issue", "Big pothole causing traffic.")
    assert score == 3
    assert label == "Medium"

    # Low Priority (Fallback)
    score, label = predict_priority(
        "Tree needs trimming", "The branches are growing too long."
    )
    assert score == 1
    assert label == "Low"


def test_predict_category():
    # Sanitation
    category, conf = predict_category(
        "Garbage dumping", "People are throwing trash near the park."
    )
    assert category == "Sanitation & SWM"
    assert conf >= 0.40

    # Electricity
    category, conf = predict_category(
        "No electricity", "The power went out and the street lamp is broken."
    )
    assert category == "Electricity Board (DISCOM)"
    assert conf >= 0.40

    # General (Low Confidence)
    category, conf = predict_category(
        "Some random issue", "Something is completely wrong here."
    )
    assert category == "General"


def test_cosine_similarity():
    text1 = "big pothole on main street"
    text2 = "massive pothole completely blocking main street"
    text3 = "stray dogs barking all night"

    sim_1_2 = cosine_similarity(text1, text2)
    sim_1_3 = cosine_similarity(text1, text3)

    assert sim_1_2 > sim_1_3
    assert sim_1_2 > 0.4  # Should have decent similarity
    assert sim_1_3 < 0.2  # Should have very low similarity

    # Exact match
    assert cosine_similarity("hello world", "hello world") > 0.99

    # Complete mismatch
    assert cosine_similarity("apple orange", "car plane") == 0.0
