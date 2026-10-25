#!/bin/bash
# D-187 handle round 2 (equal budget per architecture), development seeds 1060-1062.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_round2_d187
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
echo "starting $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD)"
for SEED in 1060 1061 1062; do
  for A in FULL_HP C13_HP C10_HP C2_H2 C1_H; do
    DIR=$OUT/s$SEED/$A
    if [ -d "$DIR" ]; then echo "skip $DIR"; continue; fi
    mkdir -p "$OUT/s$SEED"
    echo "=== $DIR $(date -u +%H:%M:%S)"
    timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
      --tasks $TASKS --seed $SEED --out "$DIR" > "$DIR.log" 2>&1
    echo "exit=$? passes=$(grep -l '"task_pass": true' $DIR/*/result.json 2>/dev/null | wc -l)"
  done
done
echo "=== DONE $(date -u +%H:%M:%S)"
