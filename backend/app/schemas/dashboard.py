from typing import Optional
from typing import List
from pydantic import BaseModel, Field


class StatCardItem(BaseModel):
    id: str
    label: str
    value: str
    change: str
    icon: str
    tint: str


class LeadsChartPoint(BaseModel):
    date: str
    leads: int


class SourceDonutItem(BaseModel):
    name: str
    value: int
    color: str


class RecentLeadItem(BaseModel):
    id: int
    name: str
    contact: str
    location: str
    propertyType: str
    source: str
    status: str
    createdAt: str


class RecentActivityItem(BaseModel):
    id: int
    title: str
    subtitle: str
    time: str
    icon: str
    tint: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    status: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    statCards: List[StatCardItem] = Field(default_factory=list)
    leadsOverview: List[LeadsChartPoint] = Field(default_factory=list)
    leadsBySource: List[SourceDonutItem] = Field(default_factory=list)
    recentLeads: List[RecentLeadItem] = Field(default_factory=list)
    recentActivity: List[RecentActivityItem] = Field(default_factory=list)
    metrics: Optional[dict] = Field(default_factory=dict)
