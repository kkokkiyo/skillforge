"""NAT custom function hosting the same bounded agent + broker."""

import asyncio
import json
from typing import Literal
from nat.plugin_api import (
    Builder,
    FunctionInfo,
    FunctionBaseConfig,
    register_function,
    Context,
    ContextState,
)
from .config import load_env
from .app import Database
from .engine import execute


class SkillForgeConfig(FunctionBaseConfig, name="skillforge_refund"):
    mode: Literal["mock", "live"] = "mock"


@register_function(config_type=SkillForgeConfig)
async def register_skillforge(config: SkillForgeConfig, builder: Builder):
    load_env()

    async def refund(order_id: str) -> str:
        db = Database()
        try:
            context = Context(ContextState.get())
            nat_steps = []
            subscription = context.intermediate_step_manager.subscribe(
                on_next=lambda step: nat_steps.append(step.model_dump(mode="json"))
            )
            with context.push_active_function(
                "skillforge_refund", {"order_id": order_id, "mode": config.mode}
            ) as span:
                # CLI integration is serial. NAT's exporter requires events on its loop.
                result = execute(
                    db,
                    order_id,
                    mode=config.mode,
                    budget_seconds=90,
                    tool_span_factory=context.push_active_function,
                )
                span.set_output(
                    {
                        "run_id": result["run_id"],
                        "status": result["status"],
                        "metrics": result["metrics"],
                    }
                )
            await asyncio.sleep(0)
            subscription.unsubscribe()
            from .config import ROOT

            folder = ROOT / "artifacts"
            folder.mkdir(exist_ok=True)
            (folder / "nat-span-evidence.json").write_text(
                json.dumps(
                    {
                        "mode": config.mode,
                        "run_id": result["run_id"],
                        "events": nat_steps,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (folder / ("nat-" + config.mode + "-evidence.json")).write_text(
                json.dumps(
                    {"result": result, "events": db.events(result["run_id"])},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            return json.dumps(result)
        finally:
            db.conn.close()

    yield FunctionInfo.from_fn(
        refund,
        description="Synthetic refund through a policy-checked, bounded agent; input is an order ID.",
    )
