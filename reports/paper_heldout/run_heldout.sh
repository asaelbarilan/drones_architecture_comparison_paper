#!/bin/bash
# HELD-OUT run (user launches it; never run by an agent). Frozen at commit 6f88bb5.
# Seeds 1-40 are held out: nothing was trained or tuned on them. Run once; no fixes after.
# Arms: FULL (no handles) and FULL_H125 (H1 + H2 + H5). Optional extra arms as arguments,
# e.g.  bash reports/paper_heldout/run_heldout.sh C0 C13
# Time: about 7.5 min per seed per arm, so 2 arms x 40 seeds is about 10 hours.
# Resumable: a finished seed/arm folder is skipped. Keep Unreal and Ollama closed.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_heldout
ARMS="FULL FULL_H125 $*"
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
echo "held-out start $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD) arms: $ARMS"
for SEED in $(seq 1 40); do
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
