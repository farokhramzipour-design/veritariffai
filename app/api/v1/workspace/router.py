"""
Collaborative Workspace API.

Manages per-shipment participants and in-workspace messaging.

All routes are protected (JWT required via the parent router dependency).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, get_current_user
from app.core.responses import ok

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory stores  (replace with DB in production)
# ---------------------------------------------------------------------------

# _participants[shipment_id] = [ {id, user_id, email, name, role, access_level, ...} ]
_participants: Dict[str, List[Dict[str, Any]]] = {}

# _messages[shipment_id] = [ {id, sender_id, sender_name, body, created_at} ]
_messages: Dict[str, List[Dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------

class ParticipantInviteRequest(BaseModel):
    email: str = Field(..., description="Email address of the invitee")
    name: Optional[str] = Field(None, description="Display name")
    role: str = Field(
        ...,
        description="Role in this shipment: EXPORTER | IMPORTER | FORWARDER | CUSTOMS_AGENT | OBSERVER",
    )
    access_level: str = Field(
        "VIEW",
        description="Access level: FULL | EDIT | VIEW",
    )


@router.post(
    "/{shipment_id}/participants",
    response_model=dict,
    status_code=201,
    summary="Invite a participant to the workspace",
)
async def invite_participant(
    shipment_id: str,
    body: ParticipantInviteRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    Add a participant to the collaborative workspace for a shipment.

    The participant receives an invitation email (mocked) and can view/edit
    the shipment according to their assigned access level.
    """
    participant_id = str(uuid.uuid4())
    now = _now()

    valid_roles = {"EXPORTER", "IMPORTER", "FORWARDER", "CUSTOMS_AGENT", "OBSERVER"}
    role = body.role.upper()
    if role not in valid_roles:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}",
        )

    valid_access = {"FULL", "EDIT", "VIEW"}
    access = body.access_level.upper()
    if access not in valid_access:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid access_level '{access}'. Must be one of: {', '.join(sorted(valid_access))}",
        )

    participant: Dict[str, Any] = {
        "id": participant_id,
        "shipment_id": shipment_id,
        "invited_by": user.id,
        "email": body.email,
        "name": body.name or body.email.split("@")[0],
        "role": role,
        "access_level": access,
        "status": "INVITED",   # INVITED | ACTIVE | DECLINED
        "online": False,
        "joined_at": None,
        "invited_at": now,
    }

    _participants.setdefault(shipment_id, []).append(participant)
    return ok(participant)


@router.get(
    "/{shipment_id}/participants",
    response_model=dict,
    summary="List workspace participants",
)
async def list_participants(
    shipment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return all participants in the workspace for a shipment."""
    items = _participants.get(shipment_id, [])
    return ok({"participants": items, "total": len(items)})


@router.delete(
    "/{shipment_id}/participants/{participant_id}",
    response_model=dict,
    summary="Remove a participant from the workspace",
)
async def remove_participant(
    shipment_id: str,
    participant_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Remove a participant from the workspace. Only the inviting user can remove participants."""
    items = _participants.get(shipment_id, [])
    for i, p in enumerate(items):
        if p["id"] == participant_id:
            if p["invited_by"] != user.id:
                raise HTTPException(
                    status_code=403,
                    detail="You can only remove participants you invited.",
                )
            removed = items.pop(i)
            return ok({"removed": True, "participant": removed})
    raise HTTPException(status_code=404, detail=f"Participant '{participant_id}' not found.")


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------

class MessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000, description="Message text")
    reply_to: Optional[str] = Field(None, description="Optional parent message ID for threads")


@router.post(
    "/{shipment_id}/messages",
    response_model=dict,
    status_code=201,
    summary="Post a message to the workspace",
)
async def post_message(
    shipment_id: str,
    body: MessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Post a new message in the collaborative workspace for a shipment."""
    message_id = str(uuid.uuid4())
    now = _now()

    message: Dict[str, Any] = {
        "id": message_id,
        "shipment_id": shipment_id,
        "sender_id": user.id,
        "sender_email": user.email,
        "body": body.body,
        "reply_to": body.reply_to,
        "created_at": now,
        "edited_at": None,
    }

    _messages.setdefault(shipment_id, []).append(message)
    return ok(message)


@router.get(
    "/{shipment_id}/messages",
    response_model=dict,
    summary="List messages in the workspace",
)
async def list_messages(
    shipment_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Return all messages for a shipment workspace, oldest first."""
    items = _messages.get(shipment_id, [])
    return ok({"messages": items, "total": len(items)})


@router.delete(
    "/{shipment_id}/messages/{message_id}",
    response_model=dict,
    summary="Delete a message",
)
async def delete_message(
    shipment_id: str,
    message_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a message. Only the original sender can delete their own messages."""
    items = _messages.get(shipment_id, [])
    for i, m in enumerate(items):
        if m["id"] == message_id:
            if m["sender_id"] != user.id:
                raise HTTPException(
                    status_code=403, detail="You can only delete your own messages."
                )
            removed = items.pop(i)
            return ok({"deleted": True, "message": removed})
    raise HTTPException(status_code=404, detail=f"Message '{message_id}' not found.")
