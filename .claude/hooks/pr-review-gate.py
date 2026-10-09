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

**이 훅은 실수를 막는다 — 일부러 우회하는 것은 막지 못한다.** 명령이 돌기 전에 문자열만 보고 판정하므로
셸이 할 수 있는 모든 일을 따라갈 수 없다. 그래서 판정할 수 있는 좁은 모양만 열고 나머지는 막는다.

## 판정 (이슈 #111)

**PR 생성은 그 Bash 호출의 유일한 명령이어야 한다.** 앞에 `cd <리터럴 경로>` 하나(뒤가 `&&` 또는
`|| exit [N]`), 뒤에 출력만 받는 파이프(`| tail`·`head`·`cat`·`tee`), 무해한 gh 환경변수 접두
(`GH_PROMPT_DISABLED=1` 등 `SAFE_ENV`)만 붙일 수 있다. push·commit은 따로 호출한다. 그 밖의 모양은 막는다.
- PR이 될 커밋: `--head <브랜치>`(`-H`·`-fH wt`·`-Hwt`·`--head=`)면 그 브랜치의 로컬 끝, 아니면 그 디렉터리
  (cwd 또는 맨 앞 `cd`)의 HEAD. `--head`가 둘 이상이거나 리터럴이 아니거나 `소유자:`(포크)면 막는다.
- 마커: 그 브랜치가 체크아웃된 워크트리의 `.claude/.pr-review-ok`. 체크아웃마다 하나다.
- **원격 브랜치**(`remote_branch` — 기본 브랜치가 아닌 추적 설정, 아니면 `origin <브랜치>`)의 끝도 그 커밋과
  같아야 한다. PR은 원격 브랜치로 만들어진다 — 푸시하지 않았거나 원격이 다른 커밋을 가리키면 막는다.
  추적 ref가 아니라 `ls-remote`로 **원격에 직접** 묻는다(이슈 #114 — 추적 ref는 남이 민 뒤에 낡는다). 못 읽으면 막는다.
- `--repo`·`-R`(없으면 훅 프로세스의 `GH_REPO`)는 그 원격과 같은 `소유자/저장소`여야 한다. 둘 이상·비리터럴이면 막는다.
- 인자 속 명령 치환은 `cat`만(`--body "$(cat <<'EOF' … EOF)"`). heredoc 태그는 따옴표를 쳐야 한다 —
  따옴표 없는 heredoc 본문의 `$( … )`는 PR 생성 **전에** 실행된다.
- `cd X;`·줄바꿈은 안 된다 — `cd`가 실패해도 다음 줄의 PR 생성이 원래 디렉터리에서 돈다.

**왜 이렇게 좁은가.** 첫 판은 `cwd`의 HEAD·마커만 읽어, 세션이 메인 체크아웃에 있고 `cd <워크트리> && …`로
PR을 열면 메인의 것으로 판정했다 — 메인 마커가 메인 HEAD와 같기만 하면 리뷰 안 된 워크트리 브랜치가 통과했다.
고치면서 명령 안의 `cd`를 **따라가는** 판, 같은 호출 안의 명령을 **허용 목록**으로 거르는 판을 거쳤는데 둘 다
샜다(코드 리뷰 다섯 번이 짚었고 test-detect가 지킨다). 같은 호출 안에서 무엇이든 돌 수 있으면 판정이 무의미하다.
다섯째 리뷰는 정직한 PR 명령 중 리뷰 안 된 커밋을 통과시키는 것을 찾지 못했다 — 실사용 차단만 나와 풀었다.

**정하지 못하면 막는다.** 입력을 못 읽는 경우(아래 `main`)와 다르다 — 그건 게이트가 사고를 만들지 않으려고
열어 두지만, 이건 **PR 생성이 확실한데 무엇을 여는지 모르는** 경우라 열면 바로 위조 경로가 된다.

## 탐지

⚠ **명령문 어디에나 있는 문자열을 잡으면 안 된다.** 첫 판에서 정확히 그 사고를 냈다 — 훅을 설명하는
문서를 heredoc으로 쓰는 명령이 게이트에 막혔다. 그래서 **셸 낱말 단위**로 본다. `lex`가 한 번 훑으며
따옴표·이스케이프·`#` 주석·줄 이음·heredoc 본문·산술 `$(( ))`을 가리고, **실제로 실행되는** 명령 치환
(`$( … )`·백틱 — 따옴표 밖이나 큰따옴표 안)만 따로 모은다. 맨 위 구분자로 나눈 단순 명령을 `shlex`로
벗긴 낱말에서 `gh`(또는 `$변수`)·`pr`·`create|new`가 차례로 나오면 PR 생성이다. 실행되는 명령 치환,
`bash -c`·`eval`의 인자, 셸에 먹이는 heredoc 본문, 따옴표 없는 heredoc 본문 속 치환은 안을 다시 본다.
그래서 `"gh" pr 'create'`·`g\\h`·`url="$(…)"`는 잡고, `grep 'gh pr create'`·작은따옴표 커밋 메시지 속
백틱처럼 글자인 것은 안 잡는다. 낱말로 못 나누는 토막은 글자로 찾는다(닫는 쪽 기본값).

셸이 읽는 **스크립트 파일**(`bash x.sh`·`source x`·`. x`·셸 shebang의 `./x`)은 파일을 열어 같은 탐지를
돌린다(이슈 #114 — 셸이 막는 복잡한 명령을 `_workspace/`의 스크립트로 돌리는 것이 이 저장소의 실사용이다).
상대 경로는 cwd와 맨 위 `cd <리터럴>` 대상에서 찾고, 못 찾으면 PR 생성이 확실하지 않으니 막지 않는다.
`gh api`로 `repos/…/pulls`에 POST하거나 GraphQL `createPullRequest`를 부르는 것도 PR 생성으로 본다. 둘 다
잡히면 `gh pr create` 모양이 아니라 막힌다 — PR은 `gh pr create`로만 연다.

## 알려진 한계 (이슈 #114)

남은 것은 일부러 감싸야 생기는 모양이거나 훅이 원리적으로 못 보는 곳이다.
- 사용자 프로필의 함수·별칭, 셸 이름을 바꾼 사본(`/tmp/x -c …`), 셸이 아닌 실행기(python `subprocess`·
  `npm run`·`make`) 안의 PR 생성. 경로가 변수인 스크립트(`bash "$X"`), 표준 입력으로 먹이는 스크립트
  (`bash < x.sh`·`cat x.sh | bash`), shebang도 `.sh`도 없이 실행하는 파일, `gh api -F query=@파일`.
- 판정과 PR 생성 사이에 다른 프로세스가 브랜치·원격을 바꾸는 경우(동시 작업).
- 저장소에 원격이 여럿일 때 gh가 고르는 기본 저장소(`gh repo set-default`) — 훅은 브랜치의 원격으로 판정한다.
- 웹 UI·`curl`로 여는 PR. 훅을 지나지 않거나 문자열 검사로 못 본다.
"""
import json
import os
import re
import shlex
import subprocess
import sys

# `gh` `pr` `create`를 붙여 쓰지 않는다 — 이 파일 자체가 게이트에 걸린다.
VERBS = ("create", "new")
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
# 명령 구분자. `2>&1`·`&>`·`>&`·`>|`의 `&`·`|`는 리다이렉션이다.
SEP = re.compile(r"&&|\|\||;;|(?<![<>])&(?!>)|(?<!>)\||[;()\n`]")
# gh pr create의 값을 받는 플래그 — 값이 다음 낱말이면 건너뛴다(그 값이 `-H…`처럼 보여도 플래그가 아니다)
VALUE_SHORT = set("BbFtalmprRTH")
VALUE_LONG = {"--base", "--body", "--body-file", "--title", "--assignee", "--label", "--milestone",
              "--project", "--reviewer", "--repo", "--template", "--recover", "--head"}
CAT_ONLY = re.compile(r"\s*cat(?:\s+<<-?\s*\S+|\s+[^\s;&|()`$<>]+)?\s*")
MARKER = ".claude/.pr-review-ok"


class Lexed:
    """`lex`의 결과. full·clean은 원문과 **같은 길이**다.

    full:  따옴표 안·이스케이프·주석·줄 이음·heredoc 본문·산술을 공백으로. 맨 위 구분자를 찾을 때 쓴다.
    clean: 주석·줄 이음·heredoc 본문만 공백으로. `shlex`로 낱말을 나눌 때 쓴다.
    subs:  실행되는 명령 치환의 안쪽 텍스트들(깊이 무관).
    docs:  heredoc들 — (여는 위치, 태그에 따옴표가 있었나, 본문).
    """

    def __init__(self, text):
        self.t, self.n = text, len(text)
        self.full, self.clean = list(text), list(text)
        self.subs, self.docs, self.pending = [], [], []
        self.normal(0, None)
        self.full, self.clean = "".join(self.full), "".join(self.clean)

    def blank(self, a, b, both=False):
        for k in range(a, min(b, self.n)):
            self.full[k] = " "
            if both:
                self.clean[k] = " "

    def heredoc_open(self, i):
        """`<<` 다음의 태그를 읽어 pending에 넣는다. 태그 끝 위치를 돌려준다."""
        t, n = self.t, self.n
        j = i + 2
        strip_tabs = j < n and t[j] == "-"
        j += 1 if strip_tabs else 0
        while j < n and t[j] in " \t":
            j += 1
        tag, quoted = [], False
        while j < n and t[j] not in " \t\n;&|()<>":
            c = t[j]
            if c in "'\"":
                e = t.find(c, j + 1)
                e = n if e < 0 else e
                tag.append(t[j + 1:e])
                quoted, j = True, e + 1
            elif c == "\\":
                tag.append(t[j + 1:j + 2])
                quoted, j = True, j + 2
            else:
                tag.append(c)
                j += 1
        if tag:
            self.pending.append((i, "".join(tag), quoted, strip_tabs))
        return j

    def heredoc_bodies(self, i):
        """줄바꿈(i) 뒤에서 대기 중인 heredoc 본문들을 읽고 가린다. 다음 위치를 돌려준다."""
        t, n = self.t, self.n
        j = i + 1
        for pos, tag, quoted, strip_tabs in self.pending:
            start = j
            while True:
                e = t.find("\n", j)
                e = n if e < 0 else e
                line = t[j:e].lstrip("\t") if strip_tabs else t[j:e]
                if line == tag or e >= n:
                    self.docs.append((pos, quoted, t[start:j if line == tag else e]))
                    self.blank(start, e, both=True)
                    j = e + 1
                    break
                j = e + 1
        self.pending = []
        return j

    def subst(self, i, closer):
        """i는 `$(`의 `(` 다음이나 백틱 다음. 안을 normal로 읽고 닫는 위치를 돌려준다."""
        end = self.normal(i, closer)
        self.subs.append(self.t[i:end])
        return end

    def normal(self, i, closer):
        t, n = self.t, self.n
        depth = 0
        while i < n:
            c = t[i]
            if closer == ")" and c == "(":
                depth += 1
            elif closer == ")" and c == ")":
                if depth == 0:
                    return i
                depth -= 1
            elif closer == "`" and c == "`":
                return i
            if c == "\\":
                self.blank(i, i + 2, both=(i + 1 < n and t[i + 1] == "\n"))
                i += 2
            elif t.startswith("$((", i):  # 산술 — 코드도 heredoc도 아니다
                d, j = 0, i + 1
                while j < n:
                    d += {"(": 1, ")": -1}.get(t[j], 0)
                    j += 1
                    if d == 0:
                        break
                self.blank(i, j)
                i = j
            elif t.startswith("$(", i):
                i = self.subst(i + 2, ")") + 1
            elif c == "`":
                i = self.subst(i + 1, "`") + 1
            elif t.startswith("$'", i):  # ANSI-C — 안의 `\'`는 닫는 따옴표가 아니다
                j = i + 2
                while j < n and t[j] != "'":
                    j += 2 if t[j] == "\\" else 1
                self.blank(i, j + 1)
                i = j + 1
            elif c == "'":
                j = t.find("'", i + 1)
                j = n - 1 if j < 0 else j
                self.blank(i, j + 1)
                i = j + 1
            elif c == '"':
                i = self.dquote(i)
            elif c == "#" and (i == 0 or t[i - 1] in " \t\n;&|()`"):
                j = t.find("\n", i)
                j = n if j < 0 else j
                self.blank(i, j, both=True)
                i = j
            elif t.startswith("<<<", i):  # here-string — heredoc이 아니다. 둘째 `<`에서 다시 읽지 않게 통째로 넘긴다
                i += 3
            elif t.startswith("<<", i):
                i = self.heredoc_open(i)
            elif c == "\n" and self.pending:
                i = self.heredoc_bodies(i)
            else:
                i += 1
        return n

    def dquote(self, i):
        t, n = self.t, self.n
        start, j = i, i + 1
        while j < n and t[j] != '"':
            if t[j] == "\\":
                j += 2
            elif t.startswith("$(", j) and not t.startswith("$((", j):
                j = self.subst(j + 2, ")") + 1
            elif t[j] == "`":
                j = self.subst(j + 1, "`") + 1
            else:
                j += 1
        self.blank(start, j + 1)
        return j + 1


def git(*args):
    """실패하면 빈 문자열. 훅이 저장소 상태 때문에 죽으면 안 된다."""
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return ""


def git_ok(*args, timeout=10):
    """(성공했나, 표준출력). 실패와 빈 결과를 가려야 할 때 — `ls-remote`는 없는 브랜치에도 0으로 끝난다."""
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=timeout,
                           env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        return p.returncode == 0, p.stdout.strip()
    except Exception:
        return False, ""


def split_top(lx):
    """맨 위 단순 명령들 — ([(clean 토막, 시작, 끝)], [구분자들])."""
    segs, seps, last = [], [], 0
    for m in SEP.finditer(lx.full):
        segs.append((lx.clean[last:m.start()], last, m.start()))
        seps.append(m.group(0))
        last = m.end()
    segs.append((lx.clean[last:], last, len(lx.full)))
    return segs, seps


def words_of(seg):
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return None


def next_word(w, i):
    """i부터 플래그가 아닌 첫 낱말의 위치. `-R`·`--repo`는 값까지 건너뛴다."""
    while i < len(w) and w[i].startswith("-"):
        i += 2 if w[i] in ("-R", "--repo") else 1
    return i


def is_pr_words(w):
    """`gh`(또는 `$변수`) 다음 첫 낱말이 `pr`, 그다음 첫 낱말이 `create|new`인가.

    위치를 본다 — 첫 판은 뒤 어딘가에 `pr`·`create`가 있기만 하면 잡아서 `gh pr list --search create`·
    `gh issue create --label pr --label create`를 막았다(5차 코드 리뷰).
    """
    for i, x in enumerate(w):
        if x.rsplit("/", 1)[-1] == "gh" or x.startswith("$"):
            j = next_word(w, i + 1)
            if j < len(w) and w[j] == "pr":
                k = next_word(w, j + 1)
                if k < len(w) and w[k] in VERBS:
                    return True
    return False


WRAPPERS = {"env", "command", "exec", "sudo", "nohup", "time", "timeout", "nice", "xargs", "builtin"}


def command_index(w):
    """환경변수 접두와 래퍼(`env`·`timeout 60`·`sudo -u x` …)를 건너뛴 명령 낱말의 위치."""
    i = 0
    while i < len(w) and (re.match(r"^\w+=", w[i]) or w[i] in WRAPPERS or w[i].startswith("-")
                          or re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", w[i])):  # `timeout 5m`
        i += 1
    return i


def command_word(w):
    """명령 낱말의 이름(경로를 뗀다). 없으면 ""."""
    i = command_index(w)
    return w[i].rsplit("/", 1)[-1] if i < len(w) else ""


def shell_script(w):
    """`bash -c '…'`·`sh -lc "…"`의 스크립트, `eval …`의 인자. 없으면 None."""
    for i, x in enumerate(w):
        if x.rsplit("/", 1)[-1] in SHELLS:
            for j in range(i + 1, len(w) - 1):
                if w[j].startswith("-") and not w[j].startswith("--") and "c" in w[j][1:]:
                    return w[j + 1]
        if x == "eval":
            return " ".join(w[i + 1:])
    return None


def body_subs(body):
    """따옴표 없는 heredoc 본문 속 `$( … )`·백틱 — 셸이 펼친다. 큰따옴표 안과 같은 규칙이라 `Lexed`에 맡긴다
    (`"`는 본문에서 글자이므로 이스케이프한다)."""
    return Lexed('"' + body.replace('"', '\\"') + '"').subs


SHELL_VALUE_LONG = {"--rcfile", "--init-file"}


def script_path(w):
    """이 단순 명령이 셸로 읽는 스크립트 파일 — (경로, shebang을 봐야 하나). 없으면 None.

    `bash x.sh`·`sh -x x.sh`·`source x`·`. x`는 셸이 읽고, `./x`처럼 경로로 실행하는 것은 셸 shebang일 때만이다.
    """
    i = command_index(w)
    if i >= len(w):
        return None
    name = w[i].rsplit("/", 1)[-1]
    if name in ("source", "."):
        return (w[i + 1], False) if i + 1 < len(w) else None
    if name in SHELLS:
        j = i + 1
        while j < len(w) and w[j][:1] in "-+" and w[j] not in ("-", "--"):
            if not w[j].startswith("--") and ("c" in w[j][1:] or "s" in w[j][1:]):
                return None  # -c는 shell_script가, -s(표준 입력)는 셸에 먹이는 heredoc이 본다
            # 값을 받는 `-o`·`-O`는 묶음 끝에 와도 다음 낱말이 값이다(`bash -euo pipefail x.sh`)
            j += 2 if w[j] in SHELL_VALUE_LONG or (not w[j].startswith("--") and w[j][-1] in "oO") else 1
        j += 1 if j < len(w) and w[j] == "--" else 0
        return (w[j], False) if j < len(w) else None
    if "/" in w[i]:
        return w[i], True
    return None


def read_script(path, need_shebang, bases):
    """(실제 경로, 스크립트 본문). 경로를 못 풀거나(`$`), 없거나, 셸 스크립트가 아니면 None —
    PR 생성이 확실하지 않으니 막지 않는다."""
    if "$" in path or "`" in path:
        return None
    path = os.path.expanduser(path)
    for base in bases:
        f = os.path.join(base, path)
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text = fh.read(1 << 20)
        except OSError:
            continue
        if need_shebang:
            first = text.split("\n", 1)[0]
            if not first.startswith("#!"):
                if not f.endswith(".sh"):
                    continue
            else:
                argv = first[2:].split()
                if argv and argv[0].rsplit("/", 1)[-1] == "env":
                    argv = [a for a in argv[1:] if not a.startswith("-")]
                if not argv or argv[0].rsplit("/", 1)[-1] not in SHELLS:
                    continue
        return os.path.realpath(f), text
    return None


API_VALUE = {"-X", "--method", "-f", "--raw-field", "-F", "--field", "-H", "--header", "--input", "-q", "--jq",
             "-t", "--template", "--cache", "-p", "--preview", "--hostname"}
PULLS = re.compile(r"(?:https?://[^/]+(?:/api/v3)?)?/?repos/[^/]+/[^/]+/pulls/?(?:\?.*)?")


def is_api_pr(w):
    """`gh api`로 PR을 여는가 — `repos/o/r/pulls`에 POST(`-f`·`-F`·`--input`이 있으면 기본이 POST),
    또는 GraphQL `createPullRequest`."""
    for i, x in enumerate(w):
        if not (x.rsplit("/", 1)[-1] == "gh" or x.startswith("$")):
            continue
        j = next_word(w, i + 1)
        if j >= len(w) or w[j] != "api":
            continue
        args = w[j + 1:]
        if any("createPullRequest" in a for a in args):
            return True
        method, fields, endpoint, k = None, False, None, 0
        while k < len(args):
            a = args[k]
            if a.startswith("--"):
                name, eq, val = a.partition("=")
            elif a.startswith("-") and len(a) > 1:
                name, val = a[:2], a[2:]
                eq = val
            else:
                endpoint = endpoint or a
                k += 1
                continue
            if name in API_VALUE and not eq:
                val = args[k + 1] if k + 1 < len(args) else ""
                k += 1
            if name in ("-X", "--method"):
                method = val
            elif name in ("-f", "--raw-field", "-F", "--field", "--input"):
                fields = True
            k += 1
        if endpoint and PULLS.fullmatch(endpoint) and (method or ("POST" if fields else "GET")).upper() == "POST":
            return True
    return False


def has_pr(command, depth=0, lx=None, bases=(), seen=frozenset()):
    """이 명령 어딘가에서 PR 생성이 도는가. 모르면 참.

    bases: 상대 경로 스크립트를 찾을 디렉터리들. seen: 이미 연 스크립트 — 자기를 `source`하는 스크립트가
    깊이 한도에 닿아 「모르면 참」으로 막히지 않게 한 번만 본다.
    """
    if depth > 8:
        return True
    lx = lx or Lexed(command)
    segs, _ = split_top(lx)
    for seg, a, b in segs:
        if not seg.strip():
            continue
        w = words_of(seg)
        if w is None:
            # 따옴표 안은 가린 full에서 찾는다 — 따옴표 속 언급(`$'…'` 본문)까지 잡지 않게
            if re.search(r"\bgh\b.*\bpr\b.*\b(?:" + "|".join(VERBS) + r")\b", lx.full[a:b], re.S):
                return True
            continue
        if is_pr_words(w) or is_api_pr(w):
            return True
        script = shell_script(w)
        if script is not None and has_pr(script, depth + 1, bases=bases, seen=seen):
            return True
        found = script_path(w)
        read = found and read_script(found[0], found[1], bases)
        if read and read[0] not in seen:
            # 스크립트 안의 상대 경로는 그 스크립트의 디렉터리(`cd "$(dirname "$0")"`)나 안의 `cd <리터럴>` 대상일 수 있다
            inner = list(bases) + [os.path.dirname(read[0])]
            inner += cd_targets(Lexed(read[1]), bases[0] if bases else inner[-1])
            if has_pr(read[1], depth + 1, bases=inner, seen=seen | {read[0]}):
                return True
        fed = command_word(w) in SHELLS  # 명령 낱말이 셸일 때만 — `--label sh`는 아니다
        for pos, quoted, body in lx.docs:
            if a <= pos < b and fed and has_pr(body, depth + 1, bases=bases, seen=seen):
                return True
    if any(has_pr(s, depth + 1, bases=bases, seen=seen) for s in lx.subs):
        return True
    return any(has_pr(s, depth + 1, bases=bases, seen=seen)
               for _p, quoted, body in lx.docs if not quoted for s in body_subs(body))


def flag_values(args, long, short):
    """gh pr create 인자에서 한 플래그(`--head`·`-H`)의 값들. pflag처럼 짧은 플래그 묶음(`-fH wt`·`-Hwt`)도 푼다."""
    values, i = [], 0
    while i < len(args):
        t = args[i]
        if t == "--":
            break
        if t.startswith("--"):
            name = t.split("=", 1)[0]
            if name == long:
                if "=" in t:
                    values.append(t.split("=", 1)[1])
                else:
                    values.append(args[i + 1] if i + 1 < len(args) else "")
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
                    if ch == short:
                        values.append(val)
                    break
        i += 1
    return values


SINKS = {"tail", "head", "cat", "tee"}  # PR 생성 뒤 파이프로 출력만 받는 것 — 어느 커밋이 PR이 될지 바꾸지 못한다
SAFE_ENV = {"GH_PROMPT_DISABLED", "NO_COLOR", "GH_NO_UPDATE_NOTIFIER", "GH_PAGER", "PAGER", "CLICOLOR",
            "CLICOLOR_FORCE", "GH_SPINNER_DISABLED", "TERM"}


def shape(lx, cwd):
    """허용하는 모양이면 (디렉터리, {"head": --head 값, "repo": --repo 값}(없으면 None), None),
    아니면 (None, None, 이유)."""
    segs, seps = split_top(lx)
    bad = [s for s in seps if s not in ("&&", "\n", "||", ";", "|")]
    if bad:
        return None, None, "`%s`가 있다(파이프·백그라운드·서브셸·명령 치환)" % bad[0].strip()
    body = [(i, s) for i, (s, _a, _b) in enumerate(segs) if s.strip()]
    if not body:
        return None, None, "PR 생성 명령을 찾지 못했다"
    if any(not quoted for _p, quoted, _b in lx.docs):
        return None, None, "따옴표 없는 heredoc 태그가 있다 — 본문의 `$( … )`가 PR 생성 전에 돈다(`<<'EOF'`로 쓴다)"
    words = []
    for _i, s in body:
        w = words_of(s)
        if w is None:
            return None, None, "명령을 셸 낱말로 나누지 못했다: %r" % s.strip()[:60]
        words.append(w)
    d, k = cwd, 0
    if len(body) >= 2 and words[0] and words[0][0] == "cd":
        args = words[0][1:]
        physical = False
        while args and args[0] in ("-P", "-L", "-e", "-@", "--"):
            physical = physical or args[0] == "-P"
            args = args[1:]
        if len(args) != 1:
            return None, None, "맨 앞 `cd`의 대상이 하나가 아니다"
        arg = args[0]
        if arg == "-" or "$" in arg or "`" in arg:
            return None, None, "`cd %s`의 대상은 셸이 돌아야 안다" % arg
        # `cd X &&` 뒤의 줄바꿈은 셸이 다음 줄로 잇는다 — 연산자가 먼저 오면 줄바꿈은 무시한다
        mid = seps[body[0][0]:body[1][0]]
        op = mid[:1] + [s for s in mid[1:] if s != "\n"]
        if op == ["&&"]:
            k = 1
        elif (op == ["||"] and len(body) == 3 and re.fullmatch(r"exit(\s+\d+)?", " ".join(words[1]))
              and seps[body[1][0]:body[2][0]] and all(s in (";", "\n", "&&") for s in seps[body[1][0]:body[2][0]])):
            k = 2
        else:
            return None, None, ("맨 앞 `cd` 뒤는 `&&`나 `|| exit`여야 한다 — `;`·줄바꿈이면 `cd`가 실패해도 "
                                "PR 생성이 원래 디렉터리에서 돈다")
        d = os.path.join(cwd, os.path.expanduser(arg))
        d = os.path.realpath(d) if physical else os.path.normpath(d)
        if not os.path.isdir(d):
            return None, None, "`cd` 대상 디렉터리가 없다: %s" % d
    if "|" in seps[:body[k][0]]:
        return None, None, "PR 생성 앞에 파이프가 있다"
    # PR 생성 뒤에는 `| tail -3` 같은 출력 받기만 — 그 밖의 명령은 같은 호출에 두지 않는다
    for m in range(k + 1, len(body)):
        if [s for s in seps[body[m - 1][0]:body[m][0]]] != ["|"] or not words[m] or words[m][0] not in SINKS:
            return None, None, "PR 생성 말고 다른 명령이 같은 호출에 있다(뒤에는 `| tail`·`head`·`cat`·`tee`만)"
    if any(s in ("||", "&&") for s in seps[body[k][0]:]):
        return None, None, "PR 생성 뒤에 `&&`·`||`가 있다"
    w = words[k]
    while w and re.match(r"^\w+=", w[0]) and w[0].split("=", 1)[0] in SAFE_ENV:
        w = w[1:]  # GH_PROMPT_DISABLED=1 같은 무해한 접두. GIT_DIR=·GH_REPO=는 남아서 아래에서 막힌다
    if len(w) < 3 or w[0] != "gh" or w[1] != "pr" or w[2] not in VERBS:
        return None, None, "PR 생성은 `gh pr create …` 그대로 써야 한다(환경변수·래퍼·경로·변수·스크립트 파일·`gh api` 없이)"
    for inner in lx.subs:
        if not CAT_ONLY.fullmatch(Lexed(inner).clean):
            return None, None, "인자 속 명령 치환은 `cat`만 허용한다: %r" % inner.strip()[:40]
    heads = flag_values(w[3:], "--head", "H")
    repos = flag_values(w[3:], "--repo", "R")
    if len(repos) > 1:
        return None, None, "`--repo`가 둘 이상이다 — gh는 마지막 것을 쓴다"
    if repos and (not repos[0] or "$" in repos[0] or "`" in repos[0]):
        return None, None, "`--repo` 값이 리터럴이 아니다"
    if len(heads) > 1:
        return None, None, "`--head`가 둘 이상이다 — gh는 마지막 것을 쓴다"
    if heads and (not heads[0] or "$" in heads[0] or "`" in heads[0]):
        return None, None, "`--head` 값이 리터럴이 아니다"
    if heads and ":" in heads[0]:
        return None, None, "`--head 소유자:브랜치` — 포크의 브랜치는 이 저장소에서 대조할 수 없다"
    return d, {"head": heads[0] if heads else None, "repo": repos[0] if repos else None}, None


def remote_branch(top, branch):
    """PR이 만들어질 원격 브랜치 — (원격 이름, 브랜치 이름).

    추적 설정(`branch.<b>.remote`·`.merge`)이 있고 그 이름이 기본 브랜치가 아니면 그것(`push -u origin wt:feature`
    → origin feature). 기본 브랜치를 추적하는 것은 「거기서 땄다」는 뜻이지 푸시했다는 뜻이 아니라
    (`switch -c x origin/main`, 워크트리 생성) `origin <브랜치>`로 넘어간다. 원격이 `.`(로컬 브랜치 추적)이어도 같다.
    """
    remote = git("-C", top, "config", "branch.%s.remote" % branch)
    merge = git("-C", top, "config", "branch.%s.merge" % branch)
    name = merge[len("refs/heads/"):] if merge.startswith("refs/heads/") else ""
    if remote and remote != "." and name and (name not in ("main", "master") or branch in ("main", "master")):
        return remote, name
    return "origin", branch


def remote_tip(top, remote, name):
    """원격 브랜치의 **지금** 끝 — (읽었나, SHA 또는 ""). 추적 ref(`origin/x`)가 아니라 원격에 직접 묻는다.

    추적 ref는 마지막 fetch·push 때의 값이다 — 그 뒤 남이 원격 브랜치를 밀면 낡은 값으로 통과했고, 다른 곳에서
    푸시해 추적 ref가 없으면 푸시했는데도 막았다(이슈 #114). 원격을 못 읽으면 PR 생성도 못 하므로 막는다.

    ⚠ 제한 시간은 `.claude/settings.json`의 훅 timeout(15초)보다 **짧아야** 한다. 훅이 먼저 죽으면 종료 코드 2로
    끝나지 않으니 차단이 아니다(실측은 안 했다) — 느린 네트워크가 곧 게이트 우회가 된다. 여기서 끊고 막는다.
    """
    ok, out = git_ok("-C", top, "ls-remote", remote, "refs/heads/" + name, timeout=8)
    sha = next((ln.split("\t", 1)[0] for ln in out.splitlines() if ln.endswith("\trefs/heads/" + name)), "")
    return ok, sha


def slug(s):
    """`소유자/저장소`(소문자) — `o/r`·`HOST/o/r`·URL·`git@host:o/r.git`·로컬 경로 모두 끝 두 마디로. 못 읽으면 ""."""
    parts = re.split(r"[/:]", re.sub(r"(?:\.git)?/*$", "", (s or "").strip()))
    return "/".join(parts[-2:]).lower() if len(parts) >= 2 and all(parts[-2:]) else ""


def cd_targets(lx, cwd):
    """맨 위 `cd <리터럴>`들의 대상 — 상대 경로 스크립트를 찾을 곳. 탐지만 쓴다(판정은 `shape`가 한다)."""
    out = []
    for seg, _a, _b in split_top(lx)[0]:
        w = words_of(seg)
        if w and w[0] == "cd" and len(w) >= 2 and "$" not in w[-1] and w[-1] != "-":
            out.append(os.path.normpath(os.path.join(cwd, os.path.expanduser(w[-1]))))
    return out


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
    lx = Lexed(command)  # 한 번만 렉싱한다 — 탐지와 모양 판정이 같은 낱말을 본다
    cwd = os.path.normpath(payload.get("cwd") or os.getcwd())
    if not has_pr(command, 0, lx, bases=[cwd] + cd_targets(lx, cwd)):
        return 0

    d, opts, why = shape(lx, cwd)
    if d is None:
        return block("PR 생성 명령이 허용하는 모양이 아니다 — %s. %s" % (why, SIMPLE))
    top = git("-C", d, "rev-parse", "--show-toplevel")
    if not top:
        if d == cwd and not opts["head"]:
            return 0  # 저장소 밖 — 첫 판부터의 동작
        return block("PR 생성 위치가 git 저장소가 아니라(%s) `--head`·`cd`가 가리키는 것을 확인할 수 없다." % d)

    if opts["head"]:
        branch = opts["head"]
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

    remote, name = remote_branch(top, branch)
    # PR이 열릴 저장소 — `--repo`, 없으면 훅 프로세스 환경의 GH_REPO. 판정한 원격과 같아야 한다(이슈 #114)
    target = opts["repo"] or os.environ.get("GH_REPO", "")
    if target:
        # `push -u <URL> wt`이면 branch.wt.remote가 이름이 아니라 URL이다
        mine = slug(git("-C", top, "config", "remote.%s.url" % remote)) or slug(remote)
        if not mine or slug(target) != mine:
            return block("PR을 `%s`에 연다 — 판정한 원격 `%s`(%s)와 다른 저장소다. 그 저장소의 브랜치는 여기서 "
                         "대조할 수 없다." % (target, remote, mine or "주소를 못 읽음"), branch, sha)
    ok, up = remote_tip(top, remote, name)
    if not ok:
        return block("원격 `%s`를 읽지 못했다(ls-remote 실패) — 리뷰한 커밋이 원격에 있는지 확인할 수 없다." % remote,
                     branch, sha)
    if not up:
        return block("`%s/%s`가 원격에 없다 — 리뷰한 커밋을 먼저 푸시한다(따로 호출)." % (remote, name), branch, sha)
    if up != sha:
        return block("원격 `%s/%s`(%s)가 리뷰한 커밋(%s)과 다르다 — PR은 원격 브랜치로 만들어진다. 리뷰한 커밋을 "
                     "푸시했는가, 원격에 다른 커밋이 올라가 있지 않은가." % (remote, name, up[:8], sha[:8]), branch, sha)
    return 0


if __name__ == "__main__":
    sys.exit(main())
