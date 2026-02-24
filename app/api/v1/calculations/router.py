from fastapi import APIRouter, Depends, Query
from uuid import uuid4
from app.api.v1.calculations.schemas import CalculationRequest, CalculationResponse
from app.application.calculations.orchestrator import calculate_sync
from app.core.responses import ok
from app.core.deps import get_current_user, require_plan
from app.domain.plan import PlanTier


router = APIRouter()


@router.post("/sync")
async def calculate_sync_endpoint(payload: CalculationRequest, user=Depends(get_current_user)):
    result = calculate_sync(payload)
    data = {
        "request_id": str(uuid4()),
        "status": "complete",
        "confidence_score": result.confidence / 100,
        "totals": {"customs_value": {"amount": str(result.breakdown.total), "currency": "GBP"}, "total_duty": {"amount": "0.00", "currency": "GBP"}, "total_vat": {"amount": "0.00", "currency": "GBP"}, "total_excise": {"amount": "0.00", "currency": "GBP"}, "total_clearance": {"amount": "0.00", "currency": "GBP"}, "total_landed_cost": {"amount": str(result.breakdown.total), "currency": "GBP"}},
        "line_results": [],
        "warnings": [],
        "audit_trail_available": True,
        "engines_used": ["classification", "tariff_measure", "vat", "fx"],
    }
    return ok(data)


@router.post("/async")
async def calculate_async_endpoint(payload: CalculationRequest, user=Depends(require_plan(PlanTier.PRO))):
    task_id = str(uuid4())
    return ok({"task_id": task_id, "status": "pending", "poll_url": f"/api/v1/calculations/{task_id}/status"})


@router.get("/{task_id}/status")
async def calc_status(task_id: str):
    return ok({"task_id": task_id, "status": "processing", "progress": {"lines_processed": 0, "lines_total": 0}})


@router.get("/{request_id}/result")
async def calc_result(request_id: str):
    return ok({"request_id": request_id, "status": "complete"})


@router.get("/{request_id}/audit")
async def calc_audit(request_id: str, user=Depends(require_plan(PlanTier.PRO))):
    return ok({"steps": [{"sequence": 1, "engine": "customs_valuation", "step_name": "incoterm_gap_adjustment", "formula_description": "FOB origin", "input_snapshot": {}, "output_snapshot": {"customs_value": "9250.00"}}]})


@router.get("")
async def calc_list(limit: int = Query(20), offset: int = Query(0), status_q: str | None = Query(None), from_date: str | None = Query(None), to_date: str | None = Query(None), user=Depends(get_current_user)):
    return ok({"results": [], "total": 0, "limit": limit, "offset": offset, "has_more": False})


@router.delete("/{request_id}")
async def calc_delete(request_id: str, user=Depends(get_current_user)):
    return ok({"deleted": True})
