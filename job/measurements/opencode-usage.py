#!/usr/bin/env python3
"""Sum the tokens of exported OpenCode sessions and convert them to gCO2e (Section V numerator)."""

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parent
# Factors, each with its source (see README.md, source register).
WH_PER_1000_OUTPUT = 1.03     # Oviedo et al., Joule 2026, as given in Session 8
GRID_G_PER_KWH = 337.0        # same grid factor as lcia-calculation.py


def session_row(path: Path) -> dict:
    data = json.loads(path.read_text())
    row = {"session": data["info"]["id"], "title": data["info"].get("title", ""),
           "requests": 0, "input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cost": 0.0}
    for message in data["messages"]:
        if "info" in message:                 # OpenCode 1.x export: {"info": {...}, "parts": [...]}
            info = message["info"]
            if info.get("role") != "assistant":
                continue
            model = f"{info.get('providerID')}/{info.get('modelID')}"
        else:                                 # OpenCode 2.x export: flat messages with a "type"
            info = message
            if info.get("type") != "assistant":
                continue
            model = f"{info['model'].get('providerID')}/{info['model'].get('id')}"
        if model != "openrouter/deepseek/deepseek-v4-flash-0731":
            raise ValueError(f"{path.name}: unexpected model {model}")
        tokens = info.get("tokens") or {}
        row["requests"] += 1
        row["input"] += tokens.get("input", 0)
        row["output"] += tokens.get("output", 0)
        row["reasoning"] += tokens.get("reasoning", 0)
        row["cache_read"] += (tokens.get("cache") or {}).get("read", 0)
        row["cost"] += info.get("cost") or 0.0
    return row


def main() -> None:
    paths = [Path(arg) for arg in sys.argv[1:]] or sorted(ROOT.glob("opencode-ses_*.json"))
    rows = [session_row(path) for path in paths]
    print("Factor: %.2f Wh per 1000 output tokens (reasoning billed as output) | grid %.1f gCO2e/kWh"
          % (WH_PER_1000_OUTPUT, GRID_G_PER_KWH))
    print("session|title|requests|input|output|reasoning|cache read|cost USD|kWh|gCO2e")
    total = {"requests": 0, "input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cost": 0.0}
    for row in rows:
        kwh = (row["output"] + row["reasoning"]) / 1000 * WH_PER_1000_OUTPUT / 1000
        print("%s|%s|%d|%d|%d|%d|%d|%.4f|%.6f|%.3f" % (
            row["session"], row["title"], row["requests"], row["input"], row["output"],
            row["reasoning"], row["cache_read"], row["cost"], kwh, kwh * GRID_G_PER_KWH))
        for key in total:
            total[key] += row[key]
    kwh = (total["output"] + total["reasoning"]) / 1000 * WH_PER_1000_OUTPUT / 1000
    print("TOTAL||%d|%d|%d|%d|%d|%.4f|%.6f|%.3f" % (
        total["requests"], total["input"], total["output"], total["reasoning"],
        total["cache_read"], total["cost"], kwh, kwh * GRID_G_PER_KWH))
    print("Short-query factor applied to long agent contexts; Section VI names that limit.")


if __name__ == "__main__":
    main()
