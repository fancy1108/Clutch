"""IUE (Interaction Understanding Engine) — 数据模型

定义交互理解引擎 6 阶段管道的输入输出类型：
  Stage 1: ElementCandidate  — 可交互元素候选
  Stage 2: ElementRole        — 元素意图角色分类
  Stage 3: TargetMatch        — 候选目标页面匹配
  Stage 4-5: FlowSuggestion    — 带置信度与推理的完整跳转建议
  Stage 6: ApprovalStatus      — 人工确认门状态
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class ElementRole(str, Enum):
    """可交互元素的语义角色分类（Stage 2 输出）。"""
    SUBMIT_BUTTON = "SubmitButton"
    CANCEL_BUTTON = "CancelButton"
    DELETE_BUTTON = "DeleteButton"
    NAV_LINK = "NavLink"
    TABLE_ROW_LINK = "TableRowLink"
    PAGINATION_NEXT = "PaginationNext"
    PAGINATION_PREV = "PaginationPrev"
    TAB_SWITCH = "TabSwitch"
    MENU_ITEM = "MenuItem"
    ACTION_BUTTON = "ActionButton"
    CREATE_BUTTON = "CreateButton"
    EDIT_BUTTON = "EditButton"
    SEARCH_BUTTON = "SearchButton"
    FILTER_BUTTON = "FilterButton"
    ICON_BUTTON = "IconButton"
    UNKNOWN = "Unknown"


class ApprovalStatus(str, Enum):
    """Stage 6 人工确认门状态。"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class ElementCandidate:
    """Stage 1 输出：已识别的可交互元素候选。

    输入为脱水降噪后的 DOM 树（已过滤冗余包裹容器、
    已将内联 <svg> 替换为 [ICON_SVG] 占位符）。
    """
    board_id: str
    element_index: int
    tag: str  # 'button', 'a', 'input', 'select', 'textarea', 'tr', 'li', etc.
    text: str
    attributes: Dict[str, str] = field(default_factory=dict)
    # Stage 2 填充
    role: ElementRole = ElementRole.UNKNOWN
    role_confidence: float = 0.0


@dataclass
class TargetMatch:
    """Stage 3 输出：候选目标画板匹配结果。"""
    source_board_id: str
    target_board_id: str
    match_method: str  # 'button_text_exact' | 'button_text_partial' | 'keyword_overlap' | 'action_heuristic' | 'title_substring'
    overlap_tokens: List[str] = field(default_factory=list)
    # Stage 4 填充
    confidence: float = 0.0
    # Stage 5 填充
    reasoning: str = ""


@dataclass
class FlowSuggestion:
    """Stage 4-5 输出：完整跳转建议，含置信度与中文推理。

    此结构可序列化为 Interaction Contract 中的 TriggerInteraction。
    """
    source_board_id: str
    target_board_id: str
    source_element_text: str = ""
    source_element_role: ElementRole = ElementRole.UNKNOWN
    trigger: str = "click"
    confidence: float = 0.0
    reasoning: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    # Stage 6 填充
    status: ApprovalStatus = ApprovalStatus.PENDING
