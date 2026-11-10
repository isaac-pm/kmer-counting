#!/usr/bin/env python3
"""Carbon payback of the AI-assisted optimisation (Section V): cost of producing it / saving per run.

Version of 2026-11-10. The optimisation keeps the program unchanged (tutoring decision, early
November 2026): the kept path is the right-sized allocation and the Cython build of the frozen
source. The agent's rewritten counter (session ses_e80fda1a..., runs 16118792-800) is discarded, and
its cost is left out of the payback; it is printed separately for Section VI.
The version of 2026-10-27 (payback-summary-20261027.txt) counted the rewritten counter instead.
"""

from pathlib import Path
from statistics import median
import importlib.util
import re


ROOT = Path(__file__).resolve().parent
BASELINE_G = 14.888              # lcia-calculation.py, lcia-summary-20261019.txt
RUNS_PER_YEAR = 100              # assumption, Section VI
# Same factors as optimised-calculation.py, for the share of a node held by short jobs.
GRID_G_PER_KWH, PUE, MEMORY_W_PER_GB = 337.0, 1.36, 0.3725
HARDWARE_G, SERVICE_LIFE_S, NODE_CORES, NODE_MEMORY_GB = 913_700.0, 6 * 365.25 * 24 * 3600, 128, 256

# The two measured variants of the kept path (optimised-calculation.py output for each).
VARIANTS = {
    "right-sized": ROOT / "optimised-summary-rightsized-20261110.txt",
    "right-sized + Cython": ROOT / "optimised-summary-cython-20261110.txt",
}
# Short jobs of the kept path, charged from their own sacct records:
# the three launch failures of 27 Oct (job-script lesson kept), the failed and the good Cython build,
# the two smoke tests on a 100,000-read sample. 16225102 was cancelled before it started (0 s).
SHORT_JOBS = (16118778, 16118780, 16118782, 16225100, 16225112, 16225101, 16225113)
# Accounting collectors (1 core, 256 MB, about 2 s each; their own sacct is not archived):
# 3 for the launch failures + 10 for the measured runs of the kept path.
COLLECTORS_KEPT = 13
# Discarded path, left out of the cost: the rewritten counter.
DISCARDED_SESSIONS = {"ses_e80fda1afffehTr0XkgdTVHW3y"}
DISCARDED_SUMMARY = ROOT / "optimised-summary-20261027.txt"   # its five runs
COLLECTORS_DISCARDED = 5


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seconds(value: str) -> float:
    days = 0
    if "-" in value:
        day_text, value = value.split("-")
        days = int(day_text)
    parts = [float(part) for part in value.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def gigabytes(req_mem: str) -> float:
    units = {"K": 1 / 1024, "M": 1.0, "G": 1024.0, "T": 1024.0 ** 2}
    return float(req_mem[:-1]) * units[req_mem[-1]] * 1.048576 / 1000


def share_g(cores: int, mem_gb: float, elapsed: float, idle_w: float) -> float:
    """Idle share and memory of a short allocation; the program increment is negligible here."""
    joules = idle_w * cores / NODE_CORES * elapsed + MEMORY_W_PER_GB * mem_gb * elapsed
    embodied = HARDWARE_G * max(cores / NODE_CORES, mem_gb / NODE_MEMORY_GB) * elapsed / SERVICE_LIFE_S
    return joules / 3.6e6 * PUE * GRID_G_PER_KWH + embodied


def summary(path: Path) -> dict:
    text = path.read_text()
    runs = re.findall(r"^(\d+)\|(aion-\d+)\|\d+\|[\d.]+\|(\d+)\|([\d.]+)\|[\d.]+\|\d+\|([\d.]+)$", text, re.M)
    parts = re.search(r"idle share (\d+) J \| program (\d+) J \| memory (\d+) J", text)
    return {"idle_w": float(re.search(r"Idle packages ([\d.]+) W", text).group(1)),
            "after_g": float(re.search(r"= ([\d.]+) gCO2e per run", text).group(1)),
            "runs_g": [float(r[4]) for r in runs], "elapsed": [float(r[2]) for r in runs],
            "nodes": sorted({r[1] for r in runs}),
            "program_j": float(parts.group(2)), "memory_j": float(parts.group(3))}


usage = load("opencode-usage")
sessions = [usage.session_row(path) for path in sorted(ROOT.glob("opencode-ses_*.json"))]
kept = [r for r in sessions if r["session"] not in DISCARDED_SESSIONS]
dropped = [r for r in sessions if r["session"] in DISCARDED_SESSIONS]


def ai_g(rows: list) -> float:
    tokens = sum(r["output"] + r["reasoning"] for r in rows)
    return tokens / 1000 * usage.WH_PER_1000_OUTPUT / 1000 * usage.GRID_G_PER_KWH


variants = {name: summary(path) for name, path in VARIANTS.items()}
idle_w = next(iter(variants.values()))["idle_w"]
chosen = min(variants, key=lambda name: variants[name]["after_g"])
after_g = variants[chosen]["after_g"]
saving_g = BASELINE_G - after_g

short = []
for job_id in SHORT_JOBS:
    row = next(line.split("|") for line in (ROOT / f"sacct-{job_id}.txt").read_text().splitlines()
               if line.startswith(f"{job_id}|"))
    short.append((job_id, row[1], int(row[6]), gigabytes(row[7]), seconds(row[9]), row[15]))
short_g = sum(share_g(c, m, e, idle_w) for _, _, c, m, e, _ in short)
collector_g = share_g(1, 0.256 * 1.073741824, 2, idle_w)
measured_g = sum(sum(v["runs_g"]) for v in variants.values())
runs_g = measured_g + short_g + COLLECTORS_KEPT * collector_g
ai_kept = ai_g(kept)
cost_g = ai_kept + runs_g

print("$ python3 job/measurements/payback-calculation.py")
print(f"Baseline {BASELINE_G} gCO2e per run (exclusive node, aion-0144 RAPL series)")
for name, v in variants.items():
    print(f"  {name}: {v['after_g']:.3f} gCO2e per run, five runs {sum(v['runs_g']):.3f} g, "
          f"median Elapsed {median(v['elapsed']):.0f} s on {', '.join(v['nodes'])}")
print(f"Chosen: {chosen}, {after_g:.3f} gCO2e per run")
print(f"\nKept OpenCode sessions: {len(kept)}, {sum(r['requests'] for r in kept)} requests, "
      f"{sum(r['output'] + r['reasoning'] for r in kept)} output tokens incl. reasoning -> {ai_kept:.3f} gCO2e")
for job_id, name, c, m, e, state in short:
    print(f"  short job {job_id} {name} {state}: {c} cores, {m:.2f} GB, {e:.0f} s -> "
          f"{share_g(c, m, e, idle_w):.4f} g")
print(f"Aion runs: ten measured runs {measured_g:.3f} g + {len(short)} short jobs {short_g:.4f} g "
      f"+ {COLLECTORS_KEPT} collectors {COLLECTORS_KEPT * collector_g:.4f} g = {runs_g:.3f} gCO2e")
print(f"Cost of producing the optimisation (kept path): {cost_g:.3f} gCO2e")
print(f"Saving per run: {BASELINE_G} - {after_g:.3f} = {saving_g:.3f} gCO2e")
print(f"Payback: {cost_g:.3f} / {saving_g:.3f} = {cost_g / saving_g:.2f} runs "
      f"-> {cost_g / saving_g / RUNS_PER_YEAR * 365.25:.1f} days at {RUNS_PER_YEAR} runs per year")
print(f"AI part only: {ai_kept / saving_g:.2f} runs | runs part only: {runs_g / saving_g:.2f} runs")

# Section VI sensitivities, each moving one input.
d = summary(DISCARDED_SUMMARY)
dropped_g = ai_g(dropped) + sum(d["runs_g"]) + COLLECTORS_DISCARDED * collector_g
print(f"\nSection VI sensitivities")
print(f"Discarded path (rewritten counter), not counted: {len(dropped)} session, "
      f"{sum(r['requests'] for r in dropped)} requests, {ai_g(dropped):.3f} g + five runs "
      f"{sum(d['runs_g']):.3f} g + {COLLECTORS_DISCARDED} collectors = {dropped_g:.3f} g; "
      f"if counted, payback {(cost_g + dropped_g) / saving_g:.2f} runs")
print(f"AI assistance x10: payback {(cost_g + 9 * ai_kept) / saving_g:.2f} runs "
      f"-> {(cost_g + 9 * ai_kept) / saving_g / RUNS_PER_YEAR * 365.25:.0f} days")
per100 = ai_kept / GRID_G_PER_KWH * 100
print(f"AI service grid +100 gCO2e/kWh: +{per100:.2f} g cost, +{per100 / saving_g:.2f} runs; "
      f"at twice 337: payback {(cost_g + ai_kept) / saving_g:.2f} runs")
v = variants[chosen]
idle_whole = (idle_w * median(v["elapsed"]) + v["program_j"] + v["memory_j"]) / 3.6e6 * PUE * GRID_G_PER_KWH
# If the freed cores stayed idle, the run is charged the whole node's idle draw for its walltime
# (operational), production still by its share.
op_after = re.search(r"Median operational ([\d.]+) g \+ embodied ([\d.]+) g", VARIANTS[chosen].read_text())
idle_after = idle_whole + float(op_after.group(2))
print(f"Freed cores left idle (whole-node idle draw over the median walltime): "
      f"{idle_after:.3f} g per run, saving {BASELINE_G - idle_after:.2f} g, "
      f"payback {cost_g / (BASELINE_G - idle_after):.2f} runs")
# Marginal check of the Cython lever alone: its own sessions, build and smoke jobs, five runs and
# collectors, against the saving it adds over the right-sized frozen counter.
CYTHON_SESSIONS = {"ses_e39d28e96ffe2cY33z7sMiWjMB", "ses_e39ce6350ffegS7XjYZprykhxy"}
CYTHON_SHORT = {16225100, 16225112, 16225113}
cy = variants["right-sized + Cython"]
cy_cost = (ai_g([r for r in sessions if r["session"] in CYTHON_SESSIONS])
           + sum(share_g(c, m, e, idle_w) for j, _, c, m, e, _ in short if j in CYTHON_SHORT)
           + sum(cy["runs_g"]) + 5 * collector_g)
cy_saving = variants["right-sized"]["after_g"] - cy["after_g"]
print(f"Cython lever alone: cost {cy_cost:.3f} g, saving {cy_saving:.3f} g per run over the right-sized "
      f"script ({(1 - median(cy['elapsed']) / median(variants['right-sized']['elapsed'])) * 100:.1f} % "
      f"shorter walltime), payback {cy_cost / cy_saving:.0f} runs "
      f"-> {cy_cost / cy_saving / RUNS_PER_YEAR * 12:.0f} months")
