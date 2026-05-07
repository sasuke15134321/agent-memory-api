"""
Creator Experiment Log API
Lost Fauna等のクリエイター向け実験管理システム
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from experiment_engine import ExperimentEngine, Platform, ChangeType, Metric

app = FastAPI(
    title="Creator Experiment Log API",
    description="Lost Fauna等のクリエイター向け実験管理システム",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize experiment engine
experiment_engine = ExperimentEngine()

# Pydantic models
class ExperimentCreateRequest(BaseModel):
    shop: str
    platform: str  # etsy/suzuri/pinterest/x
    change_type: str  # title/description/tags/price/image
    before: Dict[str, Any]
    after: Dict[str, Any]
    date: Optional[str] = None

class ExperimentResultRequest(BaseModel):
    experiment_id: str
    metric: str  # views/sales/clicks/followers
    before_value: float
    after_value: float
    measurement_date: Optional[str] = None

@app.post("/api/experiment/create")
async def create_experiment(request: ExperimentCreateRequest):
    """実験作成エンドポイント"""
    try:
        platform = Platform(request.platform)
        change_type = ChangeType(request.change_type)

        experiment_id = experiment_engine.create_experiment(
            shop=request.shop,
            platform=platform,
            change_type=change_type,
            before=request.before,
            after=request.after,
            date=request.date
        )

        return {
            "experiment_id": experiment_id,
            "recorded": True,
            "message": f"実験が記録されました (Shop: {request.shop})"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")

@app.post("/api/experiment/result")
async def record_result(request: ExperimentResultRequest):
    """実験結果記録エンドポイント"""
    try:
        metric = Metric(request.metric)

        result = experiment_engine.record_result(
            experiment_id=request.experiment_id,
            metric=metric,
            before_value=request.before_value,
            after_value=request.after_value,
            measurement_date=request.measurement_date
        )

        return {
            "improvement": request.after_value - request.before_value,
            "improvement_percent": result["improvement_percent"],
            "verdict": result["verdict"],
            "recommendation": f"{request.metric}で{result['improvement_percent']:.1f}%の変化でした"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")

@app.get("/api/experiment/history")
async def get_history(shop: Optional[str] = None, platform: Optional[str] = None):
    """実験履歴取得エンドポイント"""
    try:
        history = experiment_engine.get_experiment_history(shop=shop, platform=platform)
        return {"experiments": history, "total_count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エラー: {str(e)}")

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Creator Experiment Log API",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)