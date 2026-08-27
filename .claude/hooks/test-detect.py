"""게이트 훅 탐지기 시험 — `python3 .claude/hooks/test-detect.py`

훅이 명령을 **실행 위치에서만** 잡는지 본다. 첫 판은 명령문 어디에나 있는
문자열을 잡아서, 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 막혔다.
탐지기를 손대면 이 파일을 먼저 돌린다.

⚠ 실제 저장소가 아니라 **임시 git 저장소**에서 돌린다 (2026-08-27).
  첫 판은 `cwd`로 실제 저장소를 넘겨 진짜 마커(`.claude/.pr-review-ok`)를 읽었다 —
  리뷰 직후처럼 마커가 HEAD와 같으면 차단 케이스 7개가 **전부 통과해 버렸다.**
  `npm run check`의 결과가 게이트 상태에 따라 달라지는 검사는 검사가 아니다.
  그래서 마커 세 상태(없음 · HEAD와 같음 · 다름)를 각각 만들어 본다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.abspath(os.path.join(os.path.dirname(__file__), "pr-review-gate.py"))
MARKER = ".claude/.pr-review-ok"


def make_repo(marker):
    """커밋 하나짜리 임시 저장소. marker: None(없음) · "HEAD"(같음) · 그 밖의 문자열(다름)."""
    d = tempfile.mkdtemp(prefix="gate-fixture-")
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(g + ["init", "-q", "-b", "main", d], check=True)
    subprocess.run(g + ["-C", d, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    if marker is not None:
        head = subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
        os.makedirs(os.path.join(d, ".claude"))
        with open(os.path.join(d, MARKER), "w", encoding="utf-8") as f:
            f.write(head if marker == "HEAD" else marker)
    return d


G = "gh pr " + "create"  # 이 파일 자체가 게이트에 걸리지 않게 쪼개 둔다

BLOCK = [
    ("맨몸", G + " --base main"),
    ("체인 뒤", "git push -u origin br && " + G + " --fill"),
    ("heredoc 여는 줄", G + " --body-file - <<'BODY'\n본문\nBODY"),
    ("줄바꿈 뒤", "git push\n" + G + " --base main"),
    ("세미콜론 뒤", "npm run check; " + G),
    # 환경변수 접두 — 첫 판이 놓쳤다. gh가 줄머리도 구분자 뒤도 아니게 된다
    ("환경변수 접두", "GH_TOKEN=xxx " + G + " --base main"),
    ("환경변수 둘 + 체인", "git push && GH_HOST=github.com GH_TOKEN=x " + G),
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


def run(cmd, root):
    payload = json.dumps({"tool_input": {"command": cmd}, "cwd": root})
    p = subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, text=True
    )
    return p.returncode


def main():
    fails = 0
    no_marker = make_repo(None)
    reviewed = make_repo("HEAD")
    stale = make_repo("0000000000000000000000000000000000000000")
    try:
        for label, cmd in BLOCK:
            rc = run(cmd, no_marker)
            ok = rc == 2
            fails += not ok
            print(("  OK  " if ok else "  !!  ") + "차단해야 함 (마커 없음) — %-22s rc=%s" % (label, rc))

        for label, cmd in PASS:
            rc = run(cmd, no_marker)
            ok = rc == 0
            fails += not ok
            print(("  OK  " if ok else "  !!  ") + "통과해야 함 — %-22s rc=%s" % (label, rc))

        # 마커 상태 — 탐지가 아니라 판정 쪽. 같으면 열리고, 다르면(리뷰 뒤 커밋이 쌓임) 막힌다.
        rc = run(BLOCK[0][1], reviewed)
        ok = rc == 0
        fails += not ok
        print(("  OK  " if ok else "  !!  ") + "통과해야 함 — %-22s rc=%s" % ("마커 == HEAD", rc))
        rc = run(BLOCK[0][1], stale)
        ok = rc == 2
        fails += not ok
        print(("  OK  " if ok else "  !!  ") + "차단해야 함 — %-22s rc=%s" % ("마커 != HEAD", rc))
    finally:
        for d in (no_marker, reviewed, stale):
            shutil.rmtree(d, ignore_errors=True)

    print("\n실패 %d건" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
