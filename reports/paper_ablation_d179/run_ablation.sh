#!/bin/bash
# D-179 remove-one ablation of the final stack FULL_H125 (H1 typed contract, H2 kind-aware
# executive, H5 measured openings): the full stack and the stack minus each handle.
# FULL (none) is the D-169 matrix arm; FULL_H125D (+ wall detour) is round 5 (D-178).
# Same 12 tasks and development seeds 1060-1062. No retries; a failed run is logged.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_ablation_d179
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
echo "starting $(date -u +%H:%M:%S)"
for SEED in 1060 1061 1062; do
  for A in FULL_H125 FULL_H12 FULL_H15 FULL_H25; do
    if [ -d "$OUT/s$SEED/$A" ]; then echo "skip s$SEED $A (exists)"; continue; fi
    mkdir -p "$OUT/s$SEED"
    echo "=== s$SEED $A $(date -u +%H:%M:%S)"
    timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
      --tasks $TASKS --seed $SEED --out "$OUT/s$SEED/$A" > "$OUT/s$SEED/$A.log" 2>&1
    echo "exit=$? passes=$(grep -l '"task_pass": true' $OUT/s$SEED/$A/*/result.json 2>/dev/null | wc -l)"
  done
done
echo "=== DONE $(date -u +%H:%M:%S)"
