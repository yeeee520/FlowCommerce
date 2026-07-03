"""
agent_cluster.orchestrator — Agent 编排器

管理多个专业 Agent 的生命周期，负责任务路由、
并行执行、结果聚合与冲突消解。
"""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Agent 编排器

    职责：
    - 注册和管理多个专业 Agent（商品、订单、售后等）
    - 根据用户意图路由到对应 Agent
    - 协调多 Agent 并行执行并聚合结果
    - 处理 Agent 间的冲突和依赖

    接口契约：
        register_agent(
            name: str,
            handler: Callable[..., Any],
            intent_tags: list[str],
        ) -> None
            - 注册一个专业 Agent

        async dispatch(
            intent: str,
            payload: dict[str, Any],
        ) -> dict[str, Any]
            - 参数: intent — 意图标签
            - 参数: payload — 任务负载
            - 返回: Agent 执行结果

        async dispatch_parallel(
            tasks: list[dict[str, Any]],
        ) -> list[dict[str, Any]]
            - 参数: tasks — 任务列表 [{"intent": str, "payload": dict}, ...]
            - 返回: 各任务结果列表，顺序与输入一致
    """

    # 中文意图到英文标签的映射（用于与 customer_service agent 匹配）
    _INTENT_ALIAS_MAP: dict[str, str] = {
        "商品咨询": "product_inquiry",
        "订单查询": "order_status",
        "售后问题": "after_sales",
        "物流查询": "logistics",
        "通用问答": "general",
    }

    def __init__(self) -> None:
        self._agents: dict[str, Callable[..., Any]] = {}
        """agent_name -> handler 映射"""
        self._intent_map: dict[str, str] = {}
        """intent_tag -> agent_name 映射"""

    def register_agent(
        self,
        name: str,
        handler: Callable[..., Any],
        intent_tags: list[str],
    ) -> None:
        """
        注册专业 Agent

        Args:
            name: Agent 名称（唯一标识）
            handler: 处理函数，签名为 async def handler(payload: dict) -> dict
            intent_tags: 该 Agent 能处理的意图标签列表
        """
        self._agents[name] = handler
        for tag in intent_tags:
            self._intent_map[tag] = name
        logger.info(f"注册 Agent: '{name}', 处理意图: {intent_tags}")

    async def dispatch(
        self,
        intent: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        根据意图分发任务到对应 Agent

        支持中文意图标签自动映射到英文别名。

        Args:
            intent: 意图标签
            payload: 任务数据

        Returns:
            Agent 执行结果

        Raises:
            ValueError: 没有注册能处理该意图的 Agent
        """
        # 尝试映射别名
        resolved_intent = self._INTENT_ALIAS_MAP.get(intent, intent)
        agent_name = self._intent_map.get(resolved_intent)

        if agent_name is None:
            # 尝试用通用 agent 兜底
            agent_name = self._intent_map.get("general")
            if agent_name is None:
                error_msg = f"没有注册能处理意图 '{intent}' 的 Agent"
                logger.error(error_msg)
                return {"error": error_msg, "intent": intent}

        handler = self._agents.get(agent_name)
        if handler is None:
            error_msg = f"Agent '{agent_name}' 已注册但 handler 不存在"
            logger.error(error_msg)
            return {"error": error_msg, "intent": intent}

        logger.info(f"分发任务: intent={intent} -> agent={agent_name}")
        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(payload)
            else:
                result = handler(payload)
            return {"agent": agent_name, "intent": intent, "result": result}
        except Exception as exc:
            logger.error(f"Agent '{agent_name}' 执行失败: {exc}")
            return {"agent": agent_name, "intent": intent, "error": str(exc)}

    async def dispatch_parallel(
        self,
        tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        并行执行多个任务

        使用 asyncio.gather 并行调度，保持输入顺序。

        Args:
            tasks: 任务列表 [{"intent": str, "payload": dict}, ...]

        Returns:
            各任务结果列表，顺序与输入一致
        """
        if not tasks:
            return []

        logger.info(f"并行调度 {len(tasks)} 个任务")

        async def _run_one(task: dict[str, Any]) -> dict[str, Any]:
            intent = task.get("intent", "general")
            payload = task.get("payload", {})
            return await self.dispatch(intent, payload)

        coroutines = [_run_one(t) for t in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 将异常转换为错误结果
        processed: list[dict[str, Any]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "error": str(result),
                    "intent": tasks[i].get("intent", "unknown"),
                })
            else:
                processed.append(result)

        return processed
