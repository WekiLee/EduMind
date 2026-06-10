"""兼容性评估 API。"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user_id

router = APIRouter(prefix="/assessment", tags=["评估"])

AnswerValue = Annotated[int, Field(ge=0, le=3)]


class AssessmentRequest(BaseModel):
    """评估请求。"""

    user_id: str
    subject: str = Field(..., min_length=1, max_length=100)
    answers: list[AnswerValue] = Field(..., min_length=1, max_length=200)


@router.post("")
async def create_assessment(
    req: AssessmentRequest,
    current_user_id: str = Depends(get_current_user_id),
):
    """根据兼容性答题结果返回低风险评估摘要。"""
    if req.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能提交其他用户的评估")

    total = len(req.answers)
    score = sum(1 for answer in req.answers if answer > 0)
    percentage = round(score / total * 100, 1) if total else 0.0
    if percentage >= 80:
        difficulty_level = "advanced"
        recommendation = "可以进入更高难度材料，但仍建议结合真实题目正确率复核。"
    elif percentage >= 60:
        difficulty_level = "intermediate"
        recommendation = "建议继续当前难度，并补充针对性练习。"
    else:
        difficulty_level = "beginner"
        recommendation = "建议先巩固基础概念，再逐步增加题目复杂度。"

    return {
        "data": {
            "user_id": req.user_id,
            "subject": req.subject,
            "score": score,
            "total": total,
            "percentage": percentage,
            "difficulty_level": difficulty_level,
            "timestamp": datetime.now(UTC).isoformat(),
            "assessment_method": "compatibility_count_positive_answers",
            "calibrated": False,
            "confidence": "low",
            "interpretation": "该兼容接口仅统计非零答案数量，不代表经过校准的真实能力评估。",
            "fairness_note": "结果不得单独用于分班、升学、奖惩等高影响教育决策。",
            "recommendation": recommendation,
        }
    }
