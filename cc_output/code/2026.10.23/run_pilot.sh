#!/bin/bash
# P0 pilot driver: 10 members x (1952-1981, 2071-2100); 5 parallel lanes, 2 members each. Idempotent (skips existing npz).
export LD_LIBRARY_PATH=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/lib
PY=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/bin/python
CODE=/home/juen0828/RS12_Flood_origin/cc_output/code/2026.10.23
LOG=/home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23/pilot/logs
MEMS=(LE2-1011.001 LE2-1031.002 LE2-1051.003 LE2-1071.004 LE2-1091.005 LE2-1111.006 LE2-1131.007 LE2-1151.008 LE2-1171.009 LE2-1191.010)
for lane in 0 1 2 3 4; do
  ( for i in $lane $((lane+5)); do m=${MEMS[$i]}
      nice -n 10 $PY -u $CODE/p0_10_pilot_compute.py $m 1952 1981 > $LOG/$m.past.log 2>&1
      nice -n 10 $PY -u $CODE/p0_10_pilot_compute.py $m 2071 2100 > $LOG/$m.future.log 2>&1
    done; echo "lane $lane done" >> $LOG/driver.log ) &
done
wait; echo "ALL DONE $(date)" >> $LOG/driver.log
