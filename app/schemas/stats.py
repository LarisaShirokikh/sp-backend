# app/schemas/stats.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class StatsResponse(BaseModel):
    """Dashboard statistics response model"""
    activeGroupBuys: int = Field(..., description="Number of active group buys")
    totalParticipants: int = Field(..., description="Total number of participants across all group buys")
    totalAmount: float = Field(..., description="Total amount collected across all group buys")
    completedGroupBuys: int = Field(..., description="Number of completed group buys")
    lastMonthGrowth: float = Field(..., description="Percentage growth in the last month")


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: str = Field(..., description="Unique notification ID")
    message: str = Field(..., description="Notification message text")
    type: str = Field(..., description="Notification type (info, warning, success, error)")
    date: str = Field(..., description="Notification date (DD.MM.YYYY format)")