# This project was developed with assistance from AI tools.
"""Tests for question set endpoints (/question-sets)."""

from unittest.mock import AsyncMock, patch

from src.core.config import settings


def _make_truth_payload():
    """Build a mock TruthPayload for testing."""
    from src.schemas.truth import (
        AnswerTruth,
        RetrievalTruth,
        TruthMetadata,
        TruthPayload,
    )

    return TruthPayload(
        answer_truth=AnswerTruth(required_concepts=["concept A", "concept B"]),
        retrieval_truth=RetrievalTruth(
            required_documents=["doc.pdf"],
            expected_chunk_refs=["chunk:1"],
            evidence_mode="grounded_from_manual_answer",
        ),
        metadata=TruthMetadata(
            generated_by_model="test-judge",
            generated_at="2026-01-01T00:00:00",
            source_chunk_ids=[1],
        ),
    )


# --- CRUD tests ---


def test_create_question_set(client):
    """Should create a question set and return its data."""
    response = client.post(
        "/question-sets/",
        json={
            "name": "Test Set",
            "questions": [{"question": "What is AI?"}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Set"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["question"] == "What is AI?"


def test_list_question_sets(client):
    """Should list created question sets."""
    client.post(
        "/question-sets/",
        json={"name": "Set A", "questions": [{"question": "Q1"}]},
    )
    response = client.get("/question-sets/")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_question_set_by_id(client):
    """Should return a single question set by ID."""
    create_resp = client.post(
        "/question-sets/",
        json={"name": "By ID", "questions": [{"question": "Q1"}]},
    )
    qs_id = create_resp.json()["id"]
    response = client.get(f"/question-sets/{qs_id}")
    assert response.status_code == 200
    assert response.json()["id"] == qs_id


def test_get_question_set_not_found(client):
    """Should return 404 for non-existent question set."""
    response = client.get("/question-sets/999")
    assert response.status_code == 404


def test_delete_question_set(client):
    """Should delete a question set."""
    create_resp = client.post(
        "/question-sets/",
        json={"name": "Delete Me", "questions": [{"question": "Q1"}]},
    )
    qs_id = create_resp.json()["id"]
    del_resp = client.delete(f"/question-sets/{qs_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/question-sets/{qs_id}")
    assert get_resp.status_code == 404


# --- Truth generation tests ---


def test_create_question_set_generates_truth(client, monkeypatch):
    """Should generate truth for questions with expected answers."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    truth = _make_truth_payload()

    with patch(
        "src.routes.question_sets.generate_truth_from_manual_answer",
        new_callable=AsyncMock,
        return_value=truth,
    ) as mock_gen:
        response = client.post(
            "/question-sets/",
            json={
                "name": "Truth Set",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_called_once()
    data = response.json()
    q = data["questions"][0]
    assert q["truth"] is not None
    assert q["truth"]["answer_truth"]["required_concepts"] == ["concept A", "concept B"]
    assert q["truth"]["retrieval_truth"]["evidence_mode"] == "grounded_from_manual_answer"


def test_create_question_set_skips_truth_when_no_judge(client, monkeypatch):
    """Should not generate truth when no judge model is configured."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "", raising=False)
    monkeypatch.setattr(settings, "MODEL_A_NAME", "", raising=False)
    monkeypatch.setattr(settings, "MODEL_B_NAME", "", raising=False)

    with patch(
        "src.routes.question_sets.generate_truth_from_manual_answer",
        new_callable=AsyncMock,
    ) as mock_gen:
        response = client.post(
            "/question-sets/",
            json={
                "name": "No Judge Set",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_not_called()


def test_create_question_set_skips_truth_without_expected_answer(client, monkeypatch):
    """Should not generate truth for questions without expected answers."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    with patch(
        "src.routes.question_sets.generate_truth_from_manual_answer",
        new_callable=AsyncMock,
    ) as mock_gen:
        response = client.post(
            "/question-sets/",
            json={
                "name": "No Expected Set",
                "questions": [{"question": "What is AI?"}],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_not_called()


def test_create_question_set_graceful_on_truth_failure(client, monkeypatch):
    """Should save question set even when truth generation fails."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    with patch(
        "src.routes.question_sets.generate_truth_from_manual_answer",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM unavailable"),
    ):
        response = client.post(
            "/question-sets/",
            json={
                "name": "Failure Set",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    q = response.json()["questions"][0]
    assert q.get("truth") is None
    assert q["expected_answer"] == "Artificial intelligence."
