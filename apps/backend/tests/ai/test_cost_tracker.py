"""Unit tests for CostTracker (Fase 9.24)."""

from uuid import uuid4

from app.ai.cost_tracker import CostTracker


def test_calculate_cost_deterministic_and_api_models():
    tracker = CostTracker()

    # Local deterministic is free
    assert tracker.calculate_cost("local-deterministic", 1000, 500) == 0.0

    # Gemini 2.5 Flash: $0.075 / 1M in, $0.30 / 1M out
    # 1,000,000 in + 1,000,000 out = $0.375
    assert tracker.calculate_cost("gemini-2.5-flash", 1_000_000, 1_000_000) == 0.375

    # 10,000 in + 1,000 out
    # in: 10000/1e6 * 0.075 = 0.00075
    # out: 1000/1e6 * 0.30 = 0.0003
    # total = 0.00105
    assert tracker.calculate_cost("gemini-2.5-flash", 10_000, 1_000) == 0.00105


def test_record_query_cost_normal_and_anomalous():
    tracker = CostTracker(max_tokens_per_query=5000, max_cost_per_query=0.01)
    user_id = uuid4()
    conv_id = uuid4()

    # Normal query
    rec_normal = tracker.record_query_cost(
        query_id="q1",
        model="gemini-2.5-flash",
        intent="SPENDING_ANALYSIS",
        tokens_input=500,
        tokens_output=200,
        user_id=user_id,
        conversation_id=conv_id,
    )
    assert rec_normal.is_anomalous is False
    assert rec_normal.tokens_total == 700
    assert rec_normal.cost_usd > 0.0

    # Anomalous query (> 5000 tokens)
    rec_anomalous = tracker.record_query_cost(
        query_id="q2",
        model="gemini-2.5-flash",
        intent="SEMANTIC_SEARCH",
        tokens_input=6000,
        tokens_output=1000,
        user_id=user_id,
        conversation_id=conv_id,
    )
    assert rec_anomalous.is_anomalous is True
    assert rec_anomalous.tokens_total == 7000


def test_cost_summary_aggregation():
    tracker = CostTracker()
    user_a = uuid4()
    user_b = uuid4()

    tracker.record_query_cost(
        query_id="1",
        model="gemini-2.5-flash",
        intent="SPENDING_ANALYSIS",
        tokens_input=1000,
        tokens_output=500,
        user_id=user_a,
    )
    tracker.record_query_cost(
        query_id="2",
        model="gemini-2.5-flash",
        intent="COMPARISON",
        tokens_input=2000,
        tokens_output=1000,
        user_id=user_b,
    )

    # Global summary
    global_summary = tracker.get_summary()
    assert global_summary["queries_count"] == 2
    assert global_summary["total_tokens_input"] == 3000
    assert global_summary["total_tokens_output"] == 1500
    assert "SPENDING_ANALYSIS" in global_summary["by_intent"]
    assert "COMPARISON" in global_summary["by_intent"]

    # User A summary
    user_a_summary = tracker.get_summary(user_id=user_a)
    assert user_a_summary["queries_count"] == 1
    assert user_a_summary["total_tokens_input"] == 1000
