"""FastAPI router for conversational model authoring (ADR-0020).

Mounted into `app.py`. Only `POST /authoring/sessions` exists so far (T020);
`propose`/`decide`/`render`/`config`/`state` land in later phases per
contracts/api.md.
"""

from __future__ import annotations

from fastapi import APIRouter

from modelling_specification.authoring.state import SessionStore

router = APIRouter(prefix="/authoring", tags=["authoring"])

_store = SessionStore()


@router.post("/sessions")
def create_session() -> dict[str, str]:
    return {"session_id": _store.create_session()}
