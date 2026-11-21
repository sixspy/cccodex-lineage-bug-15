# cc-lineage-lab

CC_Codex 二期（26.11）**数据工程**产品线：**表血缘影响台**（Bottle + Waitress + 原生 JS SPA + SQLite）。

## 一句话骨架

**血缘节点 → 边关系 → 影响分析作业 → 下游通知 → 覆盖对账**

与压实/回灌/契约线正交；不碰外仓常见指纹。

## 领域

- **所属领域**：数据工程
- **子方向偏分析**：表血缘登记、影响分析、下游通知、覆盖核对

## 页面（≥5）

1. 节点目录 2. 边关系 3. 影响分析 4. 下游通知 5. 覆盖对账 6. 台参数

## 本地

http://127.0.0.1:7400/login · **admin / 123456** · 端口 **7400**

```powershell
python -m venv .venv
.\\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
python run.py
```

## 预留切口（未做）

影响作业半失败闭、通知去重锁、边变更与覆盖快照二选一命运、并发争抢写锁等，出题可切。
