"""
agent_cluster — 多 Agent 协作模块

负责多个专业 Agent 之间的任务分发、协调与结果聚合。
支持 Agent 注册、任务路由和并行执行。

对外暴露的核心接口：
    - Orchestrator    (class): Agent 编排器，负责任务分发与结果聚合
"""

from agent_cluster.orchestrator import Orchestrator

__all__ = [
    "Orchestrator",
]
