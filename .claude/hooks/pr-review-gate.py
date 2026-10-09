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
- `--head <브랜치>`(`-H`, `-Hwt`, `-H=wt`, `소유자:브랜치`)가 있으면 PR이 될 커밋은 **그 브랜치의
  로컬 끝**이고, 마커는 그 브랜치가 체크아웃된 워크트리의 것을 읽는다.
- 없으면 PR 생성이 도는 디렉터리의 HEAD와 마커다. 그 디렉터리는 훅 입력의 `cwd`에서 시작해
  PR 생성 **앞의 `cd`를 확실한 것만** 따라간다(아래).
첫 판은 `cwd`의 HEAD·마커만 읽었다. 세션이 메인 체크아웃에 있고 `cd <워크트리> && …`로 PR을
열면 메인의 것으로 판정해, 메인 마커가 메인 HEAD와 같기만 하면 리뷰하지 않은 워크트리 브랜치가
통과했다 — 게이트가 열리는 방향이다.

**모르면 막는다.** 셸을 다 해석할 수는 없다. 그래서 따라가는 형태를 좁히고 나머지는 막는다.
고친 판마다 「따라가는 형태」를 넓히다가 새는 모양이 계속 나왔다(서브셸·조건·`$( … )`·줄 이음·
pushd/popd·파이프 — 코드 리뷰가 손으로 짚은 것까지 test-detect에 있다). 넓히는 대신 막는 쪽이 이 게이트의 기본값이다.
- 따라가는 `cd`: 토막의 첫 낱말(`{`·`!`·`builtin`·`command` 뒤 포함)이고, 대상이 리터럴 경로이며,
  앞 구분자가 줄머리·`;`·줄바꿈·`(`이거나 `&&`(그때는 PR 생성까지 `&&`로만 이어질 때), 뒤 구분자가
  `|`·`&`·`||`가 아닐 때. 서브셸 `( … )`이 닫히면 되돌린다. `pushd`는 쌓고 `popd`는 꺼낸다.
- 막는 것: 그 밖의 자리에 `cd`·`pushd`·`popd`가 낱말로 있을 때(`if cd …`, `then cd`, `false && cd x; …`,
  파이프·백그라운드), `cd "$WT"`·`cd -`처럼 셸이 돌아야 아는 대상, 없는 디렉터리, `eval`·`source`·
  `bash`처럼 안에서 무엇을 할지 모르는 명령, 로컬에 없는 `--head` 브랜치, 저장소 밖에서 `--head`·`cd`.
- 판정 대상을 바꾸는 명령도 막는다: PR 생성 앞에서 HEAD를 움직이는 git 명령(`commit`·`checkout`·
  `switch`·`reset`·`rebase`·`merge`·`pull`·`cherry-pick`·`revert`·`am`) — 훅은 명령이 돌기 **전에** HEAD를 읽으므로
  리뷰한 커밋으로 판정하고 그 뒤 커밋이 PR에 들어간다. 그리고 `git push`의 `<src>:<dst>` refspec —
  로컬 브랜치와 다른 커밋을 원격 브랜치에 올릴 수 있는데, PR은 원격 브랜치로 만들어진다.
입력을 못 읽는 경우(아래 `main`)와 다르다 — 그건 게이트가 사고를 만들지 않으려고 열어 두지만,
이건 **PR 생성이 확실한데 무엇을 여는지 모르는** 경우라 열면 바로 위조 경로가 된다.

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그
사고를 냈다 — 훅을 설명하는 문서를 heredoc으로 쓰는 명령이 게이트에 막혔다.
명령을 **실행 위치**에서만 본다: heredoc 본문과 따옴표 안·이스케이프·`#` 주석을 가린 뒤(`lex`),
줄머리나 셸 구분자·키워드(`then`·`do` …) 바로 뒤에 오는 것만 명령으로 친다.

⚠ **알려진 한계** —
- `strip_heredocs`는 따옴표 상태를 추적하지 않는다. 따옴표 안의 `<< 단어`를 heredoc 여는
  줄로 오인해서, 뒤따르는 줄들을 종료 태그까지 걷어낸다. 그 안에 PR 생성 명령이 있으면 못 본다.
  "여러 줄 명령 + 앞줄 따옴표 안의 `<<` + 뒤에 PR 생성"이 겹쳐야 하므로 조건만 적어 둔다.
- 따옴표 안의 명령(`bash -c '…'`, `eval '…'`)·함수·별칭 안의 PR 생성은 **못 본다.** 탐지가 따옴표 안을
  보면 문서·커밋 메시지마다 막힌다(첫 판의 사고). 일부러 감싸야 생기는 모양이라 조건만 적는다.
- `--head` 판정은 **로컬** 브랜치 끝이다. 원격 브랜치에 이미 다른 커밋이 있으면(남이 푸시) 못 본다.
- `git -C <다른 저장소>`·`GH_REPO`·`--repo`로 다른 저장소를 여는 것은 보지 않는다.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
# 명령 자리: 줄머리·구분자·키워드 뒤. 환경변수 접두(`VAR=x gh …` — 둘째 판이 놓쳤다)와
# `command`·`env` 같은 접두, 경로(`/usr/bin/gh`), `pr`과 동사 사이 플래그(`-R o/r`), 별칭 `new`까지.
KW = r"then|do|else|elif|time|command|exec|env|nohup|builtin|sudo"
CMD = re.compile(
    r"(?:^|[;&|(){}\n]|(?<![\w-])(?:" + KW + r")(?![\w-]))"
    # 명령 부분을 `cmd`로 잡는다 — 앞 구분자(`&&`의 둘째 `&`, `;`)가 토막 계산에서 빠지지 않게
    r"\s*(?P<cmd>(?:\w+=\S*\s+)*(?:(?:" + KW + r")\s+)*(?:[^\s;&|()]*/)?gh\s+pr\s+"
    r"(?:-{1,2}[\w-]+(?:[ =]+(?!-)[^\s;&|()]+)?\s+)*(?:" + "create" + r"|new)(?![\w-]))")
# here-string `<<<`는 heredoc이 아니다 — 첫 판은 `<<< wt`의 `<< wt`를 여는 줄로 보고 뒤를 걷어냈다
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
# 셸 구분자. `lex`가 같은 길이로 가린 문자열에서 찾으므로 위치가 원문과 맞는다.
SEP = re.compile(r"&&|\|\||;;|[;|&()\n]")
ENV = re.compile(r"^\w+=")
CD = {"cd", "pushd", "popd"}
PREFIX = {"{", "}", "!", "builtin", "command"}  # 이 뒤의 cd도 현재 셸의 cd다
OPAQUE = {"eval", "source", ".", "bash", "sh", "zsh", "exec"}  # 안에서 무엇을 할지 모른다
MOVES_HEAD = {"commit", "checkout", "switch", "reset", "rebase", "merge", "pull",
              "cherry-pick", "revert", "am"}
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


def lex(text):
    """(masked, clean) — 둘 다 text와 **같은 길이**다.

    clean: `#` 주석과 줄 이음(`\\` + 줄바꿈)만 공백으로. 셸 낱말을 읽을 때 쓴다.
    masked: clean에서 따옴표 안·이스케이프까지 공백으로. 명령 자리·구분자를 찾을 때 쓴다.
    첫 판은 정규식 `'[^']*'|"[^"]*"`로 가려서, 주석 속 `don't`의 아포스트로피나 `\\"`가 다음
    따옴표까지 — PR 생성 명령까지 — 가렸다. 줄 이음을 몰라 `\\` 뒤 줄의 `--head`를 놓쳤다.
    """
    n = len(text)
    masked, clean = list(text), list(text)

    def blank(buf, a, b):
        for k in range(a, min(b, n)):
            buf[k] = " "

    i = 0
    while i < n:
        c = text[i]
        if c == "\\":
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == "\n":
                blank(masked, i, i + 2)
                blank(clean, i, i + 2)
            elif nxt.isalnum():
                masked[i] = " "  # `\gh`는 gh다
                i += 1
                continue
            else:
                blank(masked, i, i + 2)
            i += 2
            continue
        if c == "'":
            j = text.find("'", i + 1)
            j = n - 1 if j < 0 else j
            blank(masked, i, j + 1)
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(j, n - 1)
            blank(masked, i, j + 1)
            i = j + 1
            continue
        if c == "#" and (i == 0 or text[i - 1] in " \t\n;&|()"):
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(masked, i, j)
            blank(clean, i, j)
            i = j
            continue
        i += 1
    return "".join(masked), "".join(clean)


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def segments(clean, masked, end):
    """`end` 앞까지를 구분자로 나눈 [(clean 토막, 앞 구분자, 뒤 구분자)]."""
    out, last, before = [], 0, ""
    for m in SEP.finditer(masked, 0, end):
        out.append((clean[last:m.start()], before, m.group(0)))
        before, last = m.group(0), m.end()
    out.append((clean[last:end], before, ""))
    return out


def words(seg):
    """토막을 셸 낱말로. 환경변수 접두는 흘린다. 못 나누면 None."""
    try:
        w = shlex.split(seg, posix=True)
    except ValueError:
        return None
    while w and ENV.match(w[0]):
        w = w[1:]
    return w


def git_sub(w):
    """`git [-C x] [-c k=v] [--no-pager] <sub> …`의 (sub, 그 뒤 낱말들)."""
    i = 1
    while i < len(w) and w[i].startswith("-"):
        i += 2 if w[i] in ("-C", "-c") else 1
    return (w[i], w[i + 1:]) if i < len(w) else ("", [])


def resolve_dir(clean, masked, start, cwd):
    """PR 생성이 도는 디렉터리. 정하지 못하거나 판정을 바꾸는 명령이 있으면 (None, 이유)."""
    segs = segments(clean, masked, start)
    d, pstack, paren = cwd, [], []
    for idx, (seg, before, after) in enumerate(segs):
        w = words(seg)
        if w is None:
            return None, "PR 생성 앞 명령을 셸 낱말로 나누지 못했다: %r" % seg.strip()
        while w and w[0] in PREFIX:
            w = w[1:]
        if w and w[0] in OPAQUE:
            return None, "`%s`가 PR 생성 앞에 있다 — 안에서 디렉터리·HEAD를 바꾸는지 모른다" % w[0]
        if w and w[0] == "git":
            sub, rest = git_sub(w)
            if sub in MOVES_HEAD:
                return None, ("PR 생성 앞에서 `git %s`가 HEAD를 움직인다 — 훅은 명령이 돌기 전 HEAD로 "
                              "판정하므로 그 뒤 커밋이 리뷰 없이 들어간다. 따로 실행하고 리뷰한 뒤 연다" % sub)
            if sub == "push" and any(":" in a and "://" not in a and "@" not in a
                                     for a in rest if not a.startswith("-")):
                return None, ("`git push`에 `<src>:<dst>` refspec이 있다 — 로컬 브랜치와 다른 커밋을 원격에 "
                              "올릴 수 있는데 PR은 원격 브랜치로 만들어진다")
        if any(x in CD for x in w):
            if w[0] not in CD:
                return None, "`%s` 안의 `%s`는 돌았는지 셸이 돌아야 안다" % (
                    w[0], next(x for x in w if x in CD))
            if before in ("||", "|", "&") or after in ("||", "|", "&"):
                return None, "`%s`가 `%s`/`%s` 사이에 있다 — 현재 셸에서 돌았는지 모른다" % (
                    w[0], before or "줄머리", after)
            if before == "&&" and any(s[2] not in ("&&",) for s in segs[idx:-1]):
                return None, "`&& %s` 뒤에 PR 생성까지 `&&`가 아닌 구분자가 있다 — 안 돈 채 PR이 열릴 수 있다" % w[0]
            if w[0] == "popd":
                if not pstack:
                    return None, "`popd`가 꺼낼 `pushd`가 이 명령 안에 없다"
                d = pstack.pop()
            else:
                arg = w[1] if len(w) > 1 else "~"
                if arg == "-" or "$" in arg or "`" in arg:
                    return None, "`%s %s`의 대상은 셸이 돌아야 안다" % (w[0], arg)
                if w[0] == "pushd":
                    pstack.append(d)
                d = os.path.normpath(os.path.join(d, os.path.expanduser(arg)))
                if not os.path.isdir(d):
                    return None, "`%s` 대상 디렉터리가 없다: %s" % (w[0], d)
        if after == "(":
            paren.append((d, list(pstack)))
        elif after == ")" and paren:
            d, pstack = paren.pop()
    return d, None


def head_branch(clean, masked, start):
    """PR 생성 명령의 `--head` 값(소유자 접두는 뗀다). 없으면 None.

    명령의 끝은 괄호 깊이 0의 명령 구분자(`&&` `||` `;` `|` `&` 줄바꿈)다 — `$( … )` 안의 것은
    끝이 아니고(WT-M·T), 줄 이음은 `lex`가 가렸다(WT-V). 값은 clean에서 읽는다(`--head "wt"`, `-Hwt`).
    """
    stop, depth = len(masked), 0
    for m in re.finditer(r"&&|\|\||[;|&\n()]", masked[start + 1:]):
        t = m.group(0)
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
            if depth < 0:  # PR 명령을 감싼 서브셸이 닫힌다
                stop = start + 1 + m.start()
                break
        elif depth == 0:
            stop = start + 1 + m.start()
            break
    for m in re.finditer(r"(?<![\w-])(?:--head(?![\w-])|-H)", masked[:stop]):
        if m.start() < start:
            continue
        rest = clean[m.end():stop].lstrip("= \t")
        if rest[:1] in ("'", '"'):
            j = rest.find(rest[0], 1)
            val = rest[1:j] if j > 0 else rest[1:]
        else:
            val = re.match(r"[^\s;&|()<>]*", rest).group(0)
        if val:
            return val.split(":")[-1]
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


def block(why, branch="?", sha="", stat=""):
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
    masked, clean = lex(strip_heredocs(command))
    found = CMD.search(masked)
    if not found:
        return 0

    cwd = os.path.normpath(payload.get("cwd") or os.getcwd())
    start = found.start("cmd")
    d, why = resolve_dir(clean, masked, start, cwd)
    if d is None:
        return block("PR이 어느 커밋인지 정하지 못했다 — %s. 워크트리에서 열려면 세션을 그 워크트리로 "
                     "옮기거나(EnterWorktree) `cd <경로> && …` 한 줄로 쓰거나 `--head <브랜치>`를 쓴다." % why)
    branch = head_branch(clean, masked, start)
    top = git("-C", d, "rev-parse", "--show-toplevel")
    if not top:
        if d == cwd and not branch:
            return 0  # 저장소 밖 — 첫 판부터의 동작
        return block("PR 생성 위치가 git 저장소가 아니라(%s) `--head`·`cd`가 가리키는 것을 확인할 수 없다." % d)

    if branch:
        sha = git("-C", top, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % branch)
        if not sha:
            return block("`--head %s` 브랜치가 로컬에 없어 무엇이 PR이 되는지 확인할 수 없다." % branch, branch)
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
