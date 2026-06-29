# Archive Notice

This directory holds read-only archived memory files.

Do not append session or deliverable records to files in this directory.
When rotating, create a **new** archive file — never append to existing ones.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Updated on: 2026-06-29
Reason: archive index (edit only when adding new rotated files)

---

# memory/archive/

> 冷数据归档。活跃接力见 [`../PROGRESS.md`](../PROGRESS.md) · 交付索引见 [`../DELIVERABLES.md`](../DELIVERABLES.md)。  
> 生命周期规则：[`docs/document-governance.md`](../../docs/document-governance.md) §文档生命周期。

| 文件 | 内容 |
|------|------|
| `PROGRESS-2026-Q2.md` | 2026 Q2 会话日记（轮转前 54→10 会话） |
| `DELIVERABLES-M0.md` | M0 基座 Task 交付索引 |
| `DELIVERABLES-M1.md` | M1 引擎 Task 交付索引 |
| `DELIVERABLES-M2-M4-P2.md` | M2–M4、P2、D11/D12 等交付索引 |
| `DELIVERABLES-M3.md` | M3 工具链相关交付（M3-F 等） |
| `DELIVERABLES-POST-MVP.md` | D25 后迭代、UI 抛光、B-03 compaction 等 |
| `DELIVERABLES-HRT.md` | D25 Hybrid Runtime HRT-00~10 |
| `DELIVERABLES-OSR.md` | OSR T0–T1 及早期 T2 交付索引 |

**轮转：** 2026-06-29 首次执行文档生命周期治理。

## 新建归档文件时（复制到文件顶部）

```markdown
# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: YYYY-MM-DD
Reason: milestone completed / quarterly rotation

---
```
