# RS12 홍수 발원지·병목 이동 — 캐노니컬 진행 로그

## 요지 (항상 먼저 읽기)
- 주제: 온난화는 홍수를 키우는 게 아니라 옮긴다. 하천망을 네트워크 플로우로 읽어
  (a) 하구 피크의 물이 어디서 왔나(발원, 역추적), (b) 어디서 먼저 넘쳤나(병목, 용량 초과)를 과거/미래로 그린다.
- 계획서: `flood_source_bottleneck_plan_v2.docx` (2026-10-23, 전체 P0–P4). 현재 단계 = **P0 미시시피 파일럿** (AI 미사용).
- 출력 규약: `cc_output/{plan,code,result}/YYYY.MM.DD/` (RS11과 동일). 계획서의 `results/P0_mississippi/`는 쓰지 않음(사용자 10/23 결정).
- P0 판정: 발원 중심 이동 > 200 km 또는 병목 이동 뚜렷 → 갠지스·머리달링 추가; 유량 변화 %에 단순 비례 → 접음.

## 데이터 (2026-10-23 확인)
- CaMa 출력: `/data2/juen/CaMa-output/cesm/LE2-*/{outflw,storge,fldfrc,flddph,fldare,maxdph}/o_<var>YYYY.nc`
  0.25° (720×1440), 일별, 1951–2100, 91 디렉터리(1개는 _smoke). time 스탬프 = 다음날 00시(1951-01-02…1952-01-01).
- CaMa 입력 runoff: `/data1/juen/CaMa-input/CESM2_roff/LE2-*/roff_YYYY.nc` 1° (180×360), 변수 `ro`, 1850–2100.
- CaMa 지도: `/data2/juen/RS12_handoff/map/glb_15min/` — nextxy.bin, basin.bin, uparea.bin, rivlen.bin,
  rivwth_gwdlr.bin(런에 사용), rivhgt.bin, rivseq.bin, ctmare.bin, nxtdst.bin, elevtn.bin, fldhgt.bin, bifprm.txt(LPTHOUT=TRUE).
- 런 namelist 예: `/data2/juen/CaMa-work/cesm2_1deg/LE2-1031.002/input_cmf.nam` (DT=3600, DROFUNIT=1000, IFRQ_OUT=24).
- CaMa 소스: `/home/juen08282/CaMa-Flood/cmf_v430_pkg_20260312/src/` (물수지 = cmf_calc_stonxt_mod.F90, 하도용량 = cmf_ctrl_maps_mod.F90:717 `RIVSTOMAX = rivlen×rivwth×rivhgt`).
- Python: `/usr/local/anaconda3/2022.10/envs/p3.9_cpu/bin/python` + `LD_LIBRARY_PATH=/usr/local/anaconda3/2022.10/envs/p3.9_cpu/lib`.

## 결정 사항
- 2026-10-23: 출력 규약 = cc_output 규약(사용자).
- 병목 판정은 rivwth×rivhgt×유속 근사 대신 CaMa 내부 기준 `storge / RIVSTOMAX > 1`로 (제안, 사용자 확인 대기).

## 세션 로그
### 2026-10-23
- 폴더 규약·로그 생성. 데이터 경로 확인(위). P0에 필요한 변수(outflw, storge, runoff, 지도)는 모두 보유 → 추가 다운로드 불필요.
- **질량 검증(CaMa 물수지 닫힘) 완료** — 멤버 LE2-1031.002, 1952년. 코드 code/2026.10.23/p0_01~06, 로그·npz·png = result/2026.10.23/.
  - CaMa 내부: `stonxt`에서 셀별 S(t+dt)=S+(inf−out−pthout)·dt+runoff·dt. 전역 오차 로그상 1e-12 km³(완전 보존). outflw=rivout+fldout(분기 pthout 미포함), 일평균; storge는 출력 시각 순간값(스탬프=다음날 00Z).
  - **닫힘 공식(확정)**: Σ_cell max(ro,0)·INPA(inpmat)/1000 − outflw(출구) = ΔS(storge). 분기 교차 없는 상류 부분유역(미주리 상류 0.51 Mkm²)에서 일별 잔차 0.00%.
  - 함정 1: CESM runoff 음수값을 CaMa가 0으로 절단(cmf_ctrl_forcing_mod.F90:492). 파일 합을 그대로 쓰면 −3.7%(전지구 −3%) 편향. → 반드시 max(ro,0).
  - 함정 2: 분기(LPTHOUT, bifprm.txt). 미시시피 basin 6 단독은 +47% 미닫힘(하구 outflw 9.5k m³/s, 평탄). 연 284 km³가 분기 채널로 애차팔라야(65, 135 km³)와 삼각주 소유역 7개(8792·14896·11571·11869·11022·15424·2922)로 유출. 연결 31개 유역 합계는 0.1%로 닫힘(16·17 캐나다 유역은 영향 0).
  - **P0 "하구" 정의(제안)**: 삼각주 분기 시작(31.6°N) 위 본류 32.125°N, 91.125°W(uparea 2.942 Mkm², basin 6의 99.6%, 빅스버그 상당). 단일 출구(분기 교차 경로 3개 있으나 유량 ≈0), 연 잔차 +0.03%, 일별 3e-4. 1952 피크 26,477 m³/s(4월 20일, day 111), 연평균 18,208 m³/s. 마스크=result/2026.10.23/mississippi_gauge_mask.npz.
  - 데이터 형식: nextxy.bin int4 (2,720,1440) row0=북; 음수 코드 −9 하구, −10 내륙종단, −9999 바다. inpmat_1deg_nc.bin = int4 7×INPX, 7×INPY, float32 7×INPA (1-based 1° 인덱스, y=북부터). basin.bin ID로 뽑은 마스크와 nextxy 상류 추적이 완전 일치(5118셀, 2.955 Mkm²).
  - 역추적용 함의: 고정 τ 분해 Σ R_i(t−τ_i)는 저류항 ΔS를 무시하므로 "합=유량"은 안 닫히는 것이 정상. 보고는 (i) 위 정확 닫힘으로 장부 검증, (ii) 고정 τ 근사의 잔차 크기를 별도 보고.
- 추가 다운로드: P0에는 불필요(outflw·storge·runoff·지도 보유). P1(비·눈·기온·SWE·SM)부터 필요, PRECT는 보유([[reference_cesm2_prect_all_merge]]).

### 다음 단계
1. 합류점 그래프 + τ(rivlen 누적, rivvel 없음 → rivlen/1 m/s 근사 또는 outflw 상관 지연으로 보정) — 사용자 확인 후 착수.
2. 병목 판정 `storge/RIVSTOMAX`(rivlen×rivwth_gwdlr×rivhgt) 채택 여부 — 사용자 결정 대기.
- **파일럿 계산 착수(네트워크 플로우, AI 없음)** — 사용자 결정: 발원·병목 지도를 먼저 보고 원인(적설·비)은 뒤로. 코드 p0_10(멤버-연도별 계산)·p0_11(집계·그림)·run_pilot.sh(드라이버, nohup setsid, 5레인)·run_pilot_post.sh(완료 대기 → 그림 → 이 로그에 자동 append).
  - 설정: 10멤버(1011.001~1191.010), 과거 1952–1981·미래 2071–2100, 게이지 32.125N/91.125W, τ = 하도 누적거리 / 1 m/s, 발원 창 pk±5일, 병목 창 pk−10..pk, 병목 = storge/RIVSTOMAX가 1을 아래서 위로 처음 넘는 셀(집계 시 uparea ≥ 1만 km² 하천셀로 제한).
  - 스모크(1031.002, 1952–53): 고정 τ 분해 합 / 창 유량 = 1.04 (저류 무시에도 4% 이내), 창 안 용량 초과 셀 4,000+ → 큰 하천으로 거르지 않으면 병목이 흐려짐.
  - 출력: result/2026.10.23/pilot/<member>_<year>.npz (멱등, 재실행 시 건너뜀), 로그 pilot/logs/. 완료 표식 = pilot/logs/driver.log 의 "ALL DONE", 후처리 완료 = "POST DONE".
  - **재개 방법**: driver.log 확인 → POST DONE이면 이 로그 끝의 자동 요약과 그림 4장 읽고 판정 보고. 없으면 `nohup setsid run_pilot.sh` 재실행(멱등) 후 `run_pilot_post.sh`.
- 추가 변수 결정: 파일럿 1차는 다운로드 없음. 원인 단계용 최소 변수 = H2OSNO(일 SWE), RAIN(일, 땅 재분배 후 비), 선택 SOILWATER_10CM; 10멤버×7청크×~293 MB ≈ 변수당 20 GB. NCAR THREDDS가 gdex.ucar.edu로 이전되어 wget 스크립트는 사용자 생성 필요.

### 2026-10-23 (자동 체인, run_pilot_post.sh) — 파일럿 계산 완료 11:26, npz 600/600
```
loaded past 300 / future 300 member-years; main-stem cells 185; river cells (>= 10000 km2) 1129
fixed-tau closure sumC/Vwin: past 1.033+-0.095, future 1.039+-0.174
SOURCE centroid past (39.31N,89.91W) -> future (38.59N,88.92W): shift 117 km (member spread past lat sd 0.06, lon sd 0.17)
tributary shares (% of peak-window water), past -> future:
  trib@(36.9N,89.1W) 0.53Mkm2                 47.6% ->  54.2%  (member sd 1.0/2.5)
  trib@(38.9N,90.1W) 0.44Mkm2                 14.4% ->  10.0%  (member sd 0.8/0.6)
  trib@(33.9N,91.1W) 0.41Mkm2                  7.6% ->   7.4%  (member sd 0.5/0.7)
  trib@(41.1N,95.9W) 0.22Mkm2                  3.2% ->   1.9%  (member sd 0.1/0.2)
  trib@(47.9N,103.9W) 0.18Mkm2                 2.8% ->   2.3%  (member sd 0.3/0.2)
  trib@(39.1N,94.6W) 0.15Mkm2                  1.0% ->   1.0%  (member sd 0.1/0.1)
  main stem + direct                           2.5% ->   2.4%
BOTTLENECK (earliest crossing among river cells) years with a crossing: past 300/300, future 300/300
BOTTLENECK centroid past (41.56N,98.93W) -> future (42.09N,100.24W): shift 123 km
  top past: (35.62N,104.38W) 1.5% up=16k km2; (38.38N,105.12W) 1.4% up=10k km2; (40.12N,101.88W) 1.1% up=12k km2; (36.88N,99.38W) 1.1% up=27k km2; (45.88N,110.12W) 1.0% up=13k km2
  top future: (35.88N,104.38W) 1.4% up=11k km2; (46.38N,108.62W) 1.1% up=10k km2; (46.38N,108.38W) 0.9% up=11k km2; (39.62N,104.88W) 0.9% up=11k km2; (38.38N,105.12W) 0.9% up=10k km2
GAUGE annual-max Q: past 36670 -> future 36680 m3/s (+0.0%); peak day-of-year past 128 -> future 125
saved /home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23/pilot_figA_source_map.png
saved /home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23/pilot_figB_bottleneck_map.png
saved /home/juen0828/RS12_Flood_origin/cc_output/result/2026.10.23/pilot_figB2_exceed_any_map.png
saved figC
```
- 그림: result/2026.10.23/pilot_figA_source_map.png, pilot_figB_bottleneck_map.png, pilot_figB2_exceed_any_map.png, pilot_figC_summary.png; 수치 캐시 pilot_summary.npz
- 재개 시: 위 수치로 판정(발원 중심 이동 > 200 km? 병목 이동 뚜렷? 유량 변화 %와 비례?) → 사용자에게 보고 후 갠지스·머리달링 확장 여부 결정.

### 2026-10-23 파일럿 보충 집계 (p0_12_groups.py, p0_11 UPMIN=100000)
- 지류 묶음 발원 몫(%): 오하이오 47.6→54.2(+6.6, 10/10 멤버 동일 부호), 상류 미시시피 14.4→10.0(−4.4, 10/10), 미주리 18.2→14.6(−3.6, 10/10), 아칸소 7.6→7.4(불변), 하류 직접 12.2→13.8.
  주의: p0_11 기본 라벨링은 uparea 최대 경로를 본류로 잡아 미주리가 "본류"로 들어감 → 묶음은 p0_12 결과를 쓸 것.
- 게이지 연최대 유량 36,670→36,680 m³/s(+0.0%), 피크 일자 128→125일. **크기는 그대로, 출발점은 옮김.**
- 병목(≥10만 km² 대하천, 상향 교차 최초 셀): 과거는 미주리 본류 사우스다코타·네브래스카 구간(42.9N 97.9W 등 5%대)에 집중, 미래는 상류 미시시피(44.6N 92.9W 3.4%)·플랫으로 분산. 묶음 몫 미주리 51→46%, 상류 미시시피 29→36%, 오하이오 5.6→1.6%. 중심 이동 22 km(≥1만 km² 기준은 123 km이나 빈도 ≤1.5%로 흩어짐).
- 판정(1차): 발원 이동 117 km는 200 km 문턱 미만이나 지류 재배분은 10/10 멤버 일치·유량 변화 0%라 "비례 아님" 조건 충족. 병목은 정의 민감(uparea 문턱) → 정의 확정 필요. 그림: pilot_figB_bottleneck_map_up100k.png 등 _up100k 접미.
- 남은 일: (계산) 병목 정의 안정화(교차 최초 vs 초과 지속·유량 가중), τ 민감도(0.5/1.5 m/s), rivhgt ±20%; (사용자 결정) 갠지스·머리달링 확장 여부, 원인 변수(H2OSNO·RAIN) 다운로드.

### 2026-10-23 보충: "왜 117 km밖에 안 움직이나" 분해
- 셀 단위로 자리를 옮긴 피크 물 비율 = 12.4% (지류 묶음 단위 8.2%).
- 지류 무게중심이 유역 중심에서 떨어진 거리: 미주리 1117 km, 아칸소 687 km, 오하이오 571 km, 상류 미시시피 438 km, 하류 본류 386 km.
- 8%의 물이 ~1000 km 떨어진 지류 사이를 옮기면 중심은 ~100 km 움직임 → 117 km는 지류 재배분(오하이오 +6.6 pp)과 정합. 중심 이동은 유역 평균이라 희석되는 지표.
- 지류 안쪽 이동: 미주리 114 km, 상류 미시시피 86 km, 오하이오·아칸소 35 km, 하류 11 km (방향 미계산).
- 해석: 미시시피는 이미 오하이오(48%)·봄비 주도 유역이라 옮길 여지가 작음. 눈 주도 지류(상류 미시시피+미주리)가 32.6→24.6%로 1/4 감소한 것이 본 신호. 중심 km 대신 "눈 주도 지류 분담률" 같은 분담 지표를 헤드라인으로 쓰는 게 맞음 → 사용자 결정.

### 2026-10-23 보충 2: 신호가 보이는 그림 (p0_13_slope_chart.py → pilot_figD_slope_snowshare.png)
- 왼쪽: 멤버별 지류 분담 기울기 그림(과거→미래). 오하이오 47→54%, 미주리 18→15%, 상류 미시시피 15→10%, 10멤버 전부 같은 방향.
- 오른쪽: 연도별(300 멤버-년) 눈 주도 지류 분담 히스토그램. 평균 32.9±1.3 → 24.5±1.3%(멤버 간 sd). 눈 분담 >40%인 해 22% → 1%, <20%인 해 7% → 23%.
- 헤드라인 후보: "미시시피 홍수는 같은 크기로 오지만 피크 물의 출발점이 눈 지류에서 비 지류로 옮겼다 — 눈이 주도한 홍수 해(>40%)가 5년에 1번에서 100년에 1번으로."
