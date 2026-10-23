# RS12_Flood_origin — research_log.md (KST)

모든 작업을 한국 시각(KST) 기준으로 시간순 기록한다. 항목 형식: `### YYYY-MM-DD HH:MM KST — 제목` 뒤에 무엇을·왜·결과·다음.
세션 종료 시 Stop hook(`.claude/hooks/research_log_commit.sh`)이 이 파일의 변경을 확인해 자동 `git commit` 한다(제목 = 마지막 `###` 항목).
연구 내용의 캐노니컬 로그는 `cc_output/plan/2026.10.23/RS12_progress.md`; 이 파일은 그 위의 작업 일지(시간·파일·커밋 단위)다.

### 2026-10-23 (오전~13:00 KST) — 이전 세션 요약 (소급 기재)
- 질량 닫힘 검증 p0_01~06 완료: 게이지 32.125N 91.125W, 연간 잔차 +0.03%, 음수 runoff clip 필수, 분기로 델타 284 km³/yr 누출.
- 파일럿 p0_10 + run_pilot.sh: 10멤버 × (1952–81, 2071–2100) 600 npz 완료 11:25, 후처리 11:26 (driver.log POST DONE).
- 집계·그림 p0_11/p0_12/p0_13: 그림 A/B/B2/C(+_up100k)/D. 결과 한 문장: 홍수 크기 +0%, 피크 물의 8%가 눈 지류→비 지류로 이동; 눈 분담 >40% 해 5년 1번 → 100년 1번.
- overleaf_ppt/: beamer 요약서 main.tex + TikZ 그림 9장(figures/fig_*.tex, build/ 에 pdf·png).
- 상세는 cc_output/plan/2026.10.23/RS12_progress.md.

### 2026-10-23 13:40 KST — /init: CLAUDE.md 보강, research_log·git·Stop hook 도입
- 무엇: CLAUDE.md를 /init 양식으로 재작성(실행 명령·스크립트 체인·데이터 형식·함정 추가). git 저장소 초기화(.gitignore: pilot/ npz 600개·__pycache__ 제외).
- 왜: 사용자 지시 — "research_log.md를 만들어 KST 기준으로 모든 작업 기록 + git commit, 메모리에 기록하고 hook으로 상시화".
- 결과: `.claude/settings.json` Stop hook → 작업 파일이 바뀌었는데 로그가 없으면 종료 차단, 로그가 있으면 자동 커밋. 메모리 `feedback_research_log_git_commit.md` 저장.
- 다음: 병목 정의 안정화·τ 민감도(계산), 헤드라인 지표·두 번째 유역·원인 변수 다운로드(사용자 결정).
