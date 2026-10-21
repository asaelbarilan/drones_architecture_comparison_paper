#!/bin/bash
# D-163 smoke: every paper architecture flies visible_target once (development seed 1061).
cd "$(dirname "$0")/../.."
export PYTHONPATH="src;scripts/diagnostics" PYTHONWARNINGS=ignore
PY=D:/drone_vla_pilot/venv_qwen/Scripts/python.exe
for A in C0 C1 C2 C3 C4 C5 C6 FULL C7 C8 C10 C13; do
  echo "=== $A $(date -u +%H:%M:%S)"
  timeout 1500 $PY scripts/diagnostics/run_qwen_capability_suite.py --architecture $A \
    --tasks visible_target --seed 1061 --out reports/paper_smoke_20261021/$A \
    > reports/paper_smoke_20261021/$A.log 2>&1
  echo "exit=$? $(grep -o '"task_pass": [a-z]*' reports/paper_smoke_20261021/$A/visible_target/result.json 2>/dev/null)"
done
echo "=== DONE $(date -u +%H:%M:%S)"
