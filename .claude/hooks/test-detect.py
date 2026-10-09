"""게이트 훅 탐지기 시험 — `python3 .claude/hooks/test-detect.py`

훅이 명령을 **실행 위치에서만** 잡는지 본다. 첫 판은 명령문 어디에나 있는
문자열을 잡아서, 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 막혔다.
탐지기를 손대면 이 파일을 먼저 돌린다.

⚠ 실제 저장소가 아니라 **임시 git 저장소**에서 돌린다 (2026-08-27).
  첫 판은 `cwd`로 실제 저장소를 넘겨 진짜 마커(`.claude/.pr-review-ok`)를 읽었다 —
  리뷰 직후처럼 마커가 HEAD와 같으면 차단 케이스 7개가 **전부 통과해 버렸다.**
  `npm run check`의 결과가 게이트 상태에 따라 달라지는 검사는 검사가 아니다.
  그래서 마커 세 상태(없음 · HEAD와 같음 · 다름)를 각각 만들어 본다.

⚠ 워크트리 케이스(`WT_CASES`, 이슈 #111) — 세션 cwd는 메인 체크아웃에 두고 명령의 `cd`·`--head`가
  워크트리 브랜치를 PR로 여는 경우다. 훅이 cwd의 HEAD·마커만 읽던 판에서 A·B·H·I·L·M은 **리뷰하지 않은
  브랜치를 통과시켰고**(메인 마커가 메인 HEAD와 같다는 이유로), C~G·K·N은 리뷰를 마쳤는데도 막혔다.
  M은 고친 첫 판에서도 열렸다 — `--head`를 찾는 범위를 괄호에서 끊어 `$(…)` 뒤의 값을 못 봤다(리뷰에서 찾음).
  O도 고친 첫 판에서 열렸다 — 닫힌 서브셸의 `cd`를 계속 따라가 리뷰된 워크트리의 마커로 판정했다(리뷰에서 찾음).
  워크트리 경로에 공백을 넣어 따옴표 친 `cd` 경로도 함께 본다.
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

# 워크트리 — (이름, 메인 마커, 워크트리 마커, 명령, 기대 rc). 이슈 #111.
# 세션 cwd는 메인이고, 명령의 `cd`·`--head`가 워크트리 브랜치를 PR로 연다.
# `<WT>`는 워크트리 절대 경로(공백 포함)로 바뀐다.
WT_CASES = [
    ("WT-A cd 워크트리 · 워크트리 미리뷰", "HEAD", None, 'cd "<WT>" && ' + G + " --base main", 2),
    ("WT-B --head 워크트리 · 미리뷰", "HEAD", None, G + " --head wt --base main", 2),
    ("WT-C cd 워크트리 · 리뷰됨", None, "HEAD", 'cd "<WT>" && ' + G + " --base main", 0),
    ("WT-D --head 워크트리 · 리뷰됨", None, "HEAD", G + " --base main --head wt", 0),
    ("WT-E 상대 경로 cd · 리뷰됨", None, "HEAD", 'cd "../wt dir" && git push && ' + G, 0),
    ("WT-F 앞줄의 cd · 리뷰됨", None, "HEAD", 'cd "<WT>"\ngit push\n' + G, 0),
    ("WT-G --head=소유자:브랜치 · 리뷰됨", None, "HEAD", G + " --head=me:wt", 0),
    ("WT-H 워크트리 마커가 메인 SHA", "HEAD", "OTHER", 'cd "<WT>" && ' + G, 2),
    ("WT-I cd 대상을 못 푼다($변수)", "HEAD", "HEAD", 'cd "$WT" && ' + G, 2),
    ("WT-J cd 없음 · 메인 리뷰됨(기존 동작)", "HEAD", None, G + " --base main", 0),
    # 실제로 PR을 여는 모양 — 본문 heredoc이 따옴표 안에 있고, 본문에 따옴표와 명령 문자열이 섞인다
    ("WT-K 실사용 모양 · 리뷰됨", None, "HEAD",
     'git push -u origin wt && ' + G + ' --base main --head wt --title "제목 \'따옴표\'" '
     '--body "$(cat <<\'EOF\'\n본문의 ' + G + ' 와 it\'s\nEOF\n)"', 0),
    ("WT-L 실사용 모양 · 미리뷰", "HEAD", None,
     'git push -u origin wt && ' + G + ' --base main --head wt --title "제목" '
     '--body "$(cat <<\'EOF\'\n본문\nEOF\n)"', 2),
    # 따옴표 없는 `$(…)` 뒤의 --head — 괄호에서 토막을 끊으면 --head를 못 보고 cwd(메인)로 판정해 열렸다
    ("WT-M 따옴표 없는 $(…) 뒤 --head · 미리뷰", "HEAD", None, G + " --body $(cat f) --head wt", 2),
    ("WT-N 따옴표 없는 $(…) 뒤 --head · 리뷰됨", None, "HEAD", G + " --body $(cat f) --head wt", 0),
    # 서브셸 안의 cd는 닫히면 끝난다 — PR은 메인 체크아웃의 브랜치다. 서브셸을 안 따지면
    # 리뷰된 워크트리의 마커로 판정해 메인의 미리뷰 브랜치가 열렸다
    ("WT-O 닫힌 서브셸의 cd · 메인 미리뷰", None, "HEAD", '(cd "<WT>" && git push) && ' + G, 2),
    ("WT-P 서브셸 안의 cd 뒤 PR · 리뷰됨", None, "HEAD", '(cd "<WT>" && ' + G + ")", 0),
]


def make_worktree_pair(main_marker, wt_marker):
    """메인 체크아웃 + 워크트리 하나(브랜치 `wt`, 메인보다 커밋 하나 앞). 이슈 #111.

    세션 cwd는 메인에 두고 명령 안의 `cd`·`--head`로 워크트리 브랜치를 가리키는 경우를 만든다.
    main_marker / wt_marker: None(없음) · "HEAD"(그 체크아웃의 HEAD) · "OTHER"(상대 체크아웃의 HEAD).
    반환: (지울 부모 임시 디렉터리, 메인 경로, 워크트리 경로)
    """
    parent = tempfile.mkdtemp(prefix="gate-wt-")
    main_dir = os.path.join(parent, "main")
    wt_dir = os.path.join(parent, "wt dir")  # 공백 — 따옴표 친 cd 경로를 시험한다
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(g + ["init", "-q", "-b", "main", main_dir], check=True)
    subprocess.run(g + ["-C", main_dir, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
    subprocess.run(g + ["-C", main_dir, "worktree", "add", "-q", "-b", "wt", wt_dir], check=True)
    subprocess.run(g + ["-C", wt_dir, "commit", "-q", "--allow-empty", "-m", "work"], check=True)

    def head(d):
        return subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    heads = {main_dir: head(main_dir), wt_dir: head(wt_dir)}
    for d, other, m in ((main_dir, wt_dir, main_marker), (wt_dir, main_dir, wt_marker)):
        if m is None:
            continue
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        with open(os.path.join(d, MARKER), "w", encoding="utf-8") as f:
            f.write(heads[d] if m == "HEAD" else heads[other])
    return parent, main_dir, wt_dir


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

        # 첫 판은 cwd의 HEAD·마커만 읽어서 A·B가 **열렸다**(메인 마커가 메인 HEAD와 같다는 이유로)
        # — 게이트가 열리는 방향이다. C~G는 리뷰를 마친 워크트리인데도 막혔다.
        for label, mm, wm, cmd, want in WT_CASES:
            parent, main_dir, wt_dir = make_worktree_pair(mm, wm)
            try:
                rc = run(cmd.replace("<WT>", wt_dir), main_dir)
            finally:
                shutil.rmtree(parent, ignore_errors=True)
            ok = rc == want
            fails += not ok
            print(("  OK  " if ok else "  !!  ") + "%s — %-30s rc=%s"
                  % ("통과해야 함" if want == 0 else "차단해야 함", label, rc))
    finally:
        for d in (no_marker, reviewed, stale):
            shutil.rmtree(d, ignore_errors=True)

    print("\n실패 %d건" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
