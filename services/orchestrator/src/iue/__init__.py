"""IUE — Interaction Understanding Engine（交互理解引擎）

6 阶段可插拔管道，从静态 HTML 页面自动推断跳转关系，
输出带置信度与中文推理的结构化 FlowSuggestion。

Usage:
    from iue import InteractionUnderstandingEngine
    engine = InteractionUnderstandingEngine()
    suggestions = engine.analyze(boards)
"""

from .engine import InteractionUnderstandingEngine
from .models import (
    ApprovalStatus,
    ElementCandidate,
    ElementRole,
    FlowSuggestion,
    TargetMatch,
)

__all__ = [
    "InteractionUnderstandingEngine",
    "ElementCandidate",
    "ElementRole",
    "TargetMatch",
    "FlowSuggestion",
    "ApprovalStatus",
]
