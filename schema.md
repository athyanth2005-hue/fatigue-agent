# Architecture Schema - Fatigue Design Agent

```mermaid
flowchart TD
    U([User task in plain English]) --> CLI[main.py CLI]
    CLI --> A[FatigueAgent.run]
    MEM[(".agent_memory.json<br/>long-term memory")] <--> A
    A --> LLM{{Claude via Anthropic API<br/>system prompt + tool schemas}}
    LLM -->|stop_reason = tool_use| R[Tool Router<br/>execute_tool]
    R --> T1[get_material_properties]
    R --> T2[stress_concentration_hole]
    R --> T3[fatigue_notch_factor]
    R --> T4[marin_endurance_limit]
    R --> T5[goodman_safety_factor]
    R --> T6[basquin_life]
    R --> T7[calculator - AST-sandboxed]
    R --> T8[save_report]
    T1 --- DB[(materials.json)]
    T8 --> REP[/reports/*.md/]
    T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 -->|tool_result / error| OBS[Observation]
    OBS -->|appended to messages| LLM
    LLM -->|stop_reason = end_turn| FIN([Final answer + saved report])
    FIN --> A
```

## Agent loop (ReAct: Plan -> Act -> Observe -> Reflect)
1. **Plan** - model writes a numbered plan from the task.
2. **Act** - model emits one or more `tool_use` calls (e.g. Kt -> Kf -> Se -> life).
3. **Observe** - `execute_tool` runs them; results (or errors) return as `tool_result`.
4. **Reflect** - model sanity-checks, retries on error, or calls more tools (max 12 steps).
5. **Report** - model calls `save_report`, then returns a summary.

## Components
| Component | Role |
|---|---|
| `agent.py` | Orchestrator loop, step limit, persistent memory |
| `tools.py` | 8 tools + JSON schemas + safe dispatcher with error feedback |
| `materials.json` | Material knowledge base |
| `.agent_memory.json` | Cross-session memory (last 5 tasks) |
