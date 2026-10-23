# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# RS12_Flood_origin — 프로젝트 지침 (2026-10-23)

## 세션 시작 절차 (순서대로)
1. 아래 "연구 요지"를 한 줄로 재진술한다.
2. `research_log.md`(작업 일지, KST) 끝과 캐노니컬 로그 `cc_output/plan/2026.10.23/RS12_progress.md`의 "남은 일"을 읽는다.
3. 작업마다 `research_log.md`에 `### YYYY-MM-DD HH:MM KST — 제목` 항목(무엇·왜·결과·다음)을 append 한다. 세션 종료 시 Stop hook(`.claude/hooks/research_log_commit.sh`)이 이 파일이 바뀌지 않았으면 종료를 막고, 바뀌었으면 `git add -A && git commit`(제목 = 마지막 `###` 줄)을 자동 실행한다. 큰 단계가 끝나면 RS12_progress.md 세션 로그에도 append.

## 연구 요지
온난화는 홍수의 **출발점**(피크 물이 어느 지류에서 왔나)과 **터지는 지점**(어디서 먼저 둑을 넘나)을 함께 옮긴다.
CaMa-Flood v4.3 × CESM2-LE 10멤버, 하천망을 network-flow 그래프로 읽는다(그래프 이론이 핵심, XAI는 나중 "원인" 단계).
P0 파일럿(미시시피) 결과: **홍수 크기는 그대로(+0%)인데 피크 물의 8%가 눈 지류(상류 미시시피·미주리)에서 비 지류(오하이오)로 출발점을 옮겼다.** 눈 지류 분담 >40%인 해: 과거 5년에 1번 → 미래 100년에 1번.
계획서 원본: `flood_source_bottleneck_plan_v2.docx`(P0–P4); 요약 발표: `overleaf_ppt/main.tex`(beamer 16:9, XeLaTeX, 한글은 fontspec+Noto Sans CJK KR; kotex는 tectonic ICU 오류로 쓰지 않음). TikZ 원본 `overleaf_ppt/figures/src/fig_*.tex`(+`_preamble.tex`) → `figures/fig_*.pdf`; 로컬 컴파일은 `~/.local/bin/tectonic`(0.17), 그림은 `~/.claude/skills/latex-figure/scripts/tikz_compile.py --preamble "$(cat figures/src/_preamble.tex)"`. Overleaf git 토큰은 `~/.git-credentials`에 저장(묻지 않음); 푸시 = `git add -A && git commit && git pull --rebase origin main && git push origin main`.

## 실행 환경
```
export LD_LIBRARY_PATH=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/lib   # pandas GLIBCXX 오류 방지
PY=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/bin/python
$PY -u <script>          # 항상 -u (tee/pipe 버퍼링 방지)
```
- ncdump는 intel lib 문제로 쓰지 말고 xarray로 읽는다. 시스템 `python3`에는 xarray가 없다.
- climate2-00(로그인 노드)에서는 `nice`로만, 무거운 것은 qsub(01·03·04만, 05~08 금지).
- 긴 작업은 `nice nohup setsid ... &`로 세션과 분리, `.part→mv` 원자적 쓰기, 멱등(이미 있으면 skip). `/tmp` 금지.

## 파일럿 파이프라인 (cc_output/code/2026.10.23/)
```
p0_06_gauge_above_delta.py        → result/.../mississippi_gauge_mask.npz   (마스크·게이지 위치; 모든 후속 스크립트가 읽음)
bash run_pilot.sh                  → result/.../pilot/<member>_<year>.npz ×600  (p0_10을 5레인 병렬, 멱등; 완료 표식 pilot/logs/driver.log "ALL DONE")
bash run_pilot_post.sh             → ALL DONE 대기 → p0_11 → 요약을 RS12_progress.md에 append → "POST DONE"
$PY -u p0_11_pilot_figures.py [UPMIN_km2=10000]   → pilot_summary[_up100k].npz, 그림 A/B/B2/C (UPMIN≠10000이면 _up{N}k 접미)
$PY -u p0_12_groups.py             → pilot_group_labels.npy + 지류 묶음 분담 (pilot_summary.npz 필요)
$PY -u p0_13_slope_chart.py        → 그림 D (pilot_group_labels.npy 필요)
단일 멤버 수동 실행: $PY -u p0_10_pilot_compute.py <member> <y0> <y1> [v_mps=1.0]
```
- p0_01~p0_06은 질량 닫힘 검증(일회성, 1031.002/1952). 결과: 연간 잔차 +0.03%, 음수 runoff clip 필수, 분기(bifurcation)로 델타에 284 km³/yr 누출.
- 지류 묶음은 **p0_12 라벨**을 쓴다. p0_11의 기본 라벨링은 uparea 최대 경로를 본류로 잡아 미주리가 "본류"로 들어간다.
- 스크립트 상단 MAP/OUT/ROF/RES 경로 상수는 하드코딩; 다른 계정이면 수정.

## 핵심 레시피
- 발원: `C_i = Σ_{k=-5..5} R_i(pk+k−τ_i)·86400`, τ_i = 게이지까지 누적 rivlen / v(기본 1 m/s), 일 단위 반올림. runoff는 전년도 파일까지 이어붙여 τ 되감기.
- 병목: `storge / (rivlen·rivwth_gwdlr·rivhgt)`(=CaMa RIVSTOMAX)가 [pk−10, pk]에서 1을 아래서 위로 **처음** 넘는 날. 집계는 uparea ≥ 1만(기본) 또는 10만 km² 하천셀로 제한.
- 고정 τ 분해는 저류 ΔS를 무시하므로 ΣC/창유량 ≈ 1.04가 정상(닫힘은 p0_03의 정확 공식으로 별도 검증).

## 데이터 (모두 juen08282 소유, 읽기 가능)
- CaMa 출력: `/data2/juen/CaMa-output/cesm/<member>/{outflw,storge,fldfrc,flddph,fldare,maxdph}/o_<var><year>.nc` — 0.25°, (time,720,1440), row0=북, 일별, **time 스탬프 = 다음날 00Z**, outflw=일평균·storge=순간값.
- CESM2 runoff: `/data1/juen/CaMa-input/CESM2_roff/<member>/roff_<year>.nc` — 1°(180×360), 변수 `ro`, mm/s, **음수 있음 → max(ro,0)**.
- 지도: `/data2/juen/RS12_handoff/map/glb_15min/` — `.bin`은 little-endian, `nextxy` int4 (2,720,1440)(−9 하구, −10 내륙종단, −9999 바다), `uparea/rivlen/rivwth_gwdlr/rivhgt/ctmare/elevtn` float4, `inpmat_1deg_nc.bin` = int4 7×INPX, 7×INPY, float4 7×INPA(1-based, y=북부터). `bifprm.txt`(LPTHOUT=TRUE).
- 멤버 10개: LE2-1011.001 1031.002 1051.003 1071.004 1091.005 1111.006 1131.007 1151.008 1171.009 1191.010 (cesm 폴더에는 91개).
- 게이지(P0 "하구"): 32.125N 91.125W(빅스버그 상당, uparea 2.942 Mkm², 삼각주 분기 위 단일 출구).

## 폴더·보고 규약
- 산출물은 `cc_output/{plan,code,result}/YYYY.MM.DD/`(점 구분 날짜). `result/*/pilot/`·`__pycache__`는 git 제외(.gitignore).
- 보고는 연구질문→목표→분석→결과→판정 흐름. 남은 일은 "계산·그림" vs "사용자 결정 대기" 두 블록.
- 그림을 만들면 바로 보여준다. 결과 문장은 대상·숫자·동사만, 조건절 금지. 레시피 하나, 변형 최소(민감도는 SI).

## 남은 일 (2026-10-23 기준)
- 계산: 병목 정의 안정화(최초 교차 vs 지속 초과, 유량 가중, uparea 문턱), τ 민감도(0.5/1.5 m/s), rivhgt ±20%.
- 사용자 결정: 헤드라인 지표를 중심 km 대신 "눈 지류 분담률"로; 두 번째 유역(권고 컬럼비아·다뉴브·라인·인더스, 계획서는 갠지스·머리달링); 원인 변수(H2OSNO·RAIN daily) 다운로드(gdex.ucar.edu, wget 스크립트는 사용자 생성).
