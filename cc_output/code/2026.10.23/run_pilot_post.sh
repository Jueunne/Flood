#!/bin/bash
# Waits for run_pilot.sh to finish, then builds figures and appends the numeric summary to the progress log.
export LD_LIBRARY_PATH=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/lib
PY=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/bin/python
CODE=/home/juen0828/RS12_Flood_origin/cc_output/code/2026.10.23
RES=/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23
LOGMD=/home/juen0828/RS12_Flood_origin/cc_output/plan/2026.10.23/RS12_progress.md
until grep -q "ALL DONE" $RES/pilot/logs/driver.log 2>/dev/null; do sleep 30; done
n=$(ls $RES/pilot/LE2-*_*.npz | wc -l)
$PY -u $CODE/p0_11_pilot_figures.py > $RES/pilot_figures.log 2>&1
{
  echo
  echo "### 2026-10-23 (자동 체인, run_pilot_post.sh) — 파일럿 계산 완료 $(date '+%H:%M'), npz $n/600"
  echo '```'
  grep -vE "Warning|warn|ret =|arrmean|^\s*$" $RES/pilot_figures.log
  echo '```'
  echo "- 그림: result/2026.10.23/pilot_figA_source_map.png, pilot_figB_bottleneck_map.png, pilot_figB2_exceed_any_map.png, pilot_figC_summary.png; 수치 캐시 pilot_summary.npz"
  echo "- 재개 시: 위 수치로 판정(발원 중심 이동 > 200 km? 병목 이동 뚜렷? 유량 변화 %와 비례?) → 사용자에게 보고 후 갠지스·머리달링 확장 여부 결정."
} >> $LOGMD
echo "POST DONE $(date)" >> $RES/pilot/logs/driver.log
