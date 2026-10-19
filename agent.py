"""Fatigue Design Agent - a ReAct-style tool-using loop on the Anthropic API."""
import json, os
from pathlib import Path
import anthropic
from tools import TOOLS, execute_tool

MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 12
MEMORY_FILE = Path(".agent_memory.json")

SYSTEM = """You are a Fatigue Design Agent for mechanical engineers.
Work autonomously in this loop: PLAN -> ACT (call tools) -> OBSERVE -> REFLECT -> repeat -> REPORT.
Rules:
1. Start with a short numbered plan, then call tools. Never guess material data or do arithmetic by hand - use tools.
2. If a tool returns an error, fix the inputs and retry. If required inputs are missing, state a clear assumption and continue.
3. Before concluding, sanity-check results (units, Kf >= 1, safety factor plausibility, yield vs fatigue).
4. Finish by calling save_report with a concise markdown report (inputs, assumptions, steps, results, verdict), then give the user a short summary.
Stress units are MPa, lengths mm. Property values are handbook approximations - say so."""

class FatigueAgent:
    def __init__(self, verbose=True):
        self.client = anthropic.Anthropic()
        self.verbose = verbose
        self.history = self._load_memory()

    def _load_memory(self):
        return json.loads(MEMORY_FILE.read_text()) if MEMORY_FILE.exists() else []

    def _remember(self, task, answer):
        self.history.append({"task": task, "answer": answer[:400]})
        MEMORY_FILE.write_text(json.dumps(self.history[-5:], indent=2))

    def run(self, task: str) -> str:
        system = SYSTEM
        if self.history:
            system += "\n\nPrevious sessions (for context):\n" + "\n".join(f"- {h['task']} -> {h['answer']}" for h in self.history[-3:])
        messages = [{"role": "user", "content": task}]
        for step in range(1, MAX_STEPS + 1):
            resp = self.client.messages.create(model=MODEL, max_tokens=2000, system=system, tools=TOOLS, messages=messages)
            messages.append({"role": "assistant", "content": resp.content})
            for b in resp.content:
                if b.type == "text" and self.verbose and b.text.strip():
                    print(f"\n[step {step}] THOUGHT: {b.text.strip()}")
            if resp.stop_reason != "tool_use":
                answer = "".join(b.text for b in resp.content if b.type == "text")
                self._remember(task, answer)
                return answer
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    out = execute_tool(b.name, b.input)
                    if self.verbose:
                        print(f"[step {step}] ACTION: {b.name}({json.dumps(b.input)})\n          OBSERVATION: {out}")
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
            messages.append({"role": "user", "content": results})
        return "Stopped: step limit reached before the agent finished."
