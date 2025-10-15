from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User, AIStrategy
from app.api.v1.endpoints.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class StrategyCreate(BaseModel):
    name: str
    llm_model: str = "claude-3-opus"
    description: str = None

class StrategyResponse(BaseModel):
    id: str
    name: str
    llm_model: str
    description: str = None
    strategy_config: dict = {}
    performance_metrics: dict = {}
    status: str
    created_at: str
    updated_at: str = None

@router.get("", response_model=List[StrategyResponse])
async def list_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """List user's strategies"""
    strategies = db.query(AIStrategy).filter(
        AIStrategy.user_id == current_user.id
    ).order_by(AIStrategy.created_at.desc()).all()
    
    return [
        StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            llm_model=strategy.llm_model or "claude-3-opus",
            description=strategy.description,
            strategy_config=eval(strategy.strategy_config) if strategy.strategy_config else {},
            performance_metrics=eval(strategy.performance_metrics) if strategy.performance_metrics else {},
            status=strategy.status,
            created_at=strategy.created_at.isoformat(),
            updated_at=strategy.updated_at.isoformat() if strategy.updated_at else None
        )
        for strategy in strategies
    ]

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get strategy details"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        llm_model=strategy.llm_model or "claude-3-opus",
        description=strategy.description,
        strategy_config=eval(strategy.strategy_config) if strategy.strategy_config else {},
        performance_metrics=eval(strategy.performance_metrics) if strategy.performance_metrics else {},
        status=strategy.status,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat() if strategy.updated_at else None
    )

@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update strategy"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    strategy.name = strategy_data.name
    strategy.llm_model = strategy_data.llm_model
    strategy.description = strategy_data.description
    
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        llm_model=strategy.llm_model or "claude-3-opus",
        description=strategy.description,
        strategy_config=eval(strategy.strategy_config) if strategy.strategy_config else {},
        performance_metrics=eval(strategy.performance_metrics) if strategy.performance_metrics else {},
        status=strategy.status,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat() if strategy.updated_at else None
    )

@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete strategy"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Soft delete by setting status to inactive
    strategy.status = 'deleted'
    db.commit()
    
    return {"message": "Strategy deleted successfully"}

@router.post("/{strategy_id}/activate")
async def activate_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Activate strategy"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    strategy.status = 'active'
    db.commit()
    
    return {"message": "Strategy activated successfully"}

@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Deactivate strategy"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    strategy.status = 'inactive'
    db.commit()
    
    return {"message": "Strategy deactivated successfully"}
