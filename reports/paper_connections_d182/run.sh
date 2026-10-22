#!/bin/bash
# D-182 connection handles: C2_H..C6_H (H3 + H4) and C7_H, C8_H (H4 + H9).
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_connections_d182
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
echo "starting $(date -u +%H:%M:%S)"
for SEED in 1060 1061 1062; do
  for A in C2_H C3_H C4_H C5_H C6_H C7_H C8_H; do
    if [ -d "$OUT/s$SEED/$A" ]; then echo "skip s$SEED $A (exists)"; continue; fi
    mkdir -p "$OUT/s$SEED"
    echo "=== s$SEED $A $(date -u +%H:%M:%S)"
    timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
      --tasks $TASKS --seed $SEED --out "$OUT/s$SEED/$A" > "$OUT/s$SEED/$A.log" 2>&1
    echo "exit=$? passes=$(grep -l '"task_pass": true' $OUT/s$SEED/$A/*/result.json 2>/dev/null | wc -l)"
  done
done
echo "=== DONE $(date -u +%H:%M:%S)"
