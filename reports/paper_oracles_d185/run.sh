#!/bin/bash
# D-185 A: oracle swaps per level (privileged reference lines, never results), 12 tasks.
# D-185 C: latency-relaxed twins (follow_target_slow, closing_passage_late) for key arms.
# Development seeds 1060-1062 only. Resumable: finished seed/arm folders are skipped.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_oracles_d185
TASKS="known_goal visible_target approach_hover turn_search overturned_vehicle conditional_gate ordered_visit closing_passage follow_target obstacle_post obstacle_slalom obstacle_low_wall"
ORACLE_ARMS="C0_VLA FULL_H125_OP C13_H125_OP FULL_OG FULL_H125_OG C13_H125_OG C3_H_OG"
TWIN_ARMS="C0 C0_VLA FULL FULL_H125 C13_H125 C3_H FULL_H125_OP FULL_H125_OG"
run() {  # seed arm out tasks...
  local SEED=$1 A=$2 DIR=$3; shift 3
  if [ -d "$DIR" ]; then echo "skip $DIR (exists)"; return; fi
  mkdir -p "$(dirname "$DIR")"
  echo "=== $DIR $(date -u +%H:%M:%S)"
  timeout 3600 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
    --tasks "$@" --seed $SEED --out "$DIR" > "$DIR.log" 2>&1
  echo "exit=$? passes=$(grep -l '"task_pass": true' $DIR/*/result.json 2>/dev/null | wc -l)"
}
echo "starting $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD)"
for SEED in 1060 1061 1062; do
  for A in $TWIN_ARMS; do run $SEED $A $OUT/twins/s$SEED/$A follow_target_slow closing_passage_late; done
  for A in $ORACLE_ARMS; do run $SEED $A $OUT/s$SEED/$A $TASKS; done
done
echo "=== DONE $(date -u +%H:%M:%S)"
