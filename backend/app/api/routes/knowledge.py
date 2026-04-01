from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


class KnowledgeListResponse(BaseModel):
    data: list[dict]


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    _user: User = Depends(get_current_user),
) -> KnowledgeListResponse:
    # Placeholder: the knowledge feature will be implemented in a later goal.
    return KnowledgeListResponse(data=[])
