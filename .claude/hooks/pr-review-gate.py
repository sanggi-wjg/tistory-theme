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

## 어느 커밋·어느 마커인가 (이슈 #111)

마커는 체크아웃(워크트리)마다 하나다. 명령 안의 PR 생성 **하나하나**에 대해:
- `--head <브랜치>`(`-Hwt`·`-H=wt`·`소유자:`)가 있으면 그 브랜치의 **로컬** 끝을, 그 브랜치가
  체크아웃된 워크트리의 마커와 대조한다. 한 PR 생성에 `--head`가 여럿이면 막는다(gh는 마지막을 쓴다).
- 없으면 PR 생성이 도는 디렉터리의 HEAD와 마커다. 그 디렉터리는 훅 입력의 `cwd`, 또는 명령 **맨 앞**의
  `cd <리터럴 경로>`(뒤가 `&&`·`;`·줄바꿈, 또는 `|| exit [N]`)다.
첫 판은 `cwd`의 HEAD·마커만 읽었다. 세션이 메인 체크아웃에 있고 `cd <워크트리> && …`로 PR을 열면
메인의 것으로 판정해, 메인 마커가 메인 HEAD와 같기만 하면 리뷰하지 않은 워크트리 브랜치가 통과했다.

## 허용 목록 — 그 밖은 막는다

셸을 다 해석할 수는 없다. 둘째·셋째 판은 「따라가는 형태」를 넓히는 쪽이었고, 넓힐 때마다 샜다 —
닫힌 서브셸, 조건·반복·`case`·함수 본문 속 `cd`, 줄 이음, `$( … )` 속 `;`, 래퍼 뒤 `git commit`(코드 리뷰 두 번이
실행해 확인한 것까지 test-detect에 있다). 그래서 PR 생성이 든 명령에는 **허용하는 모양만** 둔다.
- `cd`·`pushd`·`popd`는 위의 맨 앞 `cd` 하나만. 다른 자리에 낱말로 있으면 막는다.
- git은 HEAD를 움직이지 않는 하위 명령(`SAFE_GIT`)만. 전역 옵션·경로·래퍼 뒤도 본다. 훅은 명령이 돌기
  **전에** HEAD를 읽으므로, 같은 명령 안의 `git commit` 등은 리뷰 안 된 커밋을 PR에 넣는다. `gh pr checkout`도.
- 셸 구조 — 제어 키워드(`if`·`while`·`case`·`{` …), 맨 괄호(서브셸·함수 정의), `eval`·`source`·`bash` 류는 막는다.
- `git push`의 `<src>:<dst>`는 `src`가 `HEAD`나 그 브랜치이고 `dst`가 그 브랜치일 때만. PR은 원격 브랜치로 만들어진다.
- 정하지 못하면 막는다 — `cd "$WT"`·`cd -`, 없는 디렉터리, 로컬에 없는 `--head`, 저장소 밖에서 `--head`·`cd`.
입력을 못 읽는 경우(아래 `main`)와 다르다 — 그건 게이트가 사고를 만들지 않으려고 열어 두지만, 이건
**PR 생성이 확실한데 무엇을 여는지 모르는** 경우라 열면 바로 위조 경로가 된다.
막히면 명령을 단순하게 쓴다 — 세션을 그 워크트리로 옮기거나(EnterWorktree), `cd <경로> && git push && <PR 생성>`
한 줄, 또는 `--head <브랜치>`. 커밋은 따로 한 뒤 리뷰한다.

## 탐지

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그 사고를 냈다 — 훅을 설명하는
문서를 heredoc으로 쓰는 명령이 게이트에 막혔다. 그래서 heredoc 본문과 따옴표 안·`#` 주석을 가린 뒤(`lex`)
본다. 단 큰따옴표 안의 `$( … )`·백틱은 셸이 **실행하므로** 가리지 않는다(`url="$(<PR 생성>)"`). 가린 뒤에는
**명령 자리를 따지지 않는다** — 한 단순 명령 안에 `gh … pr … create|new`가 있으면 PR 생성으로 본다
(`timeout 60`·`xargs`·`sudo -u x`·`env -i` 뒤도). 따옴표 밖 산문(`echo gh pr create`)은 막힐 수 있다 — 감수한다.

## 알려진 한계 (이슈 #114)

- `strip_heredocs`는 따옴표 상태를 추적하지 않는다. 따옴표 안의 `<< 단어`를 heredoc 여는 줄로 오인해서,
  뒤따르는 줄들을 종료 태그까지 걷어낸다. 그 안에 PR 생성 명령이 있으면 못 본다.
- 작은따옴표 안의 명령(`bash -c '…'`, `eval '…'` — 둘 다 막는 낱말이지만 `sh -c`의 다른 이름까지는 모른다),
  함수·별칭·`source`한 스크립트 안의 PR 생성.
- `--head` 판정은 **로컬** 브랜치 끝이다. 원격 브랜치에 이미 다른 커밋이 있으면 못 본다.
- `git -C <다른 저장소>`·`GH_REPO`·`--repo`로 다른 저장소를 여는 것.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
W = r"[^\s;&|()`]"  # 낱말 글자 — 구분자·괄호·백틱이 아닌 것
GH = re.compile(r"(?<!" + W + r")(?:" + W + r"*/)?gh\s+(?:" + W + r"+\s+)*?pr\s+(?:" + W + r"+\s+)*?(?:"
                + "create" + r"|new)(?!" + W + r")")
# here-string `<<<`는 heredoc이 아니다. 태그는 따옴표 안이면 무엇이든, 아니면 구분자 전까지(`END-X`).
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(?:'([^']+)'|\"([^\"]+)\"|([^\s;&|()<>'\"]+))")
SEP = re.compile(r"&&|\|\||;;|[;|&()\n`]")
WORD = re.compile(W + r"+")
CD = {"cd", "pushd", "popd"}
CONTROL = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case", "esac",
           "select", "function", "{", "}", "[[", "]]", "coproc"}
OPAQUE = {"eval", "source", "exec", "bash", "sh", "zsh", "dash", "ksh", "fish"}
# HEAD·작업 브랜치를 움직이지 않는 git 하위 명령. 목록 밖은 막는다(허용 목록).
SAFE_GIT = {"push", "status", "log", "diff", "show", "rev-parse", "fetch", "remote", "add", "ls-files",
            "ls-remote", "describe", "config", "grep", "blame", "shortlog", "rev-list", "cat-file",
            "branch", "tag", "check-ignore", "symbolic-ref", "for-each-ref", "name-rev", "help", "version"}
GIT_ARG_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix",
                "--config-env", "--attr-source"}
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
        tag = m.group(1) or m.group(2) or m.group(3)
        while i < len(lines) and lines[i].strip() != tag:
            i += 1
        i += 1  # 종료 태그 줄도 버린다
    return "\n".join(out)


def lex(text):
    """(full, exe, clean) — 셋 다 text와 **같은 길이**다.

    clean: `#` 주석과 줄 이음(`\\` + 줄바꿈)만 공백. 셸 낱말을 읽을 때 쓴다.
    full:  clean에서 따옴표 안 전부·이스케이프까지 공백. 맨 위 단순 명령의 경계를 찾을 때 쓴다.
    exe:   full과 같되 큰따옴표 안의 `$( … )`·백틱은 남긴다 — 셸이 실행하는 곳. 탐지·정책 검사에 쓴다.
    첫 판은 정규식으로 따옴표를 가려서 주석 속 `don't`나 `\\"`가 PR 생성 명령까지 가렸다.
    """
    n = len(text)
    full, exe, clean = list(text), list(text), list(text)

    def blank(bufs, a, b):
        for buf in bufs:
            for k in range(a, min(b, n)):
                buf[k] = " "

    def normal(i, closer):
        depth = 0
        while i < n:
            c = text[i]
            if closer == ")" and c == "(":
                depth += 1
            elif closer == ")" and c == ")":
                if depth == 0:
                    return i
                depth -= 1
            elif closer == "`" and c == "`":
                return i
            if c == "\\":
                nxt = text[i + 1] if i + 1 < n else ""
                if nxt == "\n":
                    blank((full, exe, clean), i, i + 2)
                elif nxt.isalnum():
                    blank((full, exe), i, i + 1)  # `\gh`는 gh다
                    i += 1
                    continue
                else:
                    blank((full, exe), i, i + 2)
                i += 2
                continue
            if c == "'":
                j = text.find("'", i + 1)
                j = n - 1 if j < 0 else j
                blank((full, exe), i, j + 1)
                i = j + 1
                continue
            if c == '"':
                i = dquote(i)
                continue
            if c == "#" and (i == 0 or text[i - 1] in " \t\n;&|()`"):
                j = text.find("\n", i)
                j = n if j < 0 else j
                blank((full, exe, clean), i, j)
                i = j
                continue
            i += 1
        return n

    def dquote(i):
        blank((full, exe), i, i + 1)
        j = i + 1
        while j < n and text[j] != '"':
            if text[j] == "\\":
                blank((full, exe), j, j + 2)
                j += 2
                continue
            if text[j] == "$" and j + 1 < n and text[j + 1] == "(":
                end = normal(j + 2, ")")
                blank((full,), j, end + 1)  # exe에는 남긴다 — 셸이 실행한다
                j = end + 1
                continue
            if text[j] == "`":
                end = normal(j + 1, "`")
                blank((full,), j, end + 1)
                j = end + 1
                continue
            blank((full, exe), j, j + 1)
            j += 1
        blank((full, exe), j, j + 1)
        return j + 1

    normal(0, None)
    return "".join(full), "".join(exe), "".join(clean)


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def simple_commands(masked):
    """구분자로 나눈 [(시작, 끝, 앞 구분자, 뒤 구분자)]. 빈 토막 포함."""
    out, last, before = [], 0, ""
    for m in SEP.finditer(masked):
        out.append((last, m.start(), before, m.group(0)))
        before, last = m.group(0), m.end()
    out.append((last, len(masked), before, ""))
    return out


def leading_cd(full, clean, cwd):
    """명령 맨 앞의 `cd <리터럴>`. (디렉터리, 그 cd의 (시작, 끝) 또는 None, 이유)."""
    cmds = simple_commands(full)
    k = 0
    while k < len(cmds) and not full[cmds[k][0]:cmds[k][1]].strip():
        if cmds[k][3] not in ("\n", ";", ""):
            return cwd, None, None
        k += 1
    if k >= len(cmds):
        return cwd, None, None
    a, b, _before, after = cmds[k]
    try:
        w = shlex.split(clean[a:b], posix=True)
    except ValueError:
        return cwd, None, None
    if not w or w[0] != "cd":
        return cwd, None, None
    args = w[1:]
    while args and args[0] in ("-P", "-L", "-e", "-@", "--"):
        args = args[1:]
    if len(args) != 1:
        return None, None, "맨 앞 `cd`의 대상이 하나가 아니다"
    arg = args[0]
    if arg == "-" or "$" in arg or "`" in arg or "~" in arg[1:]:
        return None, None, "`cd %s`의 대상은 셸이 돌아야 안다" % arg
    ok = after in ("&&", ";", "\n", "")
    if after == "||" and k + 1 < len(cmds):
        a2, b2, _, after2 = cmds[k + 1]
        ok = re.fullmatch(r"\s*exit(\s+\d+)?\s*", full[a2:b2]) is not None and after2 in ("&&", ";", "\n", "")
    if not ok:
        return None, None, "맨 앞 `cd` 뒤가 `&&`·`;`·줄바꿈·`|| exit`가 아니다"
    d = os.path.normpath(os.path.join(cwd, os.path.expanduser(arg)))
    if not os.path.isdir(d):
        return None, None, "`cd` 대상 디렉터리가 없다: %s" % d
    return d, (a, b), None


def policy(exe, allowed_cd):
    """허용 목록 밖의 모양이면 이유, 아니면 None. 그리고 push refspec 목록."""
    if re.search(r"(?<!\$)\(", exe):
        return "맨 괄호(서브셸·함수 정의)가 있다", []
    refspecs = []
    for a, b, _before, _after in simple_commands(exe):
        words = [(m.start() + a, m.group(0)) for m in WORD.finditer(exe[a:b])]
        names = [w for _, w in words]
        for pos, w in words:
            if w in CD and not (allowed_cd and allowed_cd[0] <= pos < allowed_cd[1]):
                return "맨 앞이 아닌 자리에 `%s`가 있다 — 돌았는지·어디서 돌았는지 셸이 돌아야 안다" % w, []
            if w in CONTROL:
                return "제어 구조(`%s`)가 있다" % w, []
            if w in OPAQUE or (w == "." and pos == (words[0][0] if words else -1)):
                return "`%s`가 있다 — 안에서 무엇을 하는지 모른다" % w, []
        for i, w in enumerate(names):
            base = w.rsplit("/", 1)[-1]
            if base == "git":
                j = i + 1
                while j < len(names) and names[j].startswith("-"):
                    j += 2 if names[j] in GIT_ARG_OPTS else 1
                sub = names[j] if j < len(names) else ""
                if sub not in SAFE_GIT:
                    return ("`git %s`가 PR 생성과 같은 명령에 있다 — 훅은 명령이 돌기 전 HEAD로 판정하므로 "
                            "HEAD가 움직이면 리뷰 안 된 커밋이 PR에 들어간다. 따로 실행하고 리뷰한 뒤 연다" % (sub or "?")), []
                if sub == "push":
                    refspecs += [x for x in names[j + 1:] if ":" in x and not x.startswith("-")
                                 and "//" not in x and "@" not in x]
            if base == "gh" and "pr" in names[i + 1:i + 4] and "checkout" in names[i + 1:]:
                return "`gh pr checkout`가 PR 생성과 같은 명령에 있다 — HEAD가 움직인다", []
    return None, refspecs


def head_values(exe, clean, start):
    """그 PR 생성 명령의 `--head`/`-H` 값들(소유자 접두는 뗀다).

    명령의 끝은 괄호 깊이 0의 구분자다 — `$( … )` 안의 것은 끝이 아니다. 줄 이음은 `lex`가 가렸다.
    """
    stop, depth = len(exe), 0
    for m in re.finditer(r"&&|\|\||[;|&\n()`]", exe[start:]):
        t = m.group(0)
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
            if depth < 0:
                stop = start + m.start()
                break
        elif depth == 0:
            stop = start + m.start()
            break
    vals = []
    for m in re.finditer(r"(?<![\w-])(?:--head(?![\w-])|-H)", exe[start:stop]):
        p = start + m.end()
        rest = clean[p:stop].lstrip("= \t")
        if rest[:1] in ("'", '"'):
            j = rest.find(rest[0], 1)
            val = rest[1:j] if j > 0 else rest[1:]
        else:
            val = re.match(r"[^\s;&|()<>`]*", rest).group(0)
        vals.append(val.split(":")[-1] if val else "")
    return vals


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


SIMPLE = ("명령을 단순하게 쓴다 — 세션을 그 워크트리로 옮기거나(EnterWorktree), "
          "`cd <경로> && git push && <PR 생성>` 한 줄, 또는 `--head <브랜치>`. 커밋은 따로 한 뒤 리뷰한다.")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 막지 않는다. 게이트가 사고를 만들면 안 된다

    command = (payload.get("tool_input") or {}).get("command") or ""
    full, exe, clean = lex(strip_heredocs(command))
    found = list(GH.finditer(exe))
    if not found:
        return 0

    cwd = os.path.normpath(payload.get("cwd") or os.getcwd())
    d, cd_span, why = leading_cd(full, clean, cwd)
    if d is None:
        return block("PR이 어느 커밋인지 정하지 못했다 — %s. %s" % (why, SIMPLE))
    why, refspecs = policy(exe, cd_span)
    if why:
        return block("PR 생성이 든 명령이 허용하는 모양이 아니다 — %s. %s" % (why, SIMPLE))

    heads = [head_values(exe, clean, m.start()) for m in found]
    for h in heads:
        if len(h) > 1 or (h and not h[0]):
            return block("한 PR 생성에 `--head`가 둘 이상이거나 값이 없다 — gh는 마지막 것을 쓴다. %s" % SIMPLE)
    top = git("-C", d, "rev-parse", "--show-toplevel")
    if not top:
        if d == cwd and not any(heads):
            return 0  # 저장소 밖 — 첫 판부터의 동작
        return block("PR 생성 위치가 git 저장소가 아니라(%s) `--head`·`cd`가 가리키는 것을 확인할 수 없다." % d)

    current = git("-C", top, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    for spec in refspecs:
        src, dst = spec.lstrip("+").split(":", 1)
        dst = dst[len("refs/heads/"):] if dst.startswith("refs/heads/") else dst
        names = {current} | {h[0] for h in heads if h}
        if dst not in names or src not in ({"HEAD"} | names):
            return block("`git push %s` — 판정하는 브랜치(%s)와 다른 커밋이 원격에 올라갈 수 있다. PR은 원격 "
                         "브랜치로 만들어진다." % (spec, ", ".join(sorted(names))))

    for h in heads:
        if h:
            branch = h[0]
            sha = git("-C", top, "rev-parse", "--verify", "-q", "refs/heads/%s^{commit}" % branch)
            if not sha:
                return block("`--head %s` 브랜치가 로컬에 없어 무엇이 PR이 되는지 확인할 수 없다." % branch, branch)
            where = checkout_of(branch, top) or top
        else:
            sha = git("-C", top, "rev-parse", "HEAD")
            if not sha:
                return 0  # 커밋이 없는 저장소
            branch, where = current, top
        try:
            with open(os.path.join(where, MARKER), encoding="utf-8") as f:
                reviewed = f.read().strip()
        except OSError:
            reviewed = ""
        if reviewed == sha:
            continue
        stat = git("-C", where, "diff", "--stat", "main..." + sha) or "(main과의 차이를 못 읽었다)"
        if reviewed:
            why = "%s의 마커는 %s에 찍혀 있는데 PR이 될 커밋은 %s다 — 리뷰 뒤에 커밋이 더 쌓였거나 다른 브랜치의 마커다." % (
                where, reviewed[:8], sha[:8])
        else:
            why = "%s에 리뷰 마커가 없다 — 이 브랜치는 아직 리뷰되지 않았다." % where
        return block(why, branch, sha, stat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
