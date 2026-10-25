#!/bin/bash
# D-188 step 3: the five harder planning tasks on the best version of every architecture,
# plus vanilla FULL and C13. Development seeds 1060-1062. Resumable.
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
OUT=reports/paper_harder_d188
TASKS="ordered_visit_3 ordered_visit_4 conditional_search revisit spatial_relation"
ARMS="FULL_H125 C13_H125 C10_HP C0 C1 C2_H2 C3_H C4_H C5_H C6_H C7_H C8_H FULL C13"
echo "starting $(date -u +%H:%M:%S) commit $(git rev-parse --short HEAD)"
for SEED in 1060 1061 1062; do
  for A in $ARMS; do
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
