from abc import ABC, abstractmethod
from typing import Any

from app.models import HazardType, Severity


class RiskScorer(ABC):
    @abstractmethod
    def score(self, hazard_type: HazardType, payload: dict[str, Any]) -> Severity:
        raise NotImplementedError


class RuleBasedRiskScorer(RiskScorer):
    def score(self, hazard_type: HazardType, payload: dict[str, Any]) -> Severity:
        if hazard_type == HazardType.flood:
            value = float(payload.get("water_level", payload.get("level", payload.get("rainfall_mm", 0))) or 0)
            danger = float(payload.get("danger_level", 999999) or 999999)
            if value >= danger:
                return Severity.high
            if value >= danger * 0.85 or value >= 115.6:
                return Severity.watch
            return Severity.low
        if hazard_type == HazardType.fire:
            confidence = str(payload.get("confidence", "")).lower()
            frp = float(payload.get("frp", 0) or 0)
            return Severity.high if confidence in {"high", "h"} or frp >= 50 else Severity.watch
        if hazard_type == HazardType.air_pollution:
            aqi = float(payload.get("aqi", payload.get("AQI", 0)) or 0)
            return Severity.high if aqi >= 300 else Severity.watch if aqi >= 200 else Severity.low
        if hazard_type == HazardType.water_pollution:
            contamination = float(payload.get("contamination_index", payload.get("pollution_index", 0)) or 0)
            return Severity.high if contamination >= 80 else Severity.watch if contamination >= 50 else Severity.low
        return Severity.low


scorer: RiskScorer = RuleBasedRiskScorer()
