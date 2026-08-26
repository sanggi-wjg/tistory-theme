"""게이트 훅 탐지기 시험 — `python3 .claude/hooks/test-detect.py`

훅이 명령을 **실행 위치에서만** 잡는지 본다. 첫 판은 명령문 어디에나 있는
문자열을 잡아서, 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 막혔다.
탐지기를 손대면 이 파일을 먼저 돌린다.
"""
import json
import subprocess
import sys

import os

HOOK = os.path.abspath(os.path.join(os.path.dirname(__file__), "pr-review-gate.py"))
ROOT = os.path.abspath(os.path.join(os.path.dirname(HOOK), "..", ".."))

G = "gh pr " + "create"  # 이 파일 자체가 게이트에 걸리지 않게 쪼개 둔다

BLOCK = [
    ("맨몸", G + " --base main"),
    ("체인 뒤", "git push -u origin br && " + G + " --fill"),
    ("heredoc 여는 줄", G + " --body-file - <<'BODY'\n본문\nBODY"),
    ("줄바꿈 뒤", "git push\n" + G + " --base main"),
    ("세미콜론 뒤", "npm run check; " + G),
]

PASS = [
    ("heredoc 본문 안 (첫 오탐)", "cat > a.md <<'MD'\n" + G + "는 훅이 막는다\nMD"),
    ("작은따옴표 안", "grep '" + G + "' CLAUDE.md"),
    ("큰따옴표 안", 'echo "' + G + ' 를 쓴다"'),
    ("python heredoc 안", "python3 - <<'PY'\ns='" + G + "'\nPY"),
    ("무관한 명령", "gh pr list --state open"),
    ("view", "gh pr view 29 --json state"),
    ("npm", "npm run check"),
]


def run(cmd):
    payload = json.dumps({"tool_input": {"command": cmd}, "cwd": ROOT})
    p = subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, text=True
    )
    return p.returncode


fails = 0
for label, cmd in BLOCK:
    rc = run(cmd)
    ok = rc == 2
    fails += not ok
    print(("  OK  " if ok else "  !!  ") + "차단해야 함 — %-22s rc=%s" % (label, rc))

for label, cmd in PASS:
    rc = run(cmd)
    ok = rc == 0
    fails += not ok
    print(("  OK  " if ok else "  !!  ") + "통과해야 함 — %-22s rc=%s" % (label, rc))

print("\n실패 %d건" % fails)
sys.exit(1 if fails else 0)
