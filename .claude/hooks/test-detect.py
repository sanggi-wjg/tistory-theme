"""게이트 훅 시험 — `python3 .claude/hooks/test-detect.py`

훅이 PR 생성을 **셸 낱말 단위로** 잡는지(문서·문자열 속 언급은 안 잡는지), 그리고 PR이 될 커밋을
제대로 판정하는지 본다. 탐지기·판정을 손대면 이 파일에 케이스를 먼저 더하고 돌린다.

⚠ 실제 저장소가 아니라 **임시 git 저장소**에서 돌린다 (2026-08-27).
  첫 판은 `cwd`로 실제 저장소를 넘겨 진짜 마커(`.claude/.pr-review-ok`)를 읽었다 —
  리뷰 직후처럼 마커가 HEAD와 같으면 차단 케이스 7개가 **전부 통과해 버렸다.**
  `npm run check`의 결과가 게이트 상태에 따라 달라지는 검사는 검사가 아니다.
  그래서 마커 상태(없음 · HEAD와 같음 · 다름)를 각각 만들어 본다. 픽스처마다 **원격(bare)**을 두고
  푸시해 둔다 — 훅이 원격 브랜치의 끝도 대조하기 때문이다(이슈 #111). 추적 ref가 아니라 원격에 직접
  묻는다(이슈 #114) — 그래서 남이 원격을 민 경우·추적 ref만 없는 경우를 원격 상태로 따로 만든다.

⚠ 이슈 #111에서 케이스가 16 → 100여 개로 늘었다. 거의 전부 **옛 훅에 돌려 새는 것을 확인한** 모양이다
  (주석 속 `don't`가 PR 명령을 가림, `git commit -am x && <PR 생성>`, `url="$(<PR 생성>)"`, `"gh" pr create` …).
  훅을 고치는 동안 「따라가는 형태」를 넓히는 판(cd 추적)과 「허용하는 모양」을 늘리는 판(같은 호출 안의
  git 하위 명령 허용 목록)이 차례로 샜다 — 내 리뷰가 다섯, 빌트인 코드 리뷰 다섯 번이 열·34·23·10·8을 짚었다.
  그래서 훅은 **PR 생성을 그 호출의 유일한 명령으로**(앞에 `cd <경로>` 하나만) 요구하고, 원격 추적 ref까지
  대조한다. 기대값이 0에서 2로 바뀐 실사용 모양(푸시와 PR을 한 줄에)은 그래서다 — 푸시는 따로 한다.

⚠ 이슈 #114에서 「알려진 한계」 중 고칠 수 있는 넷에 케이스 25개를 더했다 — 스크립트 파일 속 PR 생성, `gh api`,
  `--repo`·`GH_REPO`, 낡은 추적 ref. 옛 훅에 돌려 16건 실패(15건이 막아야 할 것을 통과)를 확인하고 고쳤다.
  리뷰에서 7개를 더 더했다(자기를 source하는 스크립트의 오탐, `-euo pipefail`, 스크립트 안의 `cd`·자기 디렉터리,
  `timeout 5m`, 전체 URL `gh api`, URL로 `push -u`한 브랜치) — 첫 커밋의 훅에 돌려 7건 모두 실패를 확인했다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.abspath(os.path.join(os.path.dirname(__file__), "pr-review-gate.py"))
MARKER = ".claude/.pr-review-ok"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]


def sh(*args, **kw):
    return subprocess.run(GIT + list(args), check=True, capture_output=True, text=True, **kw).stdout.strip()


def head_of(d, ref="HEAD"):
    return sh("-C", d, "rev-parse", ref)


def write_marker(d, sha):
    os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
    with open(os.path.join(d, MARKER), "w", encoding="utf-8") as f:
        f.write(sha)


def make_repo(marker):
    """커밋 하나짜리 임시 저장소 + 원격(푸시·추적 완료). marker: None · "HEAD" · 그 밖의 문자열."""
    parent = tempfile.mkdtemp(prefix="gate-fixture-")
    # 원격 경로의 끝 두 마디가 `o/r` — `--repo o/r`가 이 저장소, `--repo evil/r`가 남의 저장소다(이슈 #114)
    d, origin = os.path.join(parent, "repo"), os.path.join(parent, "o", "r.git")
    os.makedirs(os.path.dirname(origin))
    sh("init", "-q", "--bare", origin)
    sh("init", "-q", "-b", "main", d)
    sh("-C", d, "commit", "-q", "--allow-empty", "-m", "init")
    sh("-C", d, "remote", "add", "origin", origin)
    sh("-C", d, "push", "-q", "-u", "origin", "main")
    if marker is not None:
        write_marker(d, head_of(d) if marker == "HEAD" else marker)
    write_scripts(d)
    return parent, d


def write_scripts(d):
    """셸로 돌리는 스크립트 파일 — 추적하지 않는 파일이라 HEAD는 그대로다(이슈 #114)."""
    files = {
        "pr.sh": G + " --fill\n",
        "outer.sh": "echo start\nsource pr.sh\n",
        "sub/pr2.sh": G + " --fill\n",
        "outer-cd.sh": "cd sub && bash pr2.sh\n",
        "sub/rel.sh": 'cd "$(dirname "$0")"\nbash pr2.sh\n',
        "self.sh": "[ -n \"$DONE\" ] || { DONE=1; source self.sh; }\necho hi\n",
        "mention.sh": 'echo "' + G + ' 는 게이트가 막는다"\n',
        "pr-run": "#!/usr/bin/env bash\nset -e\n" + G + " --fill\n",
        "tool.py": "#!/usr/bin/env python3\nimport subprocess\nsubprocess.run('" + G + "'.split())\n",
    }
    os.makedirs(os.path.join(d, "sub"), exist_ok=True)
    for name, body in files.items():
        f = os.path.join(d, name)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.chmod(f, 0o755)


def make_worktree_pair(main_marker, wt_marker, remote="pushed"):
    """메인 체크아웃 + 워크트리 하나(브랜치 `wt`, 메인보다 커밋 하나 앞) + 원격. 이슈 #111.

    세션 cwd는 메인에 두고 명령 안의 `cd`·`--head`로 워크트리 브랜치를 가리키는 경우를 만든다.
    main_marker / wt_marker: None(없음) · "HEAD"(그 체크아웃의 HEAD) · "OTHER"(상대 체크아웃의 HEAD).
    remote: "pushed"(둘 다 푸시) · "unpushed"(wt를 안 푸시) · "diverged"(원격 wt가 main의 커밋) ·
      "pushed-elsewhere"(남이 원격 wt를 앞으로 밈, 추적 ref는 낡음) · "pushed-untracked"(추적 ref만 없음) …
    반환: (지울 부모 임시 디렉터리, 메인 경로, 워크트리 경로)
    """
    parent = tempfile.mkdtemp(prefix="gate-wt-")
    main_dir = os.path.join(parent, "main")
    wt_dir = os.path.join(parent, "wt dir")  # 공백 — 따옴표 친 cd 경로를 시험한다
    origin = os.path.join(parent, "origin.git")
    sh("init", "-q", "--bare", origin)
    sh("init", "-q", "-b", "main", main_dir)
    sh("-C", main_dir, "commit", "-q", "--allow-empty", "-m", "init")
    sh("-C", main_dir, "remote", "add", "origin", origin)
    sh("-C", main_dir, "push", "-q", "-u", "origin", "main")
    sh("-C", main_dir, "worktree", "add", "-q", "-b", "wt", wt_dir)
    sh("-C", wt_dir, "commit", "-q", "--allow-empty", "-m", "work")
    if remote == "pushed":
        sh("-C", wt_dir, "push", "-q", "-u", "origin", "wt")
    elif remote == "renamed":
        sh("-C", wt_dir, "push", "-q", "-u", "origin", "wt:feature")
    elif remote == "tracks-main":  # origin/main에서 딴 워크트리 — 추적은 main, 푸시는 같은 이름
        sh("-C", wt_dir, "push", "-q", "origin", "wt")
        sh("-C", wt_dir, "branch", "-q", "--set-upstream-to=origin/main")
    elif remote == "pushed-elsewhere":  # 푸시 뒤 다른 클론이 원격 wt를 앞으로 민다 — 로컬 추적 ref는 낡은 채다
        sh("-C", wt_dir, "push", "-q", "-u", "origin", "wt")
        other = os.path.join(parent, "other")
        sh("clone", "-q", "-b", "wt", origin, other)
        sh("-C", other, "commit", "-q", "--allow-empty", "-m", "someone else")
        sh("-C", other, "push", "-q", "origin", "wt")
    elif remote == "pushed-untracked":  # 원격에는 리뷰한 커밋이 있는데 로컬 추적 ref가 없다
        sh("-C", wt_dir, "push", "-q", "origin", "wt")
        sh("-C", wt_dir, "update-ref", "-d", "refs/remotes/origin/wt")
    elif remote == "diverged":
        sh("-C", wt_dir, "push", "-q", "-u", "origin", "wt")
        sh("-C", main_dir, "push", "-q", "-f", "origin", "main:wt")  # 원격 wt ← main의 (미리뷰) 커밋
        sh("-C", main_dir, "fetch", "-q", "origin")
    heads = {main_dir: head_of(main_dir), wt_dir: head_of(wt_dir)}
    for d, other, m in ((main_dir, wt_dir, main_marker), (wt_dir, main_dir, wt_marker)):
        if m is not None:
            write_marker(d, heads[d] if m == "HEAD" else heads[other])
    return parent, main_dir, wt_dir


G = "gh pr " + "create"  # 이 파일 자체가 게이트에 걸리지 않게 쪼개 둔다

# 마커 없는 저장소에서 막혀야 한다 — 탐지가 PR 생성을 보는가
BLOCK = [
    ("맨몸", G + " --base main"),
    ("체인 뒤", "git push -u origin br && " + G + " --fill"),
    ("heredoc 여는 줄", G + " --body-file - <<'BODY'\n본문\nBODY"),
    ("줄바꿈 뒤", "git push\n" + G + " --base main"),
    ("세미콜론 뒤", "npm run check; " + G),
    # 환경변수 접두 — 둘째 판이 놓쳤다
    ("환경변수 접두", "GH_TOKEN=xxx " + G + " --base main"),
    ("환경변수 둘 + 체인", "git push && GH_HOST=github.com GH_TOKEN=x " + G),
    # 1차 코드 리뷰가 손으로 짚은 탐지 구멍 — 따옴표·주석·here-string·별칭·접두
    ("주석 속 아포스트로피", "git push # don't forget\n" + G + " --fill\necho 'done'"),
    ("이스케이프된 큰따옴표", 'echo \\"; ' + G + '; echo \\"'),
    ("here-string <<<", "cat <<< wt\n" + G + " --fill\nwt"),
    ("별칭 gh pr new", "gh pr " + "new --fill"),
    ("then 뒤", "if true; then " + G + " --fill; fi"),
    ("command 접두", "command " + G + " --fill"),
    ("역슬래시 gh", "\\" + G + " --fill"),
    ("경로 gh", "/usr/bin/" + G + " --fill"),
    ("pr과 create 사이 플래그", "gh pr -R o/r " + "create --fill"),
    # 2차 — 큰따옴표 속 $( )·백틱은 셸이 실행한다, 래퍼, 하이픈 heredoc 태그
    ("큰따옴표 속 $( )", 'url="$(' + G + ' --fill)"'),
    ("echo 속 $( )", 'echo "PR: $(' + G + ' --fill)"'),
    ("백틱", "url=`" + G + " --fill`"),
    ("timeout 래퍼", "timeout 60 " + G + " --fill"),
    ("xargs 래퍼", "echo | xargs " + G + " --fill"),
    ("sudo -u 래퍼", "sudo -u me " + G + " --fill"),
    ("env -i 래퍼", "env -i PATH=/usr/bin " + G + " --fill"),
    ("하이픈 heredoc 태그", "cat <<END-X\nhi\nEND-X\n" + G + " --fill"),
    # 3차 — 낱말을 따옴표·이스케이프로 감싸도 셸에는 같은 낱말이다, ANSI-C 따옴표
    ("따옴표 친 gh", '"gh" pr ' + "create --fill"),
    ("따옴표 친 create", "gh pr 'create' --fill"),
    ("이스케이프 섞인 gh", "g\\h pr " + "create --fill"),
    ("ANSI-C $'\\''", "echo $'\\'' ; " + G + " --fill"),
    ("변수로 gh", "$GH pr " + "create --fill"),
    # 4차 — heredoc 열기를 주석·산술·부분 따옴표 태그에서 잘못 봄, 큰따옴표 -c/eval, 셸에 먹이는 heredoc
    ("주석 속 <<X", "# use <<X here\n " + G + " --fill"),
    ("산술 $((1<<3))", "echo $((1<<3))\n " + G + " --fill"),
    ('부분 따옴표 태그 <<"E"OF', 'cat <<"E"OF\nx\nEOF\n' + G + " --fill"),
    ("역슬래시 태그 <<E\\OF", "cat <<E\\OF\nx\nEOF\n" + G + " --fill"),
    ('bash -c "…"', 'bash -c "' + G + ' --fill"'),
    ('sh -c "cd; …"', 'sh -c "cd /tmp; ' + G + '"'),
    ('eval "…"', 'eval "' + G + ' --fill"'),
    ("bash <<EOF", "bash <<EOF\n" + G + " --fill\nEOF"),
    ("따옴표 없는 heredoc 본문의 $( )", "cat <<EOF\n$(" + G + " --fill)\nEOF"),
]

# 마커 없는 저장소에서 통과해야 한다 — PR 생성이 아니거나 문자열 속 언급이다
PASS = [
    ("heredoc 본문 안 (첫 오탐)", "cat > a.md <<'MD'\n" + G + "는 훅이 막는다\nMD"),
    ("작은따옴표 안", "grep '" + G + "' CLAUDE.md"),
    ("큰따옴표 안", 'echo "' + G + ' 를 쓴다"'),
    ("python heredoc 안", "python3 - <<'PY'\ns='" + G + "'\nPY"),
    ("무관한 명령", "gh pr list --state open"),
    ("view", "gh pr view 29 --json state"),
    ("npm", "npm run check"),
    ("커밋 메시지 속 언급", 'git commit -m "' + G + ' 게이트를 고친다"'),
    # 4차 — 작은따옴표 속 백틱·$( )는 글자다. 이 저장소의 커밋 메시지는 늘 백틱을 쓴다
    ("작은따옴표 커밋 메시지 속 백틱", "git commit -m '`" + G + "` 를 고친다'"),
    ("작은따옴표 속 $( )", "echo '$(" + G + ")'"),
    ("큰따옴표 속 이스케이프 백틱", 'echo "\\`' + G + '\\`"'),
    # 5차 — PR을 만들지 않는 gh 명령의 값이 create·new다, 따옴표 속 언급, 셸 이름이 플래그 값이다
    ("gh pr list --search create", "gh pr list --search create"),
    ("gh pr list --label new", "gh pr list --label new --state open"),
    ("gh pr edit --add-label new", 'gh pr edit 5 --add-label "new"'),
    ("gh pr comment --body new", "gh pr comment 5 --body new"),
    ("gh issue create --label pr --label create", "gh issue create --title x --label pr --label create"),
    ("ANSI-C 본문 속 언급", "gh issue comment 5 --body $'it\\'s fixed\\n" + G + " works'"),
    ("--label sh 뒤 heredoc 본문 속 언급", "gh issue create --label sh --body-file - <<'EOF'\n" + G + "\nEOF"),
]

# 리뷰를 마친 저장소(마커 == HEAD, 원격 추적 ref도 같음) — (이름, 명령, 기대 rc)
REVIEWED_CASES = [
    ("단독 PR 생성", G + " --base main", 0),
    # PR 생성은 그 호출의 유일한 명령이어야 한다 — 같은 호출 안의 다른 명령은 훅이 판정한 뒤에 돈다
    ("같은 호출 안 git commit", "git commit -qam x && " + G, 2),
    ("같은 호출 안 git checkout", "git checkout other && " + G, 2),
    ("git -C . switch", "git -C . switch other && " + G, 2),
    ("source 뒤", "source x.sh && " + G, 2),
    ("명령 인자 속 cd 낱말", "echo cd && " + G, 2),
    ("if 조건의 git commit", "if git commit -qam x; then " + G + "; fi", 2),
    ("경로 git commit", "/usr/bin/git commit -qam x && " + G, 2),
    ("timeout git commit", "timeout 60 git commit -qam x && " + G, 2),
    ("env git commit", "env git commit -qam x && " + G, 2),
    ("git --git-dir 옵션 뒤 commit", "git --git-dir .git commit -qam x && " + G, 2),
    ("git bisect", "git bisect start HEAD HEAD~ && " + G, 2),
    ("git stash branch", "git stash branch x && " + G, 2),
    ("gh pr checkout", "gh pr checkout 3 && " + G, 2),
    ("$( ) 속 git commit", 'x="$(git commit -qam x)" && ' + G, 2),
    ("따옴표 친 git commit", '"git" commit -qam x && ' + G, 2),
    ("git symbolic-ref", "git symbolic-ref HEAD refs/heads/evil && " + G, 2),
    ("npm version", "npm version patch && " + G, 2),
    ("-c remote.origin.push", "git -c remote.origin.push=refs/heads/x:refs/heads/main push origin && " + G, 2),
    ("GIT_DIR 접두", "GIT_DIR=.git " + G, 2),
    ("env -C", "env -C . " + G + " --fill", 2),
    ("--head가 $( )", G + ' --head "$(git branch --show-current)" --fill', 2),
    # 실사용 — 단독이면 열려야 한다(막히면 게이트를 우회하고 싶어진다)
    ("실사용 — 본문 heredoc", G + ' --base main --title "제목 (괄호)" '
     "--body \"$(cat <<'EOF'\n본문 'x' 와 " + G + " 와 git commit\nEOF\n)\"", 0),
    ("실사용 — 앞줄 주석의 아포스트로피", "# don't forget\n" + G + " --fill", 0),
    ("실사용 — 줄 이음", G + " --base main \\\n  --title t \\\n  --fill", 0),
    ("실사용 — cd . || exit 1", "cd . || exit 1; " + G + " --fill", 0),
    ("실사용 — cd -P .", "cd -P . && " + G + " --fill", 0),
    ("실사용 — 변수 제목", G + ' --title "$TITLE" --fill', 0),
    # 둘째·셋째 판에서 0이던 것 — 이제 푸시는 따로 한다
    ("푸시와 한 줄(따로 한다)", "git push -u origin main && " + G + " --fill", 2),
    # 4차 — 따옴표 없는 heredoc 본문의 $( )는 PR 생성 전에 돈다
    ("따옴표 없는 heredoc 본문의 push", G + " --body-file - <<EOF\n$(git push -f origin x:main)\nEOF", 2),
    ("$(cat <<EOF …) 본문의 push", G + ' --body "$(cat <<EOF\n$(git push -f origin x:main)\nEOF\n)"', 2),
    ("--head 소유자:브랜치(포크)", G + " --head=evil:main --fill", 2),
    ("cd X; — cd가 실패해도 PR이 돈다", "cd .; " + G + " --fill", 2),
    # 4차 — 막으면 안 되는 단독 PR 생성
    ("실사용 — 2>&1", G + " --fill 2>&1", 0),
    ("실사용 — cd && … 2>&1", "cd . && " + G + " --fill 2>&1", 0),
    ("실사용 — 작은따옴표 본문의 백틱", G + " --title t --body 'run `npm run check`'", 0),
    ("실사용 — 큰따옴표 본문의 이스케이프 백틱", G + ' --body "run \\`npm\\` ok"', 0),
    ("실사용 — 따옴표 친 heredoc 본문의 백틱·$( )", G + " --body \"$(cat <<'EOF'\n`npm run check` 와 $(x)\nEOF\n)\"", 0),
    # 5차 — 출력을 자르는 파이프, 무해한 gh 환경변수
    ("실사용 — | tail -3", G + " --fill 2>&1 | tail -3", 0),
    ("실사용 — GH_PROMPT_DISABLED=1", "GH_PROMPT_DISABLED=1 " + G + " --fill", 0),
    ("파이프 뒤가 sink가 아니다", G + " --fill | sh", 2),
    # 이슈 #114 — 스크립트 파일 속 PR 생성. 옛 훅은 명령문만 봐서 리뷰한 저장소에서 그냥 열었다
    ("스크립트 파일 bash pr.sh", "bash pr.sh", 2),
    ("bash -x pr.sh", "bash -x pr.sh", 2),
    ("source pr.sh", "source pr.sh", 2),
    (". ./pr.sh", ". ./pr.sh", 2),
    ("셸 shebang 실행 파일", "./pr-run", 2),
    ("스크립트가 source한 스크립트", "bash outer.sh", 2),
    ("cd 뒤 상대 경로 스크립트", "cd sub && bash ../pr.sh", 2),
    ("스크립트 속 언급만", "bash mention.sh", 0),
    ("자기를 source하는 스크립트(깊이 한도로 막지 않는다)", "bash self.sh", 0),
    # 코드 리뷰 — 묶음 끝의 -o, 스크립트 안의 cd·자기 디렉터리, 단위 붙은 timeout
    ("bash -euo pipefail pr.sh", "bash -euo pipefail pr.sh", 2),
    ("스크립트 안의 cd 뒤 스크립트", "bash outer-cd.sh", 2),
    ("스크립트 디렉터리 기준 상대 경로", "bash sub/rel.sh", 2),
    ("timeout 5m bash pr.sh", "timeout 5m bash pr.sh", 2),
    ("python 실행 파일(셸 아님)", "./tool.py", 0),
    ("없는 스크립트", "bash nope.sh", 0),
    # 이슈 #114 — gh api로 여는 PR
    ("gh api -f … pulls(POST)", "gh api repos/o/r/pulls -f title=t -f head=main -f base=main", 2),
    ("gh api -X POST pulls --input", "gh api -X POST 'repos/{owner}/{repo}/pulls' --input b.json", 2),
    ("gh api graphql createPullRequest",
     "gh api graphql -f query='mutation { create" + "PullRequest(input: {}) { clientMutationId } }'", 2),
    ("gh api 전체 URL pulls(POST)", "gh api https://api.github.com/repos/o/r/pulls -f title=t", 2),
    ("gh api pulls 목록", "gh api repos/o/r/pulls --jq '.[].number'", 0),
    ("gh api -X GET pulls -f state", "gh api -X GET repos/o/r/pulls -f state=closed", 0),
    ("gh api pulls/5/comments POST", "gh api repos/o/r/pulls/5/comments -f body=x", 0),
    # 이슈 #114 — 다른 저장소. 픽스처 원격의 끝 두 마디가 o/r다
    ("--repo 이 저장소", G + " --repo o/r --fill", 0),
    ("-R URL 이 저장소", G + " -R https://github.com/o/r.git --fill", 0),
    ("--repo 남의 저장소", G + " --repo evil/r --fill", 2),
    ("-R 붙여 쓴 남의 저장소", G + " -Revil/r --fill", 2),
    ("--repo 둘", G + " --repo o/r --repo evil/r --fill", 2),
]

# 훅 프로세스 환경의 GH_REPO — (이름, GH_REPO 값, 기대 rc). 리뷰한 저장소에서 돈다
ENV_CASES = [
    ("GH_REPO 이 저장소", "o/r", 0),
    ("GH_REPO 남의 저장소", "evil/r", 2),
]

# 워크트리 — (이름, 메인 마커, 워크트리 마커, 명령, 기대 rc[, 원격 상태]). 이슈 #111.
# 세션 cwd는 메인이고, 명령의 `cd`·`--head`가 워크트리 브랜치를 PR로 연다. `<WT>`는 워크트리 절대 경로(공백 포함).
WT_CASES = [
    ("WT-A cd 워크트리 · 워크트리 미리뷰", "HEAD", None, 'cd "<WT>" && ' + G + " --base main", 2),
    ("WT-B --head 워크트리 · 미리뷰", "HEAD", None, G + " --head wt --base main", 2),
    ("WT-C cd 워크트리 · 리뷰됨", None, "HEAD", 'cd "<WT>" && ' + G + " --base main", 0),
    ("WT-D --head 워크트리 · 리뷰됨", None, "HEAD", G + " --base main --head wt", 0),
    ("WT-E 상대 경로 cd · 리뷰됨", None, "HEAD", 'cd "../wt dir" && ' + G, 0),
    # 줄바꿈·`;`로 이은 cd는 실패해도 다음 줄이 돈다 — 4차부터 막는다(`&&`·`|| exit`만)
    ("WT-F 앞줄의 cd(줄바꿈 — 막음)", None, "HEAD", 'cd "<WT>"\n' + G, 2),
    # 소유자 접두는 포크 브랜치다 — 이 저장소에서 대조할 수 없어 4차부터 막는다
    ("WT-G --head=소유자:브랜치(막음)", None, "HEAD", G + " --head=me:wt", 2),
    ("WT-w cd X &&\\n PR · 리뷰됨", None, "HEAD", 'cd "<WT>" &&\n  ' + G, 0),
    # 5차 — 다른 이름으로 푸시한 브랜치(`push -u origin wt:feature`). @{upstream} 조회가 죽어 있어 막혔다
    ("WT-x 다른 이름으로 푸시 · 리뷰됨", None, "HEAD", 'cd "<WT>" && ' + G, 0, "renamed"),
    ("WT-y origin/main을 추적 · 같은 이름 푸시 · 리뷰됨", None, "HEAD", 'cd "<WT>" && ' + G, 0, "tracks-main"),
    ("WT-H 워크트리 마커가 메인 SHA", "HEAD", "OTHER", 'cd "<WT>" && ' + G, 2),
    ("WT-I cd 대상을 못 푼다($변수)", "HEAD", "HEAD", 'cd "$WT" && ' + G, 2),
    ("WT-J cd 없음 · 메인 리뷰됨(기존 동작)", "HEAD", None, G + " --base main", 0),
    ("WT-K 실사용 모양 · 리뷰됨", None, "HEAD",
     G + ' --base main --head wt --title "제목 \'따옴표\'" '
     '--body "$(cat <<\'EOF\'\n본문의 ' + G + ' 와 it\'s\nEOF\n)"', 0),
    ("WT-L 실사용 모양 · 미리뷰", "HEAD", None,
     G + ' --base main --head wt --title "제목" --body "$(cat <<\'EOF\'\n본문\nEOF\n)"', 2),
    ("WT-M 따옴표 없는 $(…) 뒤 --head · 미리뷰", "HEAD", None, G + " --body $(cat f) --head wt", 2),
    # N·P·S·E~F 옛 판: 셸로는 맞는 모양이지만 단독 PR 생성이 아니라 막는다
    ("WT-N 따옴표 없는 $(…)(단독 아님)", None, "HEAD", G + " --body $(cat f) --head wt", 2),
    ("WT-O 닫힌 서브셸의 cd · 메인 미리뷰", None, "HEAD", '(cd "<WT>" && git push) && ' + G, 2),
    ("WT-P 서브셸 안의 cd 뒤 PR(단독 아님)", None, "HEAD", '(cd "<WT>" && ' + G + ")", 2),
    ("WT-Q 조건 안의 cd", "HEAD", "HEAD", 'if true; then cd "<WT>"; fi; ' + G, 2),
    ("WT-R eval 안의 cd", "HEAD", "HEAD", "eval cd /tmp && " + G, 2),
    ("WT-S { cd; } 묶음(단독 아님)", None, "HEAD", '{ cd "<WT>"; } && ' + G, 2),
    ("WT-T $(…;…) 뒤 --head · 미리뷰", "HEAD", None, G + " --body $(cat f; echo x) --head wt", 2),
    ("WT-U builtin cd 워크트리 · 미리뷰", "HEAD", None, 'builtin cd "<WT>" && ' + G, 2),
    ("WT-V 줄 이음 \\ 뒤 --head · 미리뷰", "HEAD", None, G + " --base main \\\n  --head wt", 2),
    ("WT-W 줄 이음 \\ 뒤 --head · 리뷰됨", None, "HEAD", G + " --base main \\\n  --head wt", 0),
    ("WT-X 안 돌았을 수 있는 cd(false &&)", None, "HEAD", 'false && cd "<WT>"; ' + G, 2),
    ("WT-Y 파이프 속 cd", None, "HEAD", 'cd "<WT>" | true; ' + G, 2),
    ("WT-Z 백그라운드 cd", None, "HEAD", 'cd "<WT>" & ' + G, 2),
    ("WT-a if 조건의 cd", "HEAD", None, 'if cd "<WT>"; then :; fi; ' + G, 2),
    ("WT-b pushd … popd", None, "HEAD", 'pushd "<WT>" && git push && popd && ' + G, 2),
    ("WT-c 붙은 -Hwt", "HEAD", None, G + " -Hwt --fill", 2),
    ("WT-d -H=wt", "HEAD", None, G + " -H=wt --fill", 2),
    ("WT-e 붙은 -Hwt · 리뷰됨", None, "HEAD", G + " -Hwt --fill", 0),
    ("WT-g then\\n cd", None, "HEAD", 'if false; then\n  cd "<WT>"\nfi\n' + G, 2),
    ("WT-h case 패턴 뒤 cd", None, "HEAD", 'case x in nope) cd "<WT>";; esac; ' + G, 2),
    ("WT-i 함수 본문 cd", None, "HEAD", 'f() {\n cd "<WT>"\n}\n' + G, 2),
    ("WT-j do\\n cd", None, "HEAD", 'while false\ndo\n cd "<WT>"\ndone\n' + G, 2),
    ("WT-k &&\\n cd", None, "HEAD", 'false &&\n cd "<WT>"\n' + G, 2),
    ("WT-l PR 생성 둘 — 둘째가 미리뷰", "HEAD", None, G + " --fill && " + G + " --head wt", 2),
    ("WT-m PR 생성 둘 — 둘째가 cd 뒤", "HEAD", None, G + ' --fill; cd "<WT>" && ' + G + " --fill", 2),
    ("WT-n --head 둘(gh는 마지막을 쓴다)", None, "HEAD", G + " --head wt --head main", 2),
    ("WT-o cd || exit 1 · 리뷰됨", None, "HEAD", 'cd "<WT>" || exit 1\n' + G, 0),
    # 3차 — 묶은 짧은 플래그, 디렉터리를 바꾸는 래퍼·환경변수, 원격 쪽
    ("WT-p 묶은 -fH wt · 미리뷰", "HEAD", None, G + " -fH wt", 2),
    ("WT-q 묶은 -fH wt · 리뷰됨", None, "HEAD", G + " -fH wt", 0),
    ("WT-r env -C 워크트리", "HEAD", None, 'env -C "<WT>" ' + G + " --fill", 2),
    ("WT-s GIT_DIR=워크트리", "HEAD", None, 'GIT_DIR="<WT>/.git" ' + G + " --fill", 2),
    ("WT-t 푸시 안 한 브랜치", None, "HEAD", G + " --head wt", 2, "unpushed"),
    ("WT-u 원격 wt가 다른 커밋", None, "HEAD", G + " --head wt", 2, "diverged"),
    ("WT-v 원격 wt로 다른 커밋을 푸시", None, "HEAD", "git push -f origin main:wt && " + G + " --head wt", 2),
    # 이슈 #114 — 추적 ref가 아니라 원격에 직접 묻는다
    ("WT-0 남이 원격 wt를 앞으로 밀었다(추적 ref 낡음)", None, "HEAD", G + " --head wt", 2, "pushed-elsewhere"),
    ("WT-1 추적 ref 없이 원격에 있다", None, "HEAD", G + " --head wt", 0, "pushed-untracked"),
]

# cwd가 저장소가 아닌데 --head를 준다 — 무엇이 PR이 될지 이 저장소로 확인할 수 없다
PARENT_CASES = [
    ("WT-f 저장소 밖 cwd + --head", "HEAD", None, G + " --repo o/r --head wt", 2),
]

# 이슈 #101 — 마커 기록을 PR 생성과 한 호출에 묶었다. 훅은 실행 **전에** 판정하므로 그 기록은 판정에 안 쓰이고
# 묶인 명령은 통째로 안 돈다. 막는 것은 같지만(rc 2) 안내가 「리뷰하라」로 나가면 원인을 틀리게 짚는다.
# (이름, 저장소 상태, 명령, 메시지에 있어야 할 것, 없어야 할 것). 저장소 상태: "reviewed"(마커 == HEAD) · "none".
BUNDLED = "통째로 실행되지 않았다"
REVIEW_FIRST = "스킬을 먼저 실행하라"
MARK = "git rev-parse HEAD > " + MARKER
MSG_CASES = [
    ("마커 기록 && PR(리뷰됨)", "reviewed", MARK + " && " + G + " --fill", [BUNDLED, "같다"], [REVIEW_FIRST]),
    ("마커 기록 && push && PR(마커 없음)", "none", MARK + " && git push -u origin main && " + G + " --fill",
     [BUNDLED, "없다"], [REVIEW_FIRST]),
    ("마커 기록 줄바꿈 PR", "reviewed", MARK + "\n" + G + " --fill", [BUNDLED], [REVIEW_FIRST]),
    ("붙여 쓴 >경로", "reviewed", "git rev-parse HEAD >" + MARKER + " && " + G, [BUNDLED], [REVIEW_FIRST]),
    (">> 덧붙이기", "reviewed", "git rev-parse HEAD >> " + MARKER + " && " + G, [BUNDLED], [REVIEW_FIRST]),
    ("tee로 기록", "reviewed", "git rev-parse HEAD | tee " + MARKER + " && " + G, [BUNDLED], [REVIEW_FIRST]),
    ("cd && 마커 기록 && PR", "reviewed", "cd . && " + MARK + " && " + G, [BUNDLED], [REVIEW_FIRST]),
    # 마커 기록이 아니다 — 원래 안내가 그대로 나가야 한다
    ("push && PR(마커 없음)", "none", "git push && " + G + " --fill", [REVIEW_FIRST], [BUNDLED]),
    ("마커를 읽기만 한다", "reviewed", "cat " + MARKER + " && " + G, [REVIEW_FIRST], [BUNDLED]),
    ("마커 이름을 말하기만 한다", "reviewed", 'echo "> ' + MARKER + '" && ' + G, [REVIEW_FIRST], [BUNDLED]),
]


def run_full(cmd, root, gh_repo=None):
    payload = json.dumps({"tool_input": {"command": cmd}, "cwd": root})
    env = {k: v for k, v in os.environ.items() if k != "GH_REPO"}
    if gh_repo:
        env["GH_REPO"] = gh_repo
    p = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


def run(cmd, root, gh_repo=None):
    return run_full(cmd, root, gh_repo)[0]


def report(ok, want, label, rc, tag=""):
    print(("  OK  " if ok else "  !!  ") + "%s%s — %-34s rc=%s"
          % ("통과해야 함" if want == 0 else "차단해야 함", tag, label, rc))
    return not ok


def main():
    fails = 0
    p_none, no_marker = make_repo(None)
    p_rev, reviewed = make_repo("HEAD")
    p_stale, stale = make_repo("0000000000000000000000000000000000000000")
    try:
        for label, cmd in BLOCK:
            rc = run(cmd, no_marker)
            fails += report(rc == 2, 2, label, rc, " (마커 없음)")
        for label, cmd in PASS:
            rc = run(cmd, no_marker)
            fails += report(rc == 0, 0, label, rc, " (마커 없음)")
        rc = run(G + " --base main", stale)
        fails += report(rc == 2, 2, "마커 != HEAD", rc)
        for label, cmd, want in REVIEWED_CASES:
            rc = run(cmd, reviewed)
            fails += report(rc == want, want, label, rc, " (리뷰됨)")
        for label, value, want in ENV_CASES:
            rc = run(G + " --fill", reviewed, gh_repo=value)
            fails += report(rc == want, want, label, rc, " (리뷰됨)")
        # 마커만 기록하는 호출은 PR 생성이 아니다 — 스킬 5단계가 이렇게 찍는다
        rc = run(MARK, no_marker)
        fails += report(rc == 0, 0, "마커 기록 단독", rc, " (마커 없음)")
        for label, state, cmd, must, must_not in MSG_CASES:
            rc, err = run_full(cmd, reviewed if state == "reviewed" else no_marker)
            miss = [s for s in must if s not in err] + ["¬" + s for s in must_not if s in err]
            fails += report(rc == 2 and not miss, 2, label, rc, " (안내%s)" % (" — " + ", ".join(miss) if miss else ""))
        # `push -u <URL> x`면 branch.x.remote가 이름이 아니라 URL이다 — `-R`이 같은 저장소면 열려야 한다(코드 리뷰)
        p_url, url_repo = make_repo(None)
        try:
            sh("-C", url_repo, "switch", "-q", "-c", "x")
            sh("-C", url_repo, "commit", "-q", "--allow-empty", "-m", "x")
            sh("-C", url_repo, "push", "-q", "-u", os.path.join(p_url, "o", "r.git"), "x")
            write_marker(url_repo, head_of(url_repo))
            rc = run(G + " -R o/r --fill", url_repo)
            fails += report(rc == 0, 0, "URL로 push -u한 브랜치 + -R 이 저장소", rc, " (리뷰됨)")
        finally:
            shutil.rmtree(p_url, ignore_errors=True)
        cases = [(c[:5], c[5] if len(c) > 5 else "pushed", False) for c in WT_CASES]
        cases += [(c, "pushed", True) for c in PARENT_CASES]
        for (label, mm, wm, cmd, want), remote, in_parent in cases:
            parent, main_dir, wt_dir = make_worktree_pair(mm, wm, remote)
            try:
                rc = run(cmd.replace("<WT>", wt_dir), parent if in_parent else main_dir)
            finally:
                shutil.rmtree(parent, ignore_errors=True)
            fails += report(rc == want, want, label, rc)
    finally:
        for d in (p_none, p_rev, p_stale):
            shutil.rmtree(d, ignore_errors=True)

    print("\n실패 %d건" % fails)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
