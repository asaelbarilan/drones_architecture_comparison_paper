#!/bin/bash
# D-187 follow-up: C1_H rerun on the fixed H4 scope (all 3 seeds on one code version), and the
# matched-latency plan oracle FULL_H125_OPM (12 tasks + closing_passage_late). Dev seeds only.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_round2_d187
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
run() {
  local SEED=$1 A=$2 DIR=$3; shift 3
  if [ -d "$DIR" ]; then echo "skip $DIR"; return; fi
  mkdir -p "$(dirname "$DIR")"; echo "=== $DIR $(date -u +%H:%M:%S)"
  timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
    --tasks "$@" --seed $SEED --out "$DIR" > "$DIR.log" 2>&1
  echo "exit=$? passes=$(grep -l '"task_pass": true' $DIR/*/result.json 2>/dev/null | wc -l)"
}
echo "starting $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD)"
for SEED in 1060 1061 1062; do
  run $SEED C1_H $OUT/s$SEED/C1_H $TASKS
  run $SEED FULL_H125_OPM $OUT/s$SEED/FULL_H125_OPM $TASKS
  run $SEED FULL_H125_OPM $OUT/twins/s$SEED/FULL_H125_OPM closing_passage_late
done
echo "=== DONE $(date -u +%H:%M:%S)"
