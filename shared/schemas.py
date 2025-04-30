from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class RectangleRequest(BaseModel):
    """Request model for rectangle calculations."""
    length: float = Field(..., description="The length of the rectangle")
    width: float = Field(..., description="The width of the rectangle")

class AreaResponse(BaseModel):
    """Response model for area calculations."""
    area: float = Field(..., description="The calculated area")
    unit: str = Field(default="square units", description="The unit of measurement")
    result: Optional[str] = Field(None, description="Formatted result text from the agent")
    raw_response: Optional[str] = Field(None, description="Raw response from the agent")

class PerimeterResponse(BaseModel):
    """Response model for perimeter calculations."""
    perimeter: float = Field(..., description="The calculated perimeter")
    unit: str = Field(default="units", description="The unit of measurement")
    result: Optional[str] = Field(None, description="Formatted result text from the agent")
    raw_response: Optional[str] = Field(None, description="Raw response from the agent")

class GeometryRequest(BaseModel):
    """Request model for combined geometry calculations."""
    length: float = Field(..., description="The length of the rectangle")
    width: float = Field(..., description="The width of the rectangle")
    calculate_area: bool = Field(default=True, description="Whether to calculate area")
    calculate_perimeter: bool = Field(default=True, description="Whether to calculate perimeter")

class GeometryResponse(BaseModel):
    """Response model for combined geometry calculations."""
    area: Optional[float] = Field(None, description="The calculated area (if requested)")
    perimeter: Optional[float] = Field(None, description="The calculated perimeter (if requested)")
    area_unit: Optional[str] = Field(None, description="The unit for area measurement")
    perimeter_unit: Optional[str] = Field(None, description="The unit for perimeter measurement")
    result: Optional[str] = Field(None, description="Formatted result text from the agent")
    raw_response: Optional[str] = Field(None, description="Raw response from the agent") 