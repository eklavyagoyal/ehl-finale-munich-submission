"""LLM access for every Parallax agent: structured outputs, embeddings, web research.

Every call is logged to `llm_calls` (model, prompt version + hash, input record IDs, trimmed
request/response, tokens, latency) and counted against the run budget. In `mock` mode the same
code paths run offline with deterministic fake outputs, so the pipeline works without a key.
"""

import enum
import hashlib
import json
import math
import random
import re
import threading
import time
import types
import typing
import uuid
from typing import Any, Callable, TypeVar

from pydantic import BaseModel
from sqlalchemy import update

from parallax.config import Settings, get_settings
from parallax.db import session_scope
from parallax.llm.gate import assert_allowed
from parallax.models import LLMCall, SimRun

T = TypeVar("T", bound=BaseModel)
MAX_LOGGED_CHARS = 20000


class BudgetExceeded(RuntimeError):
    pass


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str) -> str:
    return text if len(text) <= MAX_LOGGED_CHARS else text[:MAX_LOGGED_CHARS] + f"... [{len(text) - MAX_LOGGED_CHARS} chars trimmed]"


# ------------------------------------------------------------------ mock generation


def _bounds(field_info) -> tuple[float | None, float | None]:
    low = high = None
    for meta in getattr(field_info, "metadata", []) or []:
        low = getattr(meta, "ge", getattr(meta, "gt", low))
        high = getattr(meta, "le", getattr(meta, "lt", high))
    return low, high


def _fake(annotation, rng: random.Random, name: str, field_info=None):
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Literal:
        return rng.choice(args)
    if origin in (typing.Union, types.UnionType):
        non_null = [a for a in args if a is not type(None)]
        return _fake(non_null[0], rng, name, field_info) if non_null else None
    if origin is list:
        return [_fake(args[0] if args else str, rng, name) for _ in range(rng.randint(1, 2))]
    if origin is dict:
        return {}
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return fake_instance(annotation, rng)
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return rng.choice(list(annotation))
    if annotation is bool:
        return rng.random() > 0.5
    if annotation in (int, float):
        low, high = _bounds(field_info) if field_info is not None else (None, None)
        low = 0 if low is None else low
        high = 5 if high is None else high
        value = rng.uniform(low, high)
        return int(round(value)) if annotation is int else round(value, 2)
    return f"[mock] {name.replace('_', ' ')} #{rng.randint(1, 99)}"


def fake_instance(schema: type[T], rng: random.Random) -> T:
    values = {}
    for name, info in schema.model_fields.items():
        values[name] = _fake(info.annotation, rng, name, info)
    return schema.model_validate(values)


def _mock_embedding(text: str, dim: int = 256) -> list[float]:
    vector = [0.0] * dim
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        vector[int(sha256(token)[:8], 16) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


# ------------------------------------------------------------------ client


class LLMClient:
    _lock = threading.Lock()
    _run_calls: dict[uuid.UUID, int] = {}
    _budgets: dict[uuid.UUID, int] = {}
    _local = threading.local()

    def set_budget(self, run_id: uuid.UUID, max_calls: int) -> None:
        """Per-run call budget for batch jobs whose size is known up front."""
        with self._lock:
            self._budgets[run_id] = max_calls

    def last_citations(self) -> list[dict]:
        """URL citations the web_search tool attached to this thread's last structured call."""
        return list(getattr(self._local, "citations", []) or [])

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.mode = self.settings.llm_mode
        self._openai = None
        if self.mode == "openai":
            if not self.settings.openai_api_key:
                raise RuntimeError("PARALLAX_LLM_MODE=openai needs OPENAI_API_KEY in backend/.env")
            from openai import OpenAI

            self._openai = OpenAI(api_key=self.settings.openai_api_key, max_retries=3, timeout=180)

    @property
    def provider(self) -> str:
        return "mock" if self.mode == "mock" else "openai"

    # -------------------------------------------------------------- budget + logging

    def _reserve(self, run_id: uuid.UUID | None) -> None:
        if run_id is None:
            return
        with self._lock:
            count = self._run_calls.get(run_id, 0) + 1
            limit = self._budgets.get(run_id, self.settings.max_llm_calls_per_run)
            if count > limit:
                raise BudgetExceeded(f"run {run_id} exceeded its LLM call budget ({limit})")
            self._run_calls[run_id] = count

    def _log(self, *, run_id, agent_id, requirement_id, purpose, model, prompt_version, prompt_text, record_ids,
             request: dict, response: dict | None, input_tokens: int, output_tokens: int, started: float,
             status: str, error: str | None = None) -> None:
        latency = int((time.perf_counter() - started) * 1000)
        with session_scope() as session:
            session.add(LLMCall(
                run_id=run_id, agent_id=agent_id, requirement_id=requirement_id, purpose=purpose,
                provider=self.provider, model=model, prompt_version=prompt_version, prompt_sha256=sha256(prompt_text),
                input_record_ids=list(record_ids), request=request, response=response, input_tokens=input_tokens,
                output_tokens=output_tokens, latency_ms=latency, status=status, error=error,
            ))
            if run_id is not None:
                session.execute(update(SimRun).where(SimRun.id == run_id).values(
                    llm_calls=SimRun.llm_calls + 1, input_tokens=SimRun.input_tokens + input_tokens,
                    output_tokens=SimRun.output_tokens + output_tokens,
                ))

    def _gate(self, record_ids) -> dict:
        if not record_ids:
            return {"allowed": 0, "excluded": 0}
        with session_scope() as session:
            if self.mode == "openai":
                return assert_allowed(session, list(record_ids)).as_meta()
            from parallax.llm.gate import check_records

            # Mock mode sends nothing anywhere; report what the gate would exclude.
            return {**check_records(session, list(record_ids)).as_meta(), "mock_mode_not_enforced": True}

    # -------------------------------------------------------------- calls

    def structured(self, schema: type[T], *, system: str, user: str, model: str, purpose: str, prompt_version: str,
                   agent_id: str | None = None, run_id: uuid.UUID | None = None, requirement_id: str | None = None,
                   input_record_ids: list[str] | tuple = (), web_search: bool = False,
                   mock: Callable[[random.Random], T] | None = None, reasoning_effort: str | None = None) -> T:
        """Return a validated instance of `schema`. `input_record_ids` lists every evidence record
        whose text appears in the prompt; the gate refuses the call if any is not cleared."""
        gate_meta = self._gate(input_record_ids)
        self._reserve(run_id)
        prompt_text = system + "\n\n" + user
        request = {"system": _trim(system), "user": _trim(user), "schema": schema.__name__, "web_search": web_search,
                   "gate": gate_meta}
        started = time.perf_counter()
        log = dict(run_id=run_id, agent_id=agent_id, requirement_id=requirement_id, purpose=purpose, model=model,
                   prompt_version=prompt_version, prompt_text=prompt_text, record_ids=input_record_ids, request=request,
                   started=started)
        self._local.citations = []
        if self.mode == "mock":
            rng = random.Random(sha256(f"{purpose}|{agent_id}|{requirement_id}|{prompt_text}")[:16])
            result = mock(rng) if mock else fake_instance(schema, rng)
            self._log(**log, response=result.model_dump(mode="json"), input_tokens=len(prompt_text) // 4,
                      output_tokens=len(result.model_dump_json()) // 4, status="ok")
            return result
        kwargs: dict[str, Any] = {"model": model, "instructions": system, "input": user, "text_format": schema}
        if web_search:
            kwargs["tools"] = [{"type": "web_search"}]
        if reasoning_effort and (model.startswith("gpt-5") or model.startswith("o")):
            kwargs["reasoning"] = {"effort": reasoning_effort}
        try:
            response = self._openai.responses.parse(**kwargs)
            parsed = response.output_parsed
            if parsed is None:
                raise RuntimeError("model returned no parseable output")
            usage = response.usage
            citations = []
            for item in response.output or []:
                for content in getattr(item, "content", None) or []:
                    for annotation in getattr(content, "annotations", None) or []:
                        url = getattr(annotation, "url", None)
                        if url:
                            citations.append({"url": url, "title": getattr(annotation, "title", None)})
            self._log(**log, response={"parsed": parsed.model_dump(mode="json"), "citations": citations,
                                       "response_id": response.id},
                      input_tokens=getattr(usage, "input_tokens", 0) or 0,
                      output_tokens=getattr(usage, "output_tokens", 0) or 0, status="ok")
            self._local.citations = citations
            return parsed
        except Exception as error:  # logged, then re-raised to the caller
            self._log(**log, response=None, input_tokens=0, output_tokens=0, status="error", error=repr(error)[:2000])
            raise

    def embed(self, texts: list[str], *, purpose: str, run_id: uuid.UUID | None = None,
              agent_id: str | None = None) -> list[list[float]]:
        if not texts:
            return []
        started = time.perf_counter()
        model = self.settings.embedding_model
        joined = "\n".join(texts)
        log = dict(run_id=run_id, agent_id=agent_id, requirement_id=None, purpose=purpose, model=model,
                   prompt_version="embed-v1", prompt_text=joined, record_ids=(),
                   request={"count": len(texts), "chars": len(joined)}, started=started)
        if self.mode == "mock":
            vectors = [_mock_embedding(t) for t in texts]
            self._log(**log, response={"dims": len(vectors[0])}, input_tokens=len(joined) // 4, output_tokens=0, status="ok")
            return vectors
        try:
            response = self._openai.embeddings.create(model=model, input=texts)
            vectors = [item.embedding for item in response.data]
            self._log(**log, response={"dims": len(vectors[0])}, input_tokens=response.usage.prompt_tokens,
                      output_tokens=0, status="ok")
            return vectors
        except Exception as error:
            self._log(**log, response=None, input_tokens=0, output_tokens=0, status="error", error=repr(error)[:2000])
            raise

    def list_models(self) -> list[str]:
        if self.mode == "mock":
            return [self.settings.model_fast, self.settings.model_strong, *self.settings.judge_models]
        return sorted(m.id for m in self._openai.models.list().data)


_client: LLMClient | None = None
_client_lock = threading.Lock()


def get_llm() -> LLMClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = LLMClient()
        return _client


def reset_llm() -> None:
    global _client
    with _client_lock:
        _client = None


def to_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
