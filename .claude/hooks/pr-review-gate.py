#!/usr/bin/env python3
"""PR 생성 전 코드리뷰 게이트 — PreToolUse(Bash) 훅.

PR 생성 명령을 가로채, **지금 HEAD에 대한 리뷰가 끝났는지**만 본다.
끝나 있으면 통과시키고, 아니면 exit 2로 막고 무엇을 하라고 알려 준다.

왜 훅인가 — 이 저장소의 사이클은 CLAUDE.md에 적혀 있지만, 적혀 있는 것은
지켜지지 않을 수 있다. `npm run check`는 통과해야 다음이 안 되는 구조라
강제되지만, 리뷰에는 그런 구조가 없었다.

마커 파일: `.claude/.pr-review-ok` — 내용은 리뷰가 통과한 커밋 SHA 하나.
`/pr-review-gate` 스킬이 **차단 항목 0일 때만** 찍는다. 손으로 찍지 않는다.
찍는 순간 "이 커밋을 읽었고 문제가 없다"는 뜻이 되고, 그 문장이 거짓이면
게이트는 있는 것이 없는 것보다 나쁘다 — 다음 사람이 초록불을 믿는다.

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그
사고를 냈다 — 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 게이트에 막혔다.
명령을 **실행 위치**에서만 본다: 따옴표 안과 heredoc 본문을 걷어낸 뒤,
줄머리나 셸 구분자 바로 뒤에 오는 것만 명령으로 친다.
"""
import json
import os
import re
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
CMD = re.compile(r"(?:^|[;&|(\n])\s*gh\s+pr\s+" + "create" + r"\b")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
MARKER = ".claude/.pr-review-ok"


def strip_heredocs(command):
    """heredoc 본문을 걷어낸다.

    `... --body-file - <<'BODY'` 형태에서 **본문만** 지운다. 명령 자체는
    heredoc 여는 줄에 그대로 남으므로 탐지가 죽지 않는다.
    """
    lines = command.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = HEREDOC.search(line)
        i += 1
        if not m:
            continue
        tag = m.group(2)
        while i < len(lines) and lines[i].strip() != tag:
            i += 1
        i += 1  # 종료 태그 줄도 버린다
    return "\n".join(out)


def strip_quoted(command):
    """따옴표로 감싼 구간을 지운다. `grep "gh pr …"` 같은 언급을 걸러낸다."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", command)


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 막지 않는다. 게이트가 사고를 만들면 안 된다

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not CMD.search(strip_quoted(strip_heredocs(command))):
        return 0

    root = payload.get("cwd") or os.getcwd()
    try:
        os.chdir(root)
    except OSError:
        return 0

    head = git("rev-parse", "HEAD")
    if not head:
        return 0  # 저장소가 아니다

    try:
        with open(os.path.join(root, MARKER), encoding="utf-8") as f:
            reviewed = f.read().strip()
    except OSError:
        reviewed = ""

    if reviewed == head:
        return 0

    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    stat = git("diff", "--stat", "main...HEAD") or "(main과의 차이를 못 읽었다)"
    if reviewed:
        why = "마커는 %s에 찍혀 있는데 HEAD는 %s다 — 리뷰 뒤에 커밋이 더 쌓였다." % (
            reviewed[:8],
            head[:8],
        )
    else:
        why = "이 저장소에 리뷰 마커가 없다 — 이 브랜치는 아직 리뷰되지 않았다."

    sys.stderr.write(
        "PR 생성이 게이트에 막혔다. %s\n\n"
        "브랜치: %s (HEAD %s)\n%s\n\n"
        "`/pr-review-gate` 스킬을 먼저 실행하라. 리뷰는 `npm run check`와 보는 축이 다르다 —\n"
        "린트는 규칙의 **존재**를 보고, 리뷰는 그 규칙이 이 변경에서 **실제 조건을\n"
        "재현하는지**를 본다. 차단 항목이 0이 되면 스킬이 마커를 찍고, 그때 통과한다.\n\n"
        "게이트를 건너뛸 이유가 있으면 사용자에게 확인받아라. 마커를 손으로 찍지 마라.\n"
        % (why, branch, head[:8], stat)
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
