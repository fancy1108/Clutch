"""IUE (Interaction Understanding Engine) — 6 阶段管道引擎

模块化、可插拔的交互理解引擎，将静态 HTML 页面之间的跳转关系
从"启发式猜测"升级为"结构化推理管道"。

Stage 1: 识别点击元素 — 提取所有潜在可交互节点
Stage 2: 识别元素意图 — 语义角色分类（SubmitButton, NavLink…）
Stage 3: 寻找候选目标 — 跨画板匹配潜在跳转目标
Stage 4: 拓扑概率打分 — 0.0~1.0 置信度排序
Stage 5: 输出推理理由 — 生成中文可读解释
Stage 6: 等待人工确认 — 标记审批状态，阻断代码生成

设计原则（见 PRD §1.5）：
  - 各阶段 handler 可插拔替换，不修改核心协议
  - 默认使用规则+启发式，可替换为 LLM / 向量 / 视觉模型
  - FlowSuggestion 可直接序列化为 Interaction Contract 的 TriggerInteraction
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from .models import (
    ApprovalStatus,
    ElementCandidate,
    ElementRole,
    FlowSuggestion,
    TargetMatch,
)

# ---- Stage handler type signatures (pluggable) ----

Stage1Handler = Callable[[List[Dict[str, Any]]], List[ElementCandidate]]
Stage2Handler = Callable[[List[ElementCandidate]], List[ElementCandidate]]
Stage3Handler = Callable[
    [List[ElementCandidate], List[Dict[str, Any]]], List[TargetMatch]
]
Stage4Handler = Callable[[List[TargetMatch]], List[TargetMatch]]
Stage5Handler = Callable[[List[TargetMatch]], List[FlowSuggestion]]


# ================================================================
# Default Stage Implementations (rule-based heuristics)
# ================================================================


def _normalize_words(s: str) -> List[str]:
    """提取英文单词/数字和中文单字 token，统一小写并去复数。"""
    words: List[str] = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", (s or ""))
    result: List[str] = []
    for w in words:
        wl = w.lower()
        result.append(wl)
        if wl.endswith("s") and len(wl) > 3:
            result.append(wl[:-1])
    return result


# ---------- Stage 1: 识别点击元素 ----------

def default_stage1_candidates(boards: List[Dict[str, Any]]) -> List[ElementCandidate]:
    """从 board 列表中提取所有可交互元素。

    识别标准：
      - type == 'button' | 'a' | 'input' | 'select' | 'textarea'
      - type == 'row' | 'tr'（表格行链接）
      - type == 'tab' | 'menu-item'
      - element text 非空
    """
    candidates: List[ElementCandidate] = []
    interactive_tags = {"button", "a", "input", "select", "textarea", "row", "tr", "tab", "menu-item", "li"}
    for board in boards:
        bid = board.get("id", "")
        for idx, el in enumerate(board.get("elements", [])):
            tag = str(el.get("type", "")).lower()
            text = str(el.get("text", "")).strip()
            if not text or tag not in interactive_tags:
                continue
            candidates.append(ElementCandidate(
                board_id=bid,
                element_index=idx,
                tag=tag,
                text=text,
                attributes=el.get("attributes", {}),
            ))
    return candidates


# ---------- Stage 2: 识别元素意图 ----------

# 角色分类规则：(中文关键词, 英文关键词, 标签白名单) → ElementRole
_ROLE_RULES: List[Tuple[List[str], List[str], List[str], ElementRole]] = [
    (["提交", "保存", "确认", "确定", "登录", "注册", "发布"],
     ["submit", "save", "confirm", "ok", "login", "signup", "publish", "apply", "done"],
     ["button", "input"], ElementRole.SUBMIT_BUTTON),
    (["取消", "关闭", "返回", "退出", "放弃"],
     ["cancel", "close", "back", "exit", "discard", "dismiss", "abort"],
     ["button", "a"], ElementRole.CANCEL_BUTTON),
    (["删除", "移除", "清空"],
     ["delete", "remove", "clear", "trash", "destroy"],
     ["button", "a"], ElementRole.DELETE_BUTTON),
    (["新建", "添加", "创建", "新增", "加入"],
     ["create", "new", "add", "insert"],
     ["button", "a"], ElementRole.CREATE_BUTTON),
    (["编辑", "修改", "更新", "变更"],
     ["edit", "modify", "update", "change", "rename"],
     ["button", "a"], ElementRole.EDIT_BUTTON),
    (["搜索", "查找", "查询", "检索"],
     ["search", "find", "query", "lookup"],
     ["button", "input"], ElementRole.SEARCH_BUTTON),
    (["筛选", "过滤", "排序"],
     ["filter", "sort", "order"],
     ["button", "select"], ElementRole.FILTER_BUTTON),
    (["下一页", "下一頁", "后一页", "›", "→"],
     ["next", "forward", ">", "›", "»"],
     ["button", "a"], ElementRole.PAGINATION_NEXT),
    (["上一页", "上一頁", "前一页", "‹", "←"],
     ["prev", "previous", "back", "<", "‹", "«"],
     ["button", "a"], ElementRole.PAGINATION_PREV),
    (["首页", "仪表盘", "概览", "工作台"],
     ["home", "dashboard", "overview", "index"],
     ["a", "menu-item"], ElementRole.NAV_LINK),
    (["详情", "查看", "明细", "展开"],
     ["detail", "view", "open", "expand", "inspect", "show"],
     ["button", "a", "tr", "row"], ElementRole.TABLE_ROW_LINK),
    (["tab", "标签页"],
     ["tab", "pane"],
     ["tab", "button", "a"], ElementRole.TAB_SWITCH),
]


def default_stage2_classify(candidates: List[ElementCandidate]) -> List[ElementCandidate]:
    """基于关键词规则对元素进行语义角色分类。

    匹配策略（优先级降序）：
      1. 精确匹配中文关键词
      2. 精确匹配英文关键词（button text 完全相等）
      3. 子串包含匹配（中文 + 英文）
      4. 标签推断（row/tr → TableRowLink，a → NavLink，input → SearchButton）
    """
    for c in candidates:
        text = c.text.strip()
        text_lower = text.lower()
        best_role = ElementRole.UNKNOWN
        best_confidence = 0.0

        for cn_keywords, en_keywords, allowed_tags, role in _ROLE_RULES:
            if c.tag not in allowed_tags:
                continue
            # 精确匹配
            if text in cn_keywords or text_lower in en_keywords:
                if 0.95 > best_confidence:
                    best_role, best_confidence = role, 0.95
                break  # 精确匹配命中即跳出
            # 子串包含
            if any(kw in text for kw in cn_keywords) or any(kw in text_lower for kw in en_keywords):
                if 0.75 > best_confidence:
                    best_role, best_confidence = role, 0.75
            # 中文单字级包含
            if any(kw in text for kw in cn_keywords if len(kw) == 1):
                if 0.55 > best_confidence:
                    best_role, best_confidence = role, 0.55

        # 标签推断兜底
        if best_role == ElementRole.UNKNOWN:
            if c.tag in ("tr", "row") and len(text) > 1:
                best_role, best_confidence = ElementRole.TABLE_ROW_LINK, 0.4
            elif c.tag == "a" and len(text) > 1:
                best_role, best_confidence = ElementRole.NAV_LINK, 0.3
            elif c.tag in ("button",) and len(text) > 1:
                best_role, best_confidence = ElementRole.ACTION_BUTTON, 0.2

        c.role = best_role
        c.role_confidence = best_confidence

    return candidates


# ---------- Stage 3: 寻找候选目标 ----------

def default_stage3_match(
    candidates: List[ElementCandidate], boards: List[Dict[str, Any]]
) -> List[TargetMatch]:
    """为每个候选元素匹配潜在目标画板。

    匹配方法（优先级降序）：
      1. button_text_exact: 按钮文字与目标标题完全相同
      2. button_text_partial: 按钮文字与目标标题互相子串包含
      3. keyword_overlap: 按钮文字词元与目标标题词元存在交集
      4. title_substring: 目标标题出现在源 board 文字中
      5. action_heuristic: 动词-名词启发式关联
    """
    board_index = {b["id"]: b for b in boards}
    matches: List[TargetMatch] = []

    # 按 board_id 分组 candidates
    candidates_by_board: Dict[str, List[ElementCandidate]] = {}
    for c in candidates:
        candidates_by_board.setdefault(c.board_id, []).append(c)

    for src_bid, src_candidates in candidates_by_board.items():
        src_board = board_index.get(src_bid, {})
        src_board_text = " ".join(
            [src_board.get("title", "")] +
            [el.get("text", "") for el in src_board.get("elements", [])]
        )
        src_words = set(_normalize_words(src_board_text))

        for tgt_board in boards:
            tgt_bid = tgt_board.get("id", "")
            if src_bid == tgt_bid:
                continue
            tgt_title = tgt_board.get("title", "") or ""
            tgt_words = set(_normalize_words(tgt_title))

            for candidate in src_candidates:
                btn_text = candidate.text
                btn_lower = btn_text.lower()
                tgt_lower = tgt_title.lower()

                # 方法 1: 完全相同
                if btn_lower == tgt_lower:
                    matches.append(TargetMatch(
                        source_board_id=src_bid,
                        target_board_id=tgt_bid,
                        match_method="button_text_exact",
                    ))
                    continue

                # 方法 2: 互相包含
                if btn_lower and tgt_lower and (
                    btn_lower in tgt_lower or tgt_lower in btn_lower
                ):
                    matches.append(TargetMatch(
                        source_board_id=src_bid,
                        target_board_id=tgt_bid,
                        match_method="button_text_partial",
                        overlap_tokens=[btn_lower],
                    ))
                    continue

                # 方法 3: 关键词重叠
                btn_words = set(_normalize_words(btn_text))
                common = btn_words & tgt_words
                if common and len(common) >= 1:
                    matches.append(TargetMatch(
                        source_board_id=src_bid,
                        target_board_id=tgt_bid,
                        match_method="keyword_overlap",
                        overlap_tokens=sorted(common),
                    ))
                    continue

                # 方法 4: 标题子串
                if tgt_lower and tgt_lower in src_board_text.lower():
                    matches.append(TargetMatch(
                        source_board_id=src_bid,
                        target_board_id=tgt_bid,
                        match_method="title_substring",
                    ))
                    continue

                # 方法 5: 动作启发式
                action_verbs = {"create", "new", "add", "edit", "view",
                                "open", "detail", "configure", "manage", "setting"}
                btn_verb_set = set(_normalize_words(btn_text))
                target_noun_set = tgt_words
                if btn_verb_set & action_verbs and any(
                    any(w in tgt_lower for w in ("create", "new", "edit", "setting", "config", "manage"))
                    for _ in [1]
                ):
                    matches.append(TargetMatch(
                        source_board_id=src_bid,
                        target_board_id=tgt_bid,
                        match_method="action_heuristic",
                    ))

    return matches


# ---------- Stage 4: 拓扑概率打分 ----------

_SCORE_MAP: Dict[str, float] = {
    "button_text_exact": 0.92,
    "button_text_partial": 0.78,
    "keyword_overlap": 0.65,
    "title_substring": 0.55,
    "action_heuristic": 0.40,
}


def default_stage4_score(matches: List[TargetMatch]) -> List[TargetMatch]:
    """为每个匹配计算 0.0~1.0 置信度。

    基础分数按匹配方法映射，额外加成：
      - 关键词重叠数 ≥2: +0.10
      - keyword_overlap + ≥3 重叠: +0.15
    """
    for m in matches:
        base = _SCORE_MAP.get(m.match_method, 0.30)
        if m.match_method == "keyword_overlap":
            n = len(m.overlap_tokens)
            if n >= 3:
                base += 0.15
            elif n >= 2:
                base += 0.10
        m.confidence = min(base, 1.0)
    # 按置信度降序
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches


# ---------- Stage 5: 输出推理理由 ----------

_REASON_TEMPLATES: Dict[str, str] = {
    "button_text_exact": "按钮'{btn}'与目标页面'{tgt}'标题完全一致，推断为直接跳转",
    "button_text_partial": "按钮'{btn}'文字包含目标页面'{tgt}'标题关键词，推断为关联跳转",
    "keyword_overlap": "按钮'{btn}'与页面'{tgt}'共享关键词{overlap}，推断为语义关联跳转",
    "title_substring": "页面'{tgt}'标题出现在源页面文本中，推断为上下文跳转",
    "action_heuristic": "按钮'{btn}'为操作类按钮，推断可能跳转至'{tgt}'页面",
}


def default_stage5_reason(
    matches: List[TargetMatch],
    boards: List[Dict[str, Any]],
    candidates: List[ElementCandidate],
) -> List[FlowSuggestion]:
    """生成中文推理理由并构建 FlowSuggestion 列表。"""
    board_index: Dict[str, Dict[str, Any]] = {b["id"]: b for b in boards}
    # 构建 (board_id, element_index) → candidate 查询索引
    candidate_index: Dict[Tuple[str, int], ElementCandidate] = {}
    for c in candidates:
        candidate_index[(c.board_id, c.element_index)] = c

    suggestions: List[FlowSuggestion] = []
    for m in matches:
        tgt_title = board_index.get(m.target_board_id, {}).get("title", m.target_board_id)
        btn_text = ""
        role = ElementRole.UNKNOWN

        # 通过 overlap_tokens 反查源 candidate
        src_cands = [c for c in candidates if c.board_id == m.source_board_id]
        # 找到与 target 标题最匹配的 candidate
        best_cand = None
        for c in src_cands:
            if c.text.lower() in tgt_title.lower() or tgt_title.lower() in c.text.lower():
                best_cand = c
                break
        if best_cand is None and src_cands:
            # fallback: 取第一个按钮元素
            best_cand = next((c for c in src_cands if c.tag == "button"), src_cands[0])

        if best_cand:
            btn_text = best_cand.text
            role = best_cand.role

        overlap_str = ", ".join(m.overlap_tokens[:3]) if m.overlap_tokens else "—"
        template = _REASON_TEMPLATES.get(m.match_method, "推断'{btn}'可能跳转至'{tgt}'")
        reasoning = template.format(btn=btn_text or "—", tgt=tgt_title, overlap=overlap_str)

        suggestions.append(FlowSuggestion(
            source_board_id=m.source_board_id,
            target_board_id=m.target_board_id,
            source_element_text=btn_text,
            source_element_role=role,
            trigger="click",
            confidence=m.confidence,
            reasoning=reasoning,
            params={},
            status=ApprovalStatus.PENDING,
        ))

    return suggestions


# ================================================================
# Engine Orchestrator
# ================================================================


class InteractionUnderstandingEngine:
    """交互理解引擎（IUE）—— 6 阶段管道编排器。

    支持插拔式替换每个阶段的 handler，允许未来引入
    向量检索、视觉模型、图算法或智能体等推断源。

    Usage:
        engine = InteractionUnderstandingEngine()
        # 可选：替换某一 stage handler
        engine.stage4_score = my_custom_scorer
        suggestions = engine.analyze(boards)
    """

    def __init__(
        self,
        stage1: Stage1Handler | None = None,
        stage2: Stage2Handler | None = None,
        stage3: Stage3Handler | None = None,
        stage4: Stage4Handler | None = None,
        stage5: Stage5Handler | None = None,
    ):
        self.stage1 = stage1 or default_stage1_candidates
        self.stage2 = stage2 or default_stage2_classify
        self.stage3 = stage3 or default_stage3_match
        self.stage4 = stage4 or default_stage4_score
        self.stage5 = stage5 or default_stage5_reason

    def analyze(self, boards: List[Dict[str, Any]]) -> List[FlowSuggestion]:
        """执行完整 6 阶段管道（Stage 1-5 自动；Stage 6 需外部确认）。

        Args:
            boards: 画板列表，每个 board 含 id, title, elements

        Returns:
            带置信度与中文推理的 FlowSuggestion 列表
        """
        # Stage 1: 识别可交互元素
        candidates = self.stage1(boards)
        if not candidates:
            return []

        # Stage 2: 元素意图分类
        candidates = self.stage2(candidates)

        # Stage 3: 寻找候选目标
        matches = self.stage3(candidates, boards)
        if not matches:
            return []

        # Stage 4: 拓扑概率打分
        matches = self.stage4(matches)

        # Stage 5: 输出推理理由
        suggestions = self.stage5(matches, boards, candidates)

        return suggestions

    def analyze_to_dicts(self, boards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """同 analyze()，但返回可 JSON 序列化的 dict 列表。"""
        suggestions = self.analyze(boards)
        return [
            {
                "from": s.source_board_id,
                "to": s.target_board_id,
                "trigger": s.trigger,
                "confidence": s.confidence,
                "reason": s.reasoning,
                "source_element_text": s.source_element_text,
                "source_element_role": s.source_element_role.value,
                "params": s.params,
                "status": s.status.value,
            }
            for s in suggestions
        ]
