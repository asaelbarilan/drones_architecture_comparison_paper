#!/bin/bash
# HELD-OUT run (user launches it; never run by an agent). Frozen at the commit printed below.
# Seeds 1-10 of the held-out set 1-40: nothing was trained or tuned on them. Run once; no fixes after.
# 22 arms: the 12 vanilla architectures and the 10 handled versions (D-180..D-182).
# Time: about 7.5 min per seed per arm, so 22 arms x 10 seeds is about 28 hours.
# Resumable: a finished seed/arm folder is skipped, so it can be stopped and restarted.
# Keep Unreal and Ollama closed. Optional: pass seeds as arguments, e.g. "1 2 3".
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_heldout
ARMS="C0 C1 C2 C3 C4 C5 C6 C7 C8 FULL C10 C13 C2_H C3_H C4_H C5_H C6_H C7_H C8_H FULL_H125 C10_H125 C13_H125"
SEEDS="${*:-$(seq 1 10)}"
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
echo "held-out start $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD) arms: $ARMS"
for SEED in $SEEDS; do
  for A in $ARMS; do
    if [ -d "$OUT/s$SEED/$A" ]; then echo "skip s$SEED $A (exists)"; continue; fi
    mkdir -p "$OUT/s$SEED"
    echo "=== s$SEED $A $(date -u +%H:%M:%S)"
    timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
      --tasks $TASKS --seed $SEED --out "$OUT/s$SEED/$A" > "$OUT/s$SEED/$A.log" 2>&1
    echo "exit=$? passes=$(grep -l '"task_pass": true' $OUT/s$SEED/$A/*/result.json 2>/dev/null | wc -l)"
  done
done
echo "=== DONE $(date -u +%H:%M:%S)"
