#!/bin/bash
# D-176 round 3: H7 fix and H5 detour on the FULL stack: H1 typed contract, H2 kind-aware executive, both.
# Same 12 tasks and seeds as the D-166 matrix (paired with its FULL baseline). Waits until the
# D-166 matrix has finished so the GPU is free. No retries; a failed run is logged.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_handles_d176
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
true
echo "matrix finished; starting $(date -u +%H:%M:%S)"
for SEED in 1060 1061 1062; do
  for A in FULL_H125 FULL_H1257; do
    if [ -d "$OUT/s$SEED/$A" ]; then echo "skip s$SEED $A (exists)"; continue; fi
    mkdir -p "$OUT/s$SEED"
    echo "=== s$SEED $A $(date -u +%H:%M:%S)"
    timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
      --tasks $TASKS --seed $SEED --out "$OUT/s$SEED/$A" > "$OUT/s$SEED/$A.log" 2>&1
    echo "exit=$? passes=$(grep -l '"task_pass": true' $OUT/s$SEED/$A/*/result.json 2>/dev/null | wc -l)"
  done
done
echo "=== DONE $(date -u +%H:%M:%S)"
