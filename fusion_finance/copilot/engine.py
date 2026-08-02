from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from ..ai_client import MLXClient
from ..utils.parse_json import parse_json
from .memory import ConversationMemory
from .tools import ToolRegistry

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3


class CopilotEngine:
    def __init__(self, mlx: MLXClient | None = None, registry: ToolRegistry | None = None):
        self.mlx = mlx or MLXClient()
        self.registry = registry or ToolRegistry()
        self.memory = ConversationMemory()

    def _build_system_prompt(self) -> str:
        return (
            "你是Fusion-Finance AI助手，专业的金融分析Copilot。\n"
            "你可以帮助用户进行估值建模、风险分析、财务报表分析等任务。\n\n"
            + self.registry.format_prompt()
        )

    async def chat(self, message: str, session_id: str = "default", history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        self.memory.add_message(session_id, "user", message)

        messages = history or self.memory.get_messages(session_id, limit=20)
        messages = [m for m in messages if m.get("role") in ("user", "assistant")]
        messages.append({"role": "user", "content": message})

        all_messages = [{"role": "system", "content": self._build_system_prompt()}] + messages
        tool_calls_log = []
        rounds = 0
        response = ""

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.mlx.chat(all_messages, temperature=0.1)
            tool_data = parse_json(response)

            if tool_data and "tool" in tool_data:
                rounds += 1
                tool_name = tool_data["tool"]
                tool_args = tool_data.get("args", {})
                logger.info("Copilot tool call: %s, args=%s", tool_name, tool_args)

                tool_result = await self.registry.execute(tool_name, tool_args)
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result_summary": json.dumps(tool_result, ensure_ascii=False, default=str)[:200],
                })

                all_messages.append({"role": "assistant", "content": response})
                all_messages.append({
                    "role": "user",
                    "content": f"工具 {tool_name} 执行结果:\n```json\n{json.dumps(tool_result, ensure_ascii=False, default=str)}\n```\n请根据结果继续分析或给出最终回复。",
                })
            else:
                break

        if tool_calls_log:
            final_response = await self.mlx.chat(all_messages, temperature=0.1)
        else:
            final_response = response

        self.memory.add_message(session_id, "assistant", final_response)

        return {
            "reply": final_response,
            "tool_calls": tool_calls_log,
            "rounds": rounds,
            "session_id": session_id,
        }

    async def chat_stream(self, message: str, session_id: str = "default") -> AsyncIterator[str]:
        self.memory.add_message(session_id, "user", message)
        messages = self.memory.get_messages(session_id, limit=20)
        all_messages = [{"role": "system", "content": self._build_system_prompt()}] + messages

        collected = []
        async for chunk in self.mlx.chat_stream(all_messages, temperature=0.1):
            collected.append(chunk)
            yield chunk

        full_response = "".join(collected)
        self.memory.add_message(session_id, "assistant", full_response)

    def get_history(self, session_id: str, limit: int = 20) -> list[dict[str, str]]:
        return self.memory.get_messages(session_id, limit)
