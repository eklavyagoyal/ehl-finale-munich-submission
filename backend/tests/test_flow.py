"""End-to-end through the API in mock mode: ingest -> themes -> seed -> draft -> simulate -> PM decisions -> audit."""

import time

import pytest
from sqlalchemy import text

from tests.conftest import FIXTURES


def wait_for(client, run_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/simulations/{run_id}").json()["run"]
        if run["status"] not in ("queued", "running"):
            return run
        time.sleep(0.5)
    raise AssertionError("run did not finish")


@pytest.fixture(scope="module")
def drafted(client):
    response = client.post("/api/ingest", json={"kind": "batches", "path": str(FIXTURES / "batches")})
    assert response.status_code == 200, response.text
    counts = response.json()["counts"]
    assert counts["records"] == 12 and counts["derived_claims"] >= 4
    built = client.post("/api/themes/build", json={"include_examples": True, "include_pending_claims": True}).json()
    assert built["themes"] > 0
    assert client.post("/api/agents/seed").json()["created"] > 0
    draft = client.post("/api/requirements/draft", json={"market": "US", "limit": 3}).json()
    assert len(draft["created"]) >= 2, draft
    return [item["id"] for item in draft["created"]]


def test_themes_count_reviews_once_per_feature(client, drafted):
    themes = client.get("/api/themes", params={"market": "US"}).json()["items"]
    carplay = next(t for t in themes if t["feature_key"] == "apple_carplay")
    assert carplay["mention_review_count"] == 3 and carplay["direct_review_count"] == 3
    assert carplay["pain_review_count"] == 1 and carplay["request_review_count"] == 2


def test_requirement_has_the_eight_fields_and_gates(client, drafted):
    detail = client.get(f"/api/requirements/{drafted[0]}").json()
    req = detail["requirement"]
    for field in ("id", "description", "score", "prioritization_rationale", "evidence_level", "assumptions", "uncertainties", "status"):
        assert field in req
    assert any(e["relation"] == "supporting" and e["quote_verified"] for e in detail["evidence"])
    assert detail["gates"]["evidence_traceability"]["value"] == "pass"
    assert detail["gates"]["model_market_applicability"]["value"] == "pass"
    assert req["kano_class"] in {"must_be", "performance", "attractive", "indifferent", "reverse", "unclear"}


def test_simulation_decision_challenge_and_audit(client, drafted):
    run = client.post("/api/simulations", json={"requirement_ids": drafted}).json()
    finished = wait_for(client, run["id"])
    assert finished["status"] == "completed", finished
    results = client.get(f"/api/simulations/{run['id']}/results").json()["requirements"]
    first = results[drafted[0]]
    assert len(first["persona_responses"]) == 12
    # Committee for a US case: PM, design, engineering, quality, finance and only the US sales lead.
    departments = {m["agent_id"] for m in first["department_memos"]}
    assert departments == {"dept:product-management", "dept:design", "dept:engineering", "dept:quality",
                           "dept:finance", "dept:sales-us"}
    assert first["recommendation"] and len(first["votes"]) == 3
    assert first["recommendation"][0]["challenge"]["counter_position"]
    detail = client.get(f"/api/requirements/{drafted[0]}").json()
    assert detail["requirement"]["status"] == "in_review"
    assert detail["requirement"]["score_low"] <= detail["requirement"]["score"] <= detail["requirement"]["score_high"]

    # Only humans decide.
    assert client.post(f"/api/requirements/{drafted[0]}/decision", headers={"X-Actor": "agent:synthesizer"},
                       json={"action": "approve", "rationale": "x"}).status_code == 403
    approved = client.post(f"/api/requirements/{drafted[0]}/decision", json={"action": "approve", "rationale": "Clear pain point."})
    assert approved.status_code == 200
    assert approved.json()["requirement"]["status"] == "approved"
    assert approved.json()["decision"]["ai_recommendation"] is not None

    challenged = client.post(f"/api/requirements/{drafted[1]}/decision",
                             json={"action": "challenge", "rationale": "Unclear for EU", "challenge_question": "Would EU owners care?"})
    followup = challenged.json()["followup_run_id"]
    assert followup and wait_for(client, followup)["status"] == "completed"

    # Edits create versions with rationale.
    edit = client.patch(f"/api/requirements/{drafted[2]}", json={"changes": {"title": "Sharper title"}, "rationale": "clarity"})
    assert edit.status_code == 200
    versions = client.get(f"/api/requirements/{drafted[2]}/versions").json()
    assert versions[-1]["snapshot"]["title"] == "Sharper title" and versions[-1]["change_reason"] == "clarity"

    trail = client.get(f"/api/requirements/{drafted[0]}/audit").json()
    actions = [event["action"] for event in trail]
    for expected in ("requirement.create", "requirement.score", "recommendation.create", "pm.approve"):
        assert expected in actions
    assert {"agent", "human", "system"} & {event["actor_type"] for event in trail}
    assert client.get("/api/audit", params={"category": "access"}).json()["total"] > 0
    assert client.get("/api/learning/agreement").json()


def test_audit_is_append_only(client, drafted):
    from parallax.db import get_engine

    with pytest.raises(Exception):
        with get_engine().begin() as connection:
            connection.execute(text("UPDATE audit_events SET action = 'tampered'"))
    with pytest.raises(Exception):
        with get_engine().begin() as connection:
            connection.execute(text("DELETE FROM audit_events"))


def test_llm_gate_blocks_unreviewed_sources(client, drafted):
    from parallax.db import session_scope
    from parallax.llm.gate import check_records

    with session_scope() as session:
        result = check_records(session, ["example-review-001-v1", "synthetic-g60-us-001-v1"], allow_unreviewed=False)
    assert result.allowed == ["synthetic-g60-us-001-v1"]
    assert result.excluded == {"example-review-001-v1": "source_not_accepted"}


def test_open_gates_block_approval_and_pm_overrides_stick(client, drafted):
    created = client.post("/api/requirements", json={
        "title": "Reliable wireless CarPlay", "description": "Phone projection never drops during a drive.",
        "market": "US", "feature_key": "apple_carplay", "rationale": "PM idea from the theme list"}).json()
    rid = created["id"]
    assert created["gates"]["evidence_traceability"] == "unknown"
    blocked = client.post(f"/api/requirements/{rid}/decision", json={"action": "approve", "rationale": "looks right"})
    assert blocked.status_code == 409

    override = client.post(f"/api/requirements/{rid}/gates/evidence_traceability",
                           json={"value": "pass", "rationale": "Checked the three CarPlay reviews myself."})
    assert override.json()["evidence_traceability"]["value"] == "pass"
    edit = client.patch(f"/api/requirements/{rid}", json={"changes": {"prioritization_rationale": "PM: top pain point in US."},
                                                        "rationale": "own wording"})
    assert edit.status_code == 200

    challenged = client.post(f"/api/requirements/{rid}/decision",
                             json={"action": "challenge", "rationale": "Need department view", "challenge_question": "Effort?"})
    assert wait_for(client, challenged.json()["followup_run_id"])["status"] == "completed"
    detail = client.get(f"/api/requirements/{rid}").json()
    assert detail["gates"]["evidence_traceability"]["value"] == "pass"
    assert detail["gates"]["evidence_traceability"]["owner"] == "pm:test"
    assert detail["requirement"]["prioritization_rationale"] == "PM: top pain point in US."
    assert client.post(f"/api/requirements/{rid}/decision", json={"action": "approve", "rationale": "ok now"}).status_code == 200

    trail = client.get(f"/api/requirements/{rid}/audit").json()
    assert any(e["action"] == "requirement.priority" and e["actor_id"] == "code:rank" for e in trail)


def test_records_market_filter_and_coverage_matrix(client, drafted):
    records = client.get("/api/records", params={"market": "US", "channel": "bmw_feedback", "limit": 1})
    assert records.status_code == 200 and records.json()["total"] == 8
    matrix = client.get("/api/coverage").json()["records_by_channel_market"]
    assert {"stream": "bmw", "channel": "bmw_feedback", "market": "US", "records": 8} in matrix


def test_admin_reset_needs_cli_token_and_keeps_audit(drafted):

    from fastapi.testclient import TestClient

    from parallax.api.app import app
    from parallax.config import get_settings

    settings = get_settings()
    settings.api_token, settings.cli_token = "service-token", "cli-token"
    try:
        client = TestClient(app)
        body = {"confirm": "DELETE ALL DATA", "rationale": "test"}
        assert client.post("/api/admin/reset", json=body).status_code == 401
        assert client.post("/api/admin/reset", json=body, headers={"Authorization": "Bearer service-token"}).status_code == 403
        audit_before = client.get("/api/audit", headers={"Authorization": "Bearer cli-token"}).json()["total"]
        done = client.post("/api/admin/reset", json=body, headers={"Authorization": "Bearer cli-token", "X-Actor": "pm:test"})
        assert done.status_code == 200 and done.json()["deleted"]["records"] >= 1
        after = client.get("/api/coverage", headers={"Authorization": "Bearer cli-token"}).json()
        assert after["records_by_channel"] == []
        assert client.get("/api/audit", headers={"Authorization": "Bearer cli-token"}).json()["total"] > audit_before
        assert len(client.get("/api/agents", headers={"Authorization": "Bearer cli-token"}).json()) > 0
    finally:
        settings.api_token, settings.cli_token = None, None
