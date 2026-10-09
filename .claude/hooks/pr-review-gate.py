#!/usr/bin/env python3
"""PR 생성 전 코드리뷰 게이트 — PreToolUse(Bash) 훅.

PR 생성 명령을 가로채, **PR이 될 커밋에 대한 리뷰가 끝났는지**만 본다.
끝나 있으면 통과시키고, 아니면 exit 2로 막고 무엇을 하라고 알려 준다.

왜 훅인가 — 이 저장소의 사이클은 CLAUDE.md에 적혀 있지만, 적혀 있는 것은
지켜지지 않을 수 있다. `npm run check`는 통과해야 다음이 안 되는 구조라
강제되지만, 리뷰에는 그런 구조가 없었다.

마커 파일: `.claude/.pr-review-ok` — 내용은 리뷰가 통과한 커밋 SHA 하나.
`/pr-review-gate` 스킬이 **차단 항목 0일 때만** 찍는다. 손으로 찍지 않는다.
찍는 순간 "이 커밋을 읽었고 문제가 없다"는 뜻이 되고, 그 문장이 거짓이면
게이트는 있는 것이 없는 것보다 나쁘다 — 다음 사람이 초록불을 믿는다.

**어느 커밋·어느 마커인가** (이슈 #111). 마커는 체크아웃(워크트리)마다 하나다.
- 명령 안에서 PR 생성 앞에 `cd`가 있으면 그 디렉터리를 따라간다(앞줄의 `cd`, 상대 경로,
  따옴표 친 경로 포함). 없으면 훅 입력의 `cwd`.
- `--head <브랜치>`(`-H`, `소유자:브랜치`)가 있으면 PR이 될 커밋은 **그 브랜치의 끝**이고,
  마커는 그 브랜치가 체크아웃된 워크트리의 것을 읽는다. 어디에도 체크아웃돼 있지 않으면
  위에서 정한 체크아웃의 마커다.
첫 판은 `cwd`의 HEAD·마커만 읽었다. 세션이 메인 체크아웃에 있고 `cd <워크트리> && …`로 PR을
열면 **메인의** HEAD·마커로 판정해, 메인 마커가 메인 HEAD와 같기만 하면 리뷰하지 않은
워크트리 브랜치가 통과했다 — 게이트가 열리는 방향이다.

**정하지 못하면 막는다.** `cd "$WT"`·`cd -`·`` cd `…` ``처럼 셸이 돌아야 알 수 있는 대상,
없는 디렉터리, 로컬에 없는 `--head` 브랜치. 입력을 못 읽는 경우(아래 `main`)와 다르다 —
그건 게이트가 사고를 만들지 않으려고 열어 두지만, 이건 **PR 생성이 확실한데 무엇을 여는지
모르는** 경우라 열면 바로 위조 경로가 된다.

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그
사고를 냈다 — 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 게이트에 막혔다.
명령을 **실행 위치**에서만 본다: 따옴표 안과 heredoc 본문을 걷어낸 뒤,
줄머리나 셸 구분자 바로 뒤에 오는 것만 명령으로 친다.

⚠ **알려진 한계** —
- `strip_heredocs`는 따옴표 상태를 추적하지 않는다. 따옴표 안의 `<< 단어`를 heredoc 여는
  줄로 오인해서, 뒤따르는 줄들을 종료 태그까지 걷어낸다. 그 안에 PR 생성 명령이 있으면 못 본다.
  "여러 줄 명령 + 앞줄 따옴표 안의 `<<` + 뒤에 PR 생성"이 겹쳐야 하므로 조건만 적어 둔다.
- `cd`는 구분자로 나눈 토막의 첫 낱말일 때 따른다(`{`·`!` 뒤도). 서브셸 `( … )`은 괄호로 되돌리고,
  `then`·`do`·`else`·`elif`·`eval` 뒤의 `cd`는 돌았는지 모르므로 막는다. **모르는 것** — 함수·별칭·
  `source`한 스크립트 안의 `cd`, `builtin cd`·`command cd`. 이것들은 cwd에 그대로 있다고 보므로
  **틀린 체크아웃을 보고 열릴 수 있다** — 그 체크아웃이 리뷰를 마쳤으면 그쪽 마커로 통과한다.
  첫 판의 머리말은 서브셸 한계를 「대개 막히는 방향」이라고 적었는데 정반대였다(WT-O).
  이런 명령이 필요하면 `--head <브랜치>`를 쓴다 — 그러면 디렉터리가 아니라 브랜치로 판정한다.
- `git -C`·`GH_REPO`·`--repo`는 보지 않는다.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
# `VAR=x VAR2=y gh …` 형태를 놓치지 않도록 환경변수 접두를 먼저 흘린다.
# 첫 판이 이걸 빠뜨렸다 — 게이트가 **열리는** 방향의 결함이라 가장 나쁘다.
CMD = re.compile(r"(?:^|[;&|(\n])\s*(?:\w+=\S*\s+)*gh\s+pr\s+" + "create" + r"\b")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# 셸 구분자. 따옴표를 같은 길이의 공백으로 가린 문자열에서 찾으므로 위치가 원문과 맞는다.
SEP = re.compile(r"&&|\|\||[;|&()\n]")
ENV = re.compile(r"^\w+=")
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
    """따옴표로 감싼 구간을 **같은 길이의** 공백으로 가린다.

    `grep "gh pr …"` 같은 언급을 걸러낸다. 길이를 지키는 것은 가린 문자열에서 찾은
    구분자 위치로 원문을 잘라 `cd "경로"`의 따옴표 친 경로를 되살리기 위해서다.
    """
    return re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: " " * len(m.group(0)), command)


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def segments(text, masked, end):
    """`end` 앞까지를 셸 구분자로 나눈 (원문 토막, 그 뒤 구분자) 목록. 마지막 구분자는 ""."""
    out, last = [], 0
    for m in SEP.finditer(masked, 0, end):
        out.append((text[last:m.start()], m.group(0)))
        last = m.end()
    out.append((text[last:end], ""))
    return out


def words(seg):
    """토막을 셸 단어로. 환경변수 접두는 흘린다. 못 나누면 None."""
    try:
        w = shlex.split(seg, posix=True)
    except ValueError:
        return None
    while w and ENV.match(w[0]):
        w = w[1:]
    return w


def follow_cd(text, masked, start, cwd):
    """PR 생성 앞의 `cd`를 따라간 디렉터리. 못 풀면 (None, 이유).

    서브셸 `( … )` 안의 `cd`는 닫히면 끝난다 — 여는 괄호에서 디렉터리를 쌓고 닫는 괄호에서
    되돌린다. 첫 판은 이걸 안 따져서 `(cd <리뷰된 워크트리> && git push) && <PR 생성>`을
    그 워크트리의 마커로 판정해 메인 체크아웃의 미리뷰 브랜치를 열었다(test-detect WT-O).
    """
    d, stack = cwd, []
    for seg, sep in segments(text, masked, start):
        w = words(seg)
        if w is None:
            return None, "PR 생성 앞 명령을 셸 단어로 나누지 못했다: %r" % seg.strip()
        while w and w[0] in ("{", "}", "!"):
            w = w[1:]  # 중괄호 묶음은 서브셸이 아니다 — 안의 cd가 남는다
        if w and w[0] in ("then", "do", "else", "elif", "eval") and ({"cd", "pushd"} & set(w)):
            return None, "`%s` 안의 `cd`는 돌았는지 셸이 돌아야 안다" % w[0]
        if w and w[0] in ("cd", "pushd"):
            arg = w[1] if len(w) > 1 else "~"
            if arg == "-" or "$" in arg or "`" in arg:
                return None, "`%s %s`의 대상은 셸이 돌아야 안다" % (w[0], arg)
            d = os.path.normpath(os.path.join(d, os.path.expanduser(arg)))
        if sep == "(":
            stack.append(d)
        elif sep == ")" and stack:
            d = stack.pop()
    if not os.path.isdir(d):
        return None, "`cd` 대상 디렉터리가 없다: %s" % d
    return d, None


def head_branch(text, masked, start):
    """PR 생성 명령의 `--head` 값(소유자 접두는 뗀다). 없으면 None.

    명령의 끝은 명령 구분자(`&&` `||` `;` `|` `&` 줄바꿈)까지다 — **괄호에서 끊지 않는다.**
    첫 판은 `SEP`로 끊어서 `--body $(cat f) --head wt`의 `--head`를 못 보고 cwd의 HEAD로
    판정했다(test-detect WT-M — 게이트가 열리는 방향). 값은 가린 문자열에서 위치를 찾고
    원문에서 셸 단어로 읽는다(`--head "wt"`).
    """
    end = re.compile(r"&&|\|\||[;|&\n]").search(masked, start + 1)
    stop = end.start() if end else len(masked)
    for m in re.finditer(r"(?<!\S)(?:--head(?:=|\s+)|-H\s+)", masked[:stop]):
        if m.start() < start:
            continue
        try:
            w = shlex.split(text[m.end():stop], posix=True)
        except ValueError:
            w = text[m.end():stop].split()
        if w:
            return w[0].split(":")[-1]
    return None


def checkout_of(branch, top):
    """그 브랜치가 체크아웃된 워크트리 경로. 없으면 None."""
    path = None
    for line in git("-C", top, "worktree", "list", "--porcelain").split("\n"):
        if line.startswith("worktree "):
            path = line[len("worktree "):]
        elif line == "branch refs/heads/" + branch:
            return path
    return None


def block(why, branch, sha, stat):
    sys.stderr.write(
        "PR 생성이 게이트에 막혔다. %s\n\n"
        "브랜치: %s (커밋 %s)\n%s\n\n"
        "`/pr-review-gate` 스킬을 먼저 실행하라. 리뷰는 `npm run check`와 보는 축이 다르다 —\n"
        "린트는 규칙의 **존재**를 보고, 리뷰는 그 규칙이 이 변경에서 **실제 조건을\n"
        "재현하는지**를 본다. 차단 항목이 0이 되면 스킬이 마커를 찍고, 그때 통과한다.\n\n"
        "게이트를 건너뛸 이유가 있으면 사용자에게 확인받아라. 마커를 손으로 찍지 마라.\n"
        % (why, branch, sha[:8] or "?", stat)
    )
    return 2


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 막지 않는다. 게이트가 사고를 만들면 안 된다

    command = (payload.get("tool_input") or {}).get("command") or ""
    text = strip_heredocs(command)
    masked = strip_quoted(text)
    found = CMD.search(masked)
    if not found:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    d, why = follow_cd(text, masked, found.start(), cwd)
    if d is None:
        return block("PR이 어느 체크아웃의 커밋인지 정하지 못했다 — %s. 워크트리에서 열려면 세션을 "
                     "그 워크트리로 옮기거나(EnterWorktree) `cd`에 경로를 그대로 쓴다." % why,
                     "?", "", "")
    top = git("-C", d, "rev-parse", "--show-toplevel")
    if not top:
        if d == os.path.normpath(cwd):
            return 0  # cwd가 저장소가 아니다 — 첫 판부터의 동작
        return block("`cd` 대상이 git 저장소가 아니다: %s." % d, "?", "", "")

    branch = head_branch(text, masked, found.start())
    if branch:
        sha = git("-C", top, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % branch)
        if not sha:
            return block("`--head %s` 브랜치가 로컬에 없어 무엇이 PR이 되는지 확인할 수 없다." % branch,
                         branch, "", "")
        where = checkout_of(branch, top) or top
    else:
        sha = git("-C", top, "rev-parse", "HEAD")
        if not sha:
            return 0  # 커밋이 없는 저장소
        branch = git("-C", top, "rev-parse", "--abbrev-ref", "HEAD") or "?"
        where = top

    try:
        with open(os.path.join(where, MARKER), encoding="utf-8") as f:
            reviewed = f.read().strip()
    except OSError:
        reviewed = ""

    if reviewed == sha:
        return 0

    stat = git("-C", where, "diff", "--stat", "main..." + sha) or "(main과의 차이를 못 읽었다)"
    if reviewed:
        why = "%s의 마커는 %s에 찍혀 있는데 PR이 될 커밋은 %s다 — 리뷰 뒤에 커밋이 더 쌓였거나 다른 브랜치의 마커다." % (
            where, reviewed[:8], sha[:8])
    else:
        why = "%s에 리뷰 마커가 없다 — 이 브랜치는 아직 리뷰되지 않았다." % where
    return block(why, branch, sha, stat)


if __name__ == "__main__":
    sys.exit(main())
