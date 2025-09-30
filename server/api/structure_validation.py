from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from server.core.validators import GeometryAnalyzer
from server.core.session_manager import SessionManager

router = APIRouter(prefix="/api/structures", tags=["validation"])

geometry_analyzer = GeometryAnalyzer()


class AnalysisRequest(BaseModel):
    constraints: Optional[Dict[str, Any]] = None


class ComparisonRequest(BaseModel):
    session_id_before: str
    session_id_after: str


@router.post("/{session_id}/analyze")
async def analyze_structure(session_id: str, request: AnalysisRequest):
    """
    Analyze crystal structure geometry for LLM agent feedback.

    Returns observations (factual measurements) and hints (interpretive suggestions).
    """
    session_manager = SessionManager()

    try:
        await session_manager.initialize()
        atoms = await session_manager.get_structure(session_id)

        if not atoms:
            raise HTTPException(status_code=404, detail="Structure not found")

        result = geometry_analyzer.analyze_structure(atoms, request.constraints)

        return {
            "success": True,
            "session_id": session_id,
            "analysis": result,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await session_manager.close()


@router.post("/compare")
async def compare_structures(request: ComparisonRequest):
    """
    Compare two structures to track iterative refinement progress.
    """
    session_manager = SessionManager()

    try:
        await session_manager.initialize()

        atoms_before = await session_manager.get_structure(request.session_id_before)
        atoms_after = await session_manager.get_structure(request.session_id_after)

        if not atoms_before or not atoms_after:
            raise HTTPException(status_code=404, detail="One or both structures not found")

        comparison = geometry_analyzer.compare_structures(atoms_before, atoms_after)

        return {
            "success": True,
            "session_id_before": request.session_id_before,
            "session_id_after": request.session_id_after,
            "comparison": comparison,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await session_manager.close()