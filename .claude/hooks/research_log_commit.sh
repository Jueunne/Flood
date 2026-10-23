#!/bin/bash
# Stop hook (project RS12_Flood_origin).
#  - research_log.md unchanged but other files changed -> block stop, ask Claude to log the work (KST) first.
#  - research_log.md changed -> git add -A && git commit (subject = latest "### " heading of the log).
#  - nothing changed -> no-op.
ROOT=/home/juen0828/RS12_Flood_origin
LOG=research_log.md
cd "$ROOT" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
INPUT=$(cat)
ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ -z "$(git status --porcelain)" ] && exit 0
if [ -z "$(git status --porcelain -- "$LOG")" ]; then
  # log not touched this stop
  if [ "$ACTIVE" = "true" ]; then exit 0; fi   # avoid infinite block loop
  jq -n --arg r "작업 파일이 바뀌었는데 $LOG 에 기록이 없음. $LOG 끝에 '### $(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M KST') — <제목>' 항목으로 이번 작업(무엇을·왜·결과·다음)을 적은 뒤 종료할 것. 커밋은 hook이 자동으로 함." \
     '{decision:"block", reason:$r}'
  exit 0
fi
SUBJ=$(grep -E '^### ' "$LOG" | tail -1 | sed 's/^### //')
[ -z "$SUBJ" ] && SUBJ="research_log update $(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M KST')"
git add -A >/dev/null 2>&1
git -c user.name="$(git config user.name || echo juen0828)" commit -q -m "$SUBJ" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01FS1U2uKErmWvsLY4nswBAN" >/dev/null 2>&1
H=$(git rev-parse --short HEAD)
jq -n --arg m "git commit $H: $SUBJ" '{systemMessage:$m}'
exit 0
