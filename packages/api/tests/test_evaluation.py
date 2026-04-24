# This project was developed with assistance from AI tools.
"""Tests for evaluation endpoints (/evaluations)."""

from unittest.mock import AsyncMock, patch

from src.core.config import settings

# --- Tests ---


def test_create_eval_run(client):
    """Should create an evaluation run and return its ID."""
    # Mock background task so it doesn't actually run
    with patch("src.routes.evaluation._run_evaluation"):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?", "Explain RAG."],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["eval_run_id"] >= 1
    assert data["model_name"] == "granite-3.1-8b-instruct"
    assert data["status"] == "pending"
    assert data["total_questions"] == 2
    assert "2 questions" in data["message"]


def test_create_eval_run_validates_empty_questions(client):
    """Should reject empty questions list."""
    response = client.post(
        "/evaluations/",
        json={"model_name": "granite-3.1-8b-instruct", "questions": []},
    )
    assert response.status_code == 422


def test_list_eval_runs_empty(client):
    """Should return empty list when no runs exist."""
    response = client.get("/evaluations/")
    assert response.status_code == 200
    assert response.json() == []


def test_list_eval_runs_after_create(client):
    """Should include created run in list."""
    with patch("src.routes.evaluation._run_evaluation"):
        client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )

    response = client.get("/evaluations/")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == 1
    assert runs[0]["model_name"] == "granite-3.1-8b-instruct"


def test_get_eval_run_by_id(client):
    """Should return eval run with its results."""
    with patch("src.routes.evaluation._run_evaluation"):
        create_resp = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )
    run_id = create_resp.json()["eval_run_id"]

    response = client.get(f"/evaluations/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["model_name"] == "granite-3.1-8b-instruct"
    assert "results" in data


def test_get_eval_run_not_found(client):
    """Should return 404 for non-existent eval run."""
    response = client.get("/evaluations/999")
    assert response.status_code == 404


# --- Rerun tests ---


def test_rerun_creates_new_run_with_same_questions(client, _setup_db):
    """Should create a new run copying questions from the original."""
    with patch("src.routes.evaluation._run_evaluation"):
        create_resp = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?", "Explain RAG."],
            },
        )
    original_id = create_resp.json()["eval_run_id"]

    # Seed EvalResult rows since _run_evaluation is mocked and won't create them
    import asyncio

    from db import EvalResult

    _, async_session = _setup_db

    async def _seed_results():
        async with async_session() as session:
            for q in ["What is AI?", "Explain RAG."]:
                session.add(EvalResult(eval_run_id=original_id, question=q))
            await session.commit()

    asyncio.run(_seed_results())

    with patch("src.routes.evaluation._run_evaluation"):
        rerun_resp = client.post(
            f"/evaluations/{original_id}/rerun",
            json={"model_name": "llama-3.1-8b-instruct"},
        )

    assert rerun_resp.status_code == 201
    data = rerun_resp.json()
    assert data["model_name"] == "llama-3.1-8b-instruct"
    assert data["total_questions"] == 2
    assert f"run #{original_id}" in data["message"]
    assert data["eval_run_id"] != original_id


def test_rerun_not_found(client):
    """Should return 404 when original run does not exist."""
    response = client.post(
        "/evaluations/999/rerun",
        json={"model_name": "llama-3.1-8b-instruct"},
    )
    assert response.status_code == 404


# --- Compare tests ---


def test_compare_two_runs(client):
    """Should return side-by-side comparison of two runs."""
    with patch("src.routes.evaluation._run_evaluation"):
        resp_a = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )
        resp_b = client.post(
            "/evaluations/",
            json={
                "model_name": "llama-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )

    id_a = resp_a.json()["eval_run_id"]
    id_b = resp_b.json()["eval_run_id"]

    response = client.get(f"/evaluations/compare?run_a_id={id_a}&run_b_id={id_b}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_a"]["id"] == id_a
    assert data["run_b"]["id"] == id_b
    assert len(data["metrics"]) == 11
    assert data["metrics"][0]["metric"] == "groundedness"


def test_compare_not_found(client):
    """Should return 404 when a run does not exist."""
    with patch("src.routes.evaluation._run_evaluation"):
        resp = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": ["What is AI?"],
            },
        )
    run_id = resp.json()["eval_run_id"]

    response = client.get(f"/evaluations/compare?run_a_id={run_id}&run_b_id=999")
    assert response.status_code == 404


# --- Inline truth generation tests ---


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


def test_create_eval_run_generates_truth_for_inline_questions(client, monkeypatch):
    """Should generate truth for inline questions with expected answers."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    truth = _make_truth_payload()

    with (
        patch("src.routes.evaluation._run_evaluation"),
        patch(
            "src.routes.evaluation.generate_truth_from_manual_answer",
            new_callable=AsyncMock,
            return_value=truth,
        ) as mock_gen,
    ):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_called_once()


def test_create_eval_run_skips_truth_when_no_judge(client, monkeypatch):
    """Should not generate truth when no judge model is configured."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "", raising=False)
    monkeypatch.setattr(settings, "MODEL_A_NAME", "", raising=False)
    monkeypatch.setattr(settings, "MODEL_B_NAME", "", raising=False)

    with (
        patch("src.routes.evaluation._run_evaluation"),
        patch(
            "src.routes.evaluation.generate_truth_from_manual_answer",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_not_called()


def test_create_eval_run_skips_truth_when_already_present(client, monkeypatch):
    """Should not regenerate truth when question already has truth."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    truth_dict = _make_truth_payload().model_dump(mode="json")

    with (
        patch("src.routes.evaluation._run_evaluation"),
        patch(
            "src.routes.evaluation.generate_truth_from_manual_answer",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": [
                    {
                        "question": "What is AI?",
                        "expected_answer": "Artificial intelligence.",
                        "truth": truth_dict,
                    },
                ],
            },
        )

    assert response.status_code == 201
    mock_gen.assert_not_called()


def test_create_eval_run_graceful_on_truth_failure(client, monkeypatch):
    """Should still create run when truth generation fails."""
    monkeypatch.setattr(settings, "JUDGE_MODEL_NAME", "test-judge", raising=False)

    with (
        patch("src.routes.evaluation._run_evaluation"),
        patch(
            "src.routes.evaluation.generate_truth_from_manual_answer",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM unavailable"),
        ),
    ):
        response = client.post(
            "/evaluations/",
            json={
                "model_name": "granite-3.1-8b-instruct",
                "questions": [
                    {"question": "What is AI?", "expected_answer": "Artificial intelligence."},
                ],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["total_questions"] == 1
