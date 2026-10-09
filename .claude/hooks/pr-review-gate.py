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

## 판정 (이슈 #111)

**PR 생성은 그 Bash 호출의 유일한 명령이어야 한다.** 앞에 `cd <리터럴 경로>` 하나(뒤가 `&&`·`;`·
줄바꿈, 또는 `|| exit [N]`)만 붙일 수 있다. push·commit은 따로 호출한다. 그 밖의 모양은 막는다.
- PR이 될 커밋: `--head <브랜치>`(`-H`·`-fH wt`·`-Hwt`·`--head=`·`소유자:`)면 그 브랜치의 로컬 끝, 아니면
  그 디렉터리(cwd 또는 맨 앞 `cd`)의 HEAD. `--head`가 둘 이상이거나 리터럴이 아니면 막는다.
- 마커: 그 브랜치가 체크아웃된 워크트리의 `.claude/.pr-review-ok`. 체크아웃마다 하나다.
- **원격 추적 ref**(`<브랜치>@{upstream}`, 없으면 `origin/<브랜치>`)도 그 커밋과 같아야 한다. PR은 원격
  브랜치로 만들어진다 — 푸시하지 않았거나 원격이 다른 커밋을 가리키면(남의 푸시, `push main:wt`) 막는다.
  최근 푸시·페치 기준이다(훅은 네트워크를 쓰지 않는다).
- `--body "$(cat <<'EOF' … EOF)"`처럼 인자 속 명령 치환은 `cat`만 허용한다.

**왜 이렇게 좁은가.** 첫 판은 `cwd`의 HEAD·마커만 읽어, 세션이 메인 체크아웃에 있고 `cd <워크트리> && …`로
PR을 열면 메인의 것으로 판정했다 — 메인 마커가 메인 HEAD와 같기만 하면 리뷰 안 된 워크트리 브랜치가 통과했다.
고치면서 둘째 판은 명령 안의 `cd`를 **따라가고**, 셋째 판은 같은 호출 안의 명령을 **허용 목록**으로 걸렀는데
둘 다 샜다(서브셸·조건·`case`·함수 속 `cd`, 래퍼·경로·따옴표 뒤 `git commit`, `symbolic-ref`, `fetch
--update-head-ok`, `npm version`, `-c remote.origin.push=` … — 코드 리뷰 세 번이 짚고 test-detect가 지킨다).
훅은 명령이 돌기 **전에** 판정하므로, 같은 호출 안에서 무엇이든 돌 수 있으면 판정이 무의미해진다.
그래서 같은 호출 안에 다른 명령을 두지 않는다. 막히면 우회하지 말고 나눠 쓴다.

**정하지 못하면 막는다.** 입력을 못 읽는 경우(아래 `main`)와 다르다 — 그건 게이트가 사고를 만들지 않으려고
열어 두지만, 이건 **PR 생성이 확실한데 무엇을 여는지 모르는** 경우라 열면 바로 위조 경로가 된다.

## 탐지

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그 사고를 냈다 — 훅을 설명하는
문서를 heredoc으로 쓰는 명령이 게이트에 막혔다. 그래서 **셸 낱말 단위**로 본다: heredoc 본문과 `#` 주석을
걷고, 맨 위 구분자로 단순 명령을 나눈 뒤 `shlex`로 따옴표를 벗긴 낱말에서 `gh`(또는 `$변수`)·`pr`·`create|new`가
차례로 나오면 PR 생성이다. 그래서 `"gh" pr 'create'`·`g\\h`는 잡고, `grep 'gh pr create'`·`git commit -m "…gh pr
create…"`처럼 한 낱말 속 문자열은 안 잡는다. 낱말 속 `$( … )`·백틱은 셸이 실행하므로 안을 다시 본다.
낱말로 못 나누는 토막은 글자로 찾는다(닫는 쪽 기본값).

## 알려진 한계 (이슈 #114)

- `strip_heredocs`는 따옴표 상태를 추적하지 않는다. 따옴표 안의 `<< 단어`를 heredoc 여는 줄로 오인하면
  뒤따르는 줄을 종료 태그까지 걷어낸다. 그 안에 PR 생성 명령이 있으면 못 본다.
- 작은따옴표 속 명령(`bash -c '…'`, `eval '…'`)·함수·별칭·`source`한 스크립트 안의 PR 생성.
- 판정 뒤에 다른 프로세스가 브랜치를 바꾸는 경우(동시 작업), 원격 추적 ref가 낡은 경우.
- `--repo`·`GH_REPO`로 다른 저장소를 여는 것.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
VERBS = ("create", "new")
# here-string `<<<`는 heredoc이 아니다. 태그는 따옴표 안이면 무엇이든, 아니면 구분자 전까지(`END-X`).
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(?:'([^']+)'|\"([^\"]+)\"|([^\s;&|()<>'\"]+))")
SEP = re.compile(r"&&|\|\||;;|[;|&()\n`]")
# gh pr create의 값을 받는 플래그 — 값이 다음 낱말이면 건너뛴다(그 값이 `-H…`처럼 보여도 플래그가 아니다)
VALUE_SHORT = set("BbFtalmprRTH")
VALUE_LONG = {"--base", "--body", "--body-file", "--title", "--assignee", "--label", "--milestone",
              "--project", "--reviewer", "--repo", "--template", "--recover", "--head"}
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
    """(full, clean) — 둘 다 text와 **같은 길이**다.

    clean: `#` 주석과 줄 이음(`\\` + 줄바꿈)만 공백. 셸 낱말로 나눌 때 쓴다.
    full:  clean에서 따옴표 안(`'…'`·`"…"`·`$'…'`)과 이스케이프까지 공백. 맨 위 구분자를 찾을 때 쓴다.
    첫 판은 정규식으로 따옴표를 가려서 주석 속 `don't`나 `\\"`가 PR 생성 명령까지 가렸다.
    """
    n = len(text)
    full, clean = list(text), list(text)

    def blank(bufs, a, b):
        for buf in bufs:
            for k in range(a, min(b, n)):
                buf[k] = " "

    i = 0
    while i < n:
        c = text[i]
        if c == "\\":
            if i + 1 < n and text[i + 1] == "\n":
                blank((full, clean), i, i + 2)
            else:
                blank((full,), i, i + 2)
            i += 2
            continue
        if c == "$" and i + 1 < n and text[i + 1] == "'":  # ANSI-C — 안의 `\'`는 닫는 따옴표가 아니다
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            blank((full,), i, j + 1)
            i = j + 1
            continue
        if c == "'":
            j = text.find("'", i + 1)
            j = n - 1 if j < 0 else j
            blank((full,), i, j + 1)
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            blank((full,), i, j + 1)
            i = j + 1
            continue
        if c == "#" and (i == 0 or text[i - 1] in " \t\n;&|()`"):
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank((full, clean), i, j)
            i = j
            continue
        i += 1
    return "".join(full), "".join(clean)


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def split_top(command):
    """맨 위 단순 명령들 — ([(clean 토막, 시작)], [구분자들]). heredoc·주석을 걷은 뒤다."""
    full, clean = lex(strip_heredocs(command))
    segs, seps, last = [], [], 0
    for m in SEP.finditer(full):
        segs.append((clean[last:m.start()], last))
        seps.append(m.group(0))
        last = m.end()
    segs.append((clean[last:], last))
    return segs, seps


def substitutions(word):
    """낱말 속 `$( … )`·백틱의 안쪽 텍스트들."""
    out, i = [], 0
    while i < len(word):
        if word.startswith("$(", i):
            depth, j = 0, i + 2
            while j < len(word):
                if word[j] == "(":
                    depth += 1
                elif word[j] == ")":
                    if depth == 0:
                        break
                    depth -= 1
                j += 1
            out.append(word[i + 2:j])
            i = j + 1
        elif word[i] == "`":
            j = word.find("`", i + 1)
            j = len(word) if j < 0 else j
            out.append(word[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def is_pr_words(w):
    """낱말 열에 `gh`(또는 `$변수`) … `pr` … `create|new`가 차례로 있는가."""
    for i, x in enumerate(w):
        if x.rsplit("/", 1)[-1] == "gh" or x.startswith("$"):
            rest = w[i + 1:]
            if "pr" in rest and any(v in rest[rest.index("pr") + 1:] for v in VERBS):
                return True
    return False


def has_pr(command, depth=0):
    """이 명령 어딘가에서 PR 생성이 도는가. 모르면 참."""
    if depth > 8:
        return True
    segs, _ = split_top(command)
    for seg, _start in segs:
        if not seg.strip():
            continue
        try:
            w = shlex.split(seg, posix=True)
        except ValueError:
            if re.search(r"gh.*\bpr\b.*\b(?:" + "|".join(VERBS) + r")\b", seg, re.S):
                return True
            continue
        if is_pr_words(w):
            return True
        for x in w:
            if any(has_pr(inner, depth + 1) for inner in substitutions(x)):
                return True
    return False


def parse_heads(args):
    """gh pr create 인자에서 `--head` 값들. pflag처럼 짧은 플래그 묶음(`-fH wt`·`-Hwt`)도 푼다."""
    heads, i = [], 0
    while i < len(args):
        t = args[i]
        if t == "--":
            break
        if t.startswith("--"):
            name = t.split("=", 1)[0]
            if name == "--head":
                if "=" in t:
                    heads.append(t.split("=", 1)[1])
                else:
                    heads.append(args[i + 1] if i + 1 < len(args) else "")
                    i += 1
            elif name in VALUE_LONG and "=" not in t:
                i += 1
        elif t.startswith("-") and len(t) > 1:
            cluster = t[1:]
            for ci, ch in enumerate(cluster):
                if ch in VALUE_SHORT:
                    rest = cluster[ci + 1:]
                    if not rest:
                        val = args[i + 1] if i + 1 < len(args) else ""
                        i += 1
                    else:
                        val = rest[1:] if rest.startswith("=") else rest
                    if ch == "H":
                        heads.append(val)
                    break
        i += 1
    return heads


def shape(command, cwd):
    """허용하는 모양이면 (디렉터리, --head 값 또는 None, None), 아니면 (None, None, 이유)."""
    segs, seps = split_top(command)
    body = [(i, s) for i, (s, _) in enumerate(segs) if s.strip()]
    bad = [s for s in seps if s not in ("&&", ";", "\n", "||")]
    if bad:
        return None, None, "`%s`가 있다(파이프·백그라운드·서브셸·명령 치환)" % bad[0]
    if not body:
        return None, None, "PR 생성 명령을 찾지 못했다"

    def between(i, j):  # segs[i]와 segs[j] 사이의 구분자들
        return seps[i:j]

    words = []
    for i, s in body:
        try:
            words.append(shlex.split(s, posix=True))
        except ValueError:
            return None, None, "명령을 셸 낱말로 나누지 못했다: %r" % s.strip()[:60]
    d = cwd
    k = 0
    if len(body) >= 2 and words[0] and words[0][0] == "cd":
        args = words[0][1:]
        while args and args[0] in ("-P", "-L", "-e", "-@", "--"):
            args = args[1:]
        if len(args) != 1:
            return None, None, "맨 앞 `cd`의 대상이 하나가 아니다"
        arg = args[0]
        if arg == "-" or "$" in arg or "`" in arg:
            return None, None, "`cd %s`의 대상은 셸이 돌아야 안다" % arg
        mid = between(body[0][0], body[1][0])
        if "||" in mid:
            if (len(body) != 3 or mid != ["||"] or not re.fullmatch(r"exit(\s+\d+)?", " ".join(words[1]))
                    or "||" in between(body[1][0], body[2][0])):
                return None, None, "맨 앞 `cd` 뒤가 `&&`·`;`·줄바꿈·`|| exit`가 아니다"
            k = 2
        else:
            k = 1
        d = os.path.normpath(os.path.join(cwd, os.path.expanduser(arg)))
        if not os.path.isdir(d):
            return None, None, "`cd` 대상 디렉터리가 없다: %s" % d
    if len(body) != k + 1:
        return None, None, "PR 생성 말고 다른 명령이 같은 호출에 있다"
    if "||" in seps[body[k][0]:]:
        return None, None, "PR 생성 뒤에 `||`가 있다"
    w = words[k]
    if len(w) < 3 or w[0] != "gh" or w[1] != "pr" or w[2] not in VERBS:
        return None, None, "PR 생성은 `gh pr create …` 그대로 써야 한다(환경변수·래퍼·경로·변수 없이)"
    for x in w[3:]:
        for inner in substitutions(x):
            if not re.fullmatch(r"\s*cat(?:\s+<<-?\s*\S+|\s+[^\s;&|()`$<>]+)?\s*", strip_heredocs(inner)):
                return None, None, "인자 속 명령 치환은 `cat`만 허용한다: %r" % inner.strip()[:40]
    heads = parse_heads(w[3:])
    if len(heads) > 1:
        return None, None, "`--head`가 둘 이상이다 — gh는 마지막 것을 쓴다"
    if heads and (not heads[0] or "$" in heads[0] or "`" in heads[0]):
        return None, None, "`--head` 값이 리터럴이 아니다"
    return d, (heads[0].split(":")[-1] if heads else None), None


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


SIMPLE = ("PR 생성은 그 호출의 유일한 명령으로 쓴다 — push·commit은 따로 호출하고, 워크트리면 세션을 옮기거나"
          "(EnterWorktree) `cd <경로> && gh pr create …` 또는 `gh pr create --head <브랜치> …`.")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # 입력을 못 읽으면 막지 않는다. 게이트가 사고를 만들면 안 된다

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not has_pr(command):
        return 0

    cwd = os.path.normpath(payload.get("cwd") or os.getcwd())
    d, head, why = shape(command, cwd)
    if d is None:
        return block("PR 생성 명령이 허용하는 모양이 아니다 — %s. %s" % (why, SIMPLE))
    top = git("-C", d, "rev-parse", "--show-toplevel")
    if not top:
        if d == cwd and not head:
            return 0  # 저장소 밖 — 첫 판부터의 동작
        return block("PR 생성 위치가 git 저장소가 아니라(%s) `--head`·`cd`가 가리키는 것을 확인할 수 없다." % d)

    if head:
        branch = head
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
    if reviewed != sha:
        stat = git("-C", where, "diff", "--stat", "main..." + sha) or "(main과의 차이를 못 읽었다)"
        if reviewed:
            why = "%s의 마커는 %s에 찍혀 있는데 PR이 될 커밋은 %s다 — 리뷰 뒤에 커밋이 더 쌓였거나 다른 브랜치의 마커다." % (
                where, reviewed[:8], sha[:8])
        else:
            why = "%s에 리뷰 마커가 없다 — 이 브랜치는 아직 리뷰되지 않았다." % where
        return block(why, branch, sha, stat)

    up = (git("-C", top, "rev-parse", "--verify", "-q", "refs/heads/%s@{upstream}" % branch)
          or git("-C", top, "rev-parse", "--verify", "-q", "refs/remotes/origin/%s" % branch))
    if not up:
        return block("`%s`가 원격에 없다(추적 ref 없음) — 리뷰한 커밋을 먼저 푸시한다(따로 호출)." % branch, branch, sha)
    if up != sha:
        return block("원격 `%s`(%s)가 리뷰한 커밋(%s)과 다르다 — PR은 원격 브랜치로 만들어진다. 리뷰한 커밋을 푸시했는가, "
                     "원격에 다른 커밋이 올라가 있지 않은가." % (branch, up[:8], sha[:8]), branch, sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
