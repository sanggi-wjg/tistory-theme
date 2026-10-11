#!/usr/bin/env python3
"""티스토리 스킨 정적 린트.

이 도메인은 조용히 실패한다 — 치환자 오타는 무시되고, CSS 선택자는 매칭이 안 돼도
에러를 내지 않으며, JS 셀렉터는 null을 반환하고 끝난다. 이 스크립트는 그 침묵을 깬다.

사용:
  python3 .claude/skills/skin-qa-check/scripts/lint.py
  python3 .claude/skills/skin-qa-check/scripts/lint.py --json
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = os.getcwd()
SRC = os.path.join(ROOT, "src")

ERRORS, WARNINGS, INFO = [], [], []


def err(code, msg, where=""):
    ERRORS.append({"level": "error", "code": code, "message": msg, "where": where})


def warn(code, msg, where=""):
    WARNINGS.append({"level": "warning", "code": code, "message": msg, "where": where})


def info(msg):
    INFO.append(msg)


def read(p):
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def lines_of(text, needle):
    return [i + 1 for i, l in enumerate(text.split("\n")) if needle in l]


# ─────────────────────────── 0. 태그 균형 (SYN002) ───────────────────────────

# 자식을 가질 수 없는 요소. 닫는 태그가 없는 것이 정상이다.
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
             "param", "source", "track", "wbr"}


class _TagBalance(HTMLParser):
    """여는 태그와 닫는 태그가 짝을 이루는가. <s_*> 그룹 치환자도 요소로 센다 —
    티스토리 치환 엔진이 그 쌍을 찾기 때문이다(SUB005가 짝 수를, 여기서는 위치를 본다)."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack, self.problems = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        # `<br/>`는 무해하지만 `<div/>`·`<s_x/>`는 브라우저가 **여는 태그**로 읽는다 —
        # 자기 닫힘 표기가 있어도 그 뒤 형제를 삼키는 정확히 그 침묵이다.
        if tag not in VOID_TAGS:
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        line = self.getpos()[0]
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        names = [t for t, _ in self.stack]
        if tag in names:
            i = len(names) - 1 - names[::-1].index(tag)
            for t, l in self.stack[i + 1:]:
                self.problems.append("%d행의 <%s>가 닫히지 않은 채 %d행에서 </%s>를 만났다" % (l, t, line, tag))
            del self.stack[i:]
        else:
            self.problems.append("%d행: 여는 태그 없는 </%s>" % (line, tag))


def lint_html_balance(skin):
    """skin.html의 태그 균형 — SYN002.

    2026-08-27 하네스 리뷰: `</section>` 하나를 지우거나 닫지 않는 `<div>`를 끼워도
    린트 45종이 **오류 0**이었다. 브라우저는 알아서 복구해 그리므로 에러가 없고,
    복구된 트리는 CSS 선택자·레이아웃이 조용히 어긋난다. 마크업이 이 저장소의 가장 큰
    표면인데 문법 자체를 보는 검사가 없었다 — 규칙 하나가 아니라 파서가 그 부류를 덮는다.
    """
    p = _TagBalance()
    try:
        p.feed(skin)
        p.close()
    except Exception as e:  # pragma: no cover — 파서 자체가 죽으면 그것도 오류다
        err("SYN002", "skin.html을 파싱하지 못했다: %s" % e, "src/skin.html")
        return
    for tag, line in p.stack:
        p.problems.append("%d행의 <%s>가 파일 끝까지 닫히지 않았다" % (line, tag))
    for m in p.problems:
        err("SYN002", m + ". 브라우저는 복구해 그리지만 복구된 트리는 CSS·레이아웃이 조용히 어긋난다.",
            "src/skin.html")


# ─────────────────────────── 0b. index.xml 문서 형식 (SYN003) ───────────────────────────

def lint_index_xml(xml):
    """src/index.xml이 올바른 XML이고 루트가 <skin>인가 — SYN003.

    이슈 #147: 빌드는 이 파일을 파싱하지 않고 바이트 그대로 dist/로 옮기고, 린트·프리뷰는
    <variable>을 정규식으로만 읽는다. `</information>`을 지워도 `npm run check`가 초록불이었다.
    깨진 것은 스킨 편집기에 올릴 때에야 드러나는데, 이 파일은 올릴 때마다 스킨 설정이
    초기화되므로(결정 1) 라이브에서 시험해 볼 수 있는 파일이 아니다.

    dist가 아니라 src를 본다 — dist는 그 사본이라, src를 망가뜨려도 낡은 dist가 남아 있으면
    통과해 버린다(티스토리 시트 검사들이 src만 보는 것과 같은 이유).
    """
    if xml is None:
        return
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError as e:
        line, col = e.position
        err("SYN003", "index.xml이 올바른 XML이 아니다 — %d행 %d열: %s. "
            "CDATA 안의 `]]>`, CDATA 밖의 맨 `<`·`&`, 빠진 닫는 태그를 본다." % (line, col + 1, e),
            "src/index.xml")
        return
    if root.tag != "skin":
        err("SYN003", "index.xml의 루트가 <%s>다. 티스토리 스킨 정보는 <skin>으로 감싼다." % root.tag,
            "src/index.xml")


# ─────────────────────────── 1. 치환자 유효성 ───────────────────────────

def lint_substitutions(skin, xml, wl):
    groups = set(wl["groups"])
    values = set(v[4:-4] for v in wl["values"])   # [##_x_##] → x

    # 주석 안에 그룹 태그를 쓰면 치환 엔진이 그것을 여는 태그로 집는다.
    # 로컬 렌더러에서 실제로 재현했다 — 바깥 <article> 껍데기가 반복에서 빠지고
    # <s_...> 태그가 출력에 그대로 남았다. 티스토리도 같은 방식으로 텍스트를 찾을
    # 가능성이 높고, 그러면 그 영역이 통째로 망가진다. 아예 금지한다.
    for c in re.finditer(r"<!--.*?-->", skin, re.S):
        for t in sorted(set(re.findall(r"</?s_[a-zA-Z0-9_]+>", c.group(0)))):
            err("SUB007", "주석 안에 그룹 치환자 태그 %s가 그대로 쓰였다. 치환 엔진은 "
                "주석을 가리지 않는다 — 꺾쇠 없이 이름만 적어라." % t, "src/skin.html")

    # HTML 주석 안의 치환자는 티스토리에도 무의미하다. 세면 오탐이 난다 —
    # 왜 이 태그를 쓰지 않았는지 주석으로 설명하는 순간 SUB005 짝이 어긋난다.
    # (주석 안에서만 여는 태그를 지우고 닫는 태그를 남기는 실수는 주석을 지운
    #  이 본문 기준으로 여전히 잡힌다.)
    skin = re.sub(r"<!--.*?-->", "", skin, flags=re.S)

    # 여는 태그만 모으면 **여는 태그를 지웠을 때 고아가 된 닫는 태그를 못 잡는다** —
    # 그 그룹이 목록에 없어서 아래 짝 검사가 아예 돌지 않기 때문이다.
    # 닫는 태그 이름도 함께 모아야 양쪽 방향이 다 걸린다.
    used_g = set(m.group(1).lower() for m in re.finditer(r"<(s_[a-zA-Z0-9_]+)(?:\s[^>]*)?>", skin))
    used_g |= set(m.group(1).lower() for m in re.finditer(r"</(s_[a-zA-Z0-9_]+)>", skin))
    used_v = set(re.findall(r"\[##_([a-zA-Z0-9_]+)_##\]", skin))

    # 동적 치환자는 index.xml과 대조한다
    declared = set()
    if xml:
        for m in re.finditer(r"<variable>(.*?)</variable>", xml, re.S):
            n = re.search(r"<name>(.*?)</name>", m.group(1), re.S)
            if n:
                declared.add(n.group(1).strip())

    for g in sorted(used_g):
        if g.startswith(("s_if_var_", "s_not_var_")):
            name = g[9:] if g.startswith("s_if_var_") else g[10:]
            if name not in declared:
                err("SUB001", "<%s>가 쓰였지만 index.xml에 <name>%s</name> 변수가 없다. "
                    "빈 값으로 처리되어 블록이 통째로 사라진다." % (g, name),
                    "src/skin.html:%s" % lines_of(skin, "<" + g)[:1])
        elif g not in groups:
            err("SUB002", "존재하지 않는 그룹 치환자 <%s>. 티스토리가 조용히 무시한다. "
                "data/substitutions.json 확인." % g,
                "src/skin.html:%s" % lines_of(skin, "<" + g)[:1])

    for v in sorted(used_v):
        if v.startswith("var_"):
            if v[4:] not in declared:
                err("SUB003", "[##_%s_##]가 쓰였지만 index.xml에 <name>%s</name> 변수가 없다. "
                    "빈 문자열이 출력된다." % (v, v[4:]), "src/skin.html")
        elif v not in values:
            err("SUB004", "존재하지 않는 값 치환자 [##_%s_##]. 문자 그대로 출력되거나 사라진다." % v,
                "src/skin.html")

    # 여닫이 짝
    for g in sorted(used_g):
        if g.startswith(("s_if_var_", "s_not_var_")):
            continue
        o = len(re.findall(r"<%s(?:\s[^>]*)?>" % re.escape(g), skin, re.I))
        c = len(re.findall(r"</%s>" % re.escape(g), skin, re.I))
        if o != c:
            err("SUB005", "<%s> 여는 태그 %d개 / 닫는 태그 %d개 — 짝이 맞지 않는다." % (g, o, c),
                "src/skin.html")

    if "s_t3" not in used_g:
        err("SUB006", "<s_t3>가 없다. 티스토리 공통 JS가 삽입되지 않아 댓글·공유가 전부 죽는다.",
            "src/skin.html")

    # SUB008 — s_article_rep의 하위 영역은 반드시 그 안에 있어야 한다.
    #
    # 2026-08-25 배포에서 실제로 당했다. <s_permalink_article_rep>를 최상위에 두었더니
    # 티스토리가 그 영역을 **통째로 버렸다** — 글 페이지에 본문·제목·목차·관련글이
    # 하나도 없었고, 에러도 빈 껍데기도 없었다. 홈은 s_list가 대신 그려 줘서
    # 멀쩡해 보였기 때문에 발견이 더 늦었다.
    #
    # 짝 검사(SUB005)로는 절대 못 잡는다 — 짝은 맞고 위치만 틀리기 때문이다.
    for child in ("s_permalink_article_rep", "s_index_article_rep"):
        if child not in used_g:
            continue
        for m in re.finditer(r"<%s(?:\s[^>]*)?>" % child, skin, re.I):
            before = skin[:m.start()]
            opened = len(re.findall(r"<s_article_rep(?:\s[^>]*)?>", before, re.I))
            closed = len(re.findall(r"</s_article_rep>", before, re.I))
            if opened <= closed:
                err("SUB008", "<%s>가 <s_article_rep> 바깥에 있다. 이건 독립 영역이 아니라 "
                    "s_article_rep의 하위 영역이라, 바깥에 두면 티스토리가 통째로 버린다 — "
                    "에러도 빈 껍데기도 없이 글 본문이 사라진다 (DECISIONS.md 결정 29)." % child,
                    "src/skin.html")
                break

    # SUB009 — *_group 치환자는 자기 그룹 래퍼 안에 있어야 한다.
    #
    # 2026-08-26 본 블로그 배포에서 당했다. [##_comment_group_##]을 <s_rp> 없이
    # 두었더니 티스토리가 **빈 문자열로 치환했다** — 잔존 치환자도, 빈 껍데기도,
    # 에러도 없었다. .comments 안이 그냥 비어 있었고 <s_rp_count>는 "댓글 2"를
    # 정상 출력하고 있어서 더 헷갈렸다.
    #
    # 같은 페이지의 방명록이 원인을 짚어 줬다 — [##_guestbook_group_##]은
    # <s_guest> 안에 있었고 정상 렌더됐다. 둘은 공식 문서에서 완전히 대칭인데
    # 우리 쪽만 한쪽 래퍼가 빠져 있었다.
    #
    # SUB005(짝 검사)도 SUB008(s_article_rep 중첩)도 이걸 못 잡는다 — 짝은 맞고,
    # s_article_rep 안에 있는 것도 맞다. 빠진 것은 **자기 그룹 래퍼**다.
    for val, wrap, what in (("comment_group", "s_rp", "댓글"),
                            ("guestbook_group", "s_guest", "방명록")):
        for m in re.finditer(r"\[##_%s_##\]" % val, skin, re.I):
            before = skin[:m.start()]
            opened = len(re.findall(r"<%s(?:\s[^>]*)?>" % wrap, before, re.I))
            closed = len(re.findall(r"</%s>" % wrap, before, re.I))
            if opened <= closed:
                err("SUB009", "[##_%s_##]이 <%s> 바깥에 있다. 티스토리는 이걸 "
                    "**빈 문자열로 치환한다** — 에러도 잔존 치환자도 없이 %s이 통째로 "
                    "사라진다 (DECISIONS.md 결정 34)." % (val, wrap, what),
                    "src/skin.html")
                break

    # CAT001 — 카테고리는 리스트형이어야 한다.
    #
    # [##_category_##](폴더형)과 [##_category_list_##](리스트형)은 이름만 비슷하고
    # 완전히 다른 것을 출력한다. 2026-08-25 양쪽 실측:
    #
    #   폴더형   중첩 table 19 + 트리선 GIF 17장, 링크는 onclick(a href 0개),
    #            div마다 인라인 style="color:#4d4d4d" · background-color:#ffffff 18개
    #   리스트형 ul.tt_category/li + a href 36개, 인라인 style 0개, 이미지 0장
    #
    # 폴더형이 나가면 조용히 실패하는 게 아니라 **다른 UI가 나온다**. tistory.css의
    # .tt_category 규칙이 하나도 매칭되지 않아 티스토리 기본 트리가 그대로 노출되고,
    # category.js는 ul을 못 찾아 물러나고, 인라인 색이 다크모드를 이긴다.
    # 2026-08-25 첫 배포에서 실제로 폴더형이 나갔다 (DECISIONS.md 결정 31).
    if "category" in used_v:
        err("CAT001", "[##_category_##](폴더형)이 쓰였다. 이 스킨은 리스트형 마크업"
            "(ul.tt_category)에 CSS와 JS를 걸어 두었으므로 [##_category_list_##]를 써야 한다. "
            "폴더형은 중첩 table과 트리선 GIF를 내보내고 링크가 onclick이라 "
            "내부링크가 0개가 되며, 인라인 색이 다크모드를 이긴다 (DECISIONS.md 결정 31).",
            "src/skin.html")

    info("치환자: 그룹 %d종 / 값 %d종 사용" % (len(used_g), len(used_v)))


# ─────────────────────── 2. 영역 치환자 페이지 정합성 ───────────────────────

def lint_area_scope(skin):
    """홈 목록과 일반 목록의 접두사가 섞이면 조용히 빈 화면이 된다.

    ⚠ **주석을 먼저 벗긴다.** 여기 검사들은 전부 "이 이름이 skin.html에 있는가"로
      묻는데, 주석 안의 글자도 그냥 걸린다. 2026-08-27에 실제로 당했다 —
      `AREA003`(아래에서 폐기)이 뜨지 않고 있던 유일한 이유가 `skin.html`의
      **주석 문장 한 줄**에 그 이름이 적혀 있어서였다. 그 문장을 고치는 순간
      경고가 살아난다. 검사가 무엇을 근거로 조용한지가 우연이면 그건 통과가
      아니라 침묵이다.
      (`lint_substitutions`는 자기 지역 변수에서만 벗겨서 여기까지 오지 않았다.)
    """
    skin = re.sub(r"<!--.*?-->", "", skin, flags=re.S)

    def inner_of(tag):
        m = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (tag, tag), skin, re.S | re.I)
        return m.group(1) if m else ""

    idx = inner_of("s_index_article_rep")
    if idx and re.search(r"\[##_list_rep_", idx):
        err("AREA001", "<s_index_article_rep> 안에서 [##_list_rep_*_##]를 쓰고 있다. "
            "홈에서는 [##_article_rep_*_##]를 써야 한다. 지금은 값이 비어 나온다.", "src/skin.html")

    lst = inner_of("s_list_rep")
    if lst and re.search(r"\[##_article_rep_", lst):
        err("AREA002", "<s_list_rep> 안에서 [##_article_rep_*_##]를 쓰고 있다. "
            "목록에서는 [##_list_rep_*_##]를 써야 한다.", "src/skin.html")

    # AREA003은 폐기했다 (2026-08-27). 「<s_list_rep>는 있는데 <s_index_article_rep>가
    # 없다」를 경고했는데, **결정 29가 그 전제를 뒤집었다** — <s_list>는 홈에서도
    # 렌더되고(2026-08-25 실측) 그래서 홈 목록을 s_index_article_rep로 따로 그릴
    # 이유가 없어졌다. 즉 이 경고는 지금 규범과 정반대를 요구한다.
    # 번호는 재사용하지 않는다. SKILL.md에 폐기 사실을 적어 둔다.

    if "[##_body_id_##]" not in skin:
        warn("AREA004", "[##_body_id_##]가 없다. body_id로 페이지별 CSS 분기를 할 수 없다.",
             "src/skin.html")

    # AREA005 — AREA003이 지키려던 것(«목록이 통째로 빈다»)은 여전히 실재하는
    # 위험이다. 다만 지금 그 위험을 만드는 것은 s_index_article_rep의 부재가 아니라
    # **<s_list> 자체의 부재**다. 결정 29 이후 홈·카테고리·검색·태그·보관함
    # 다섯 페이지가 전부 이 한 영역에 걸려 있다 — 빠지면 다섯 장이 같이 빈다.
    # 짝 검사(SUB005)는 «있는 것»의 짝만 보므로 통째로 없는 것은 못 잡는다.
    if not re.search(r"<s_list(?:\s[^>]*)?>", skin, re.I):
        err("AREA005", "<s_list> 영역이 없다. 결정 29 이후 홈·카테고리·검색·태그·보관함이 "
            "전부 이 한 영역으로 그려지므로, 빠지면 다섯 페이지가 동시에 빈다 — "
            "에러도 미치환 치환자도 없이 목록만 사라진다.", "src/skin.html")


# ────────────────── 3. 경계면: 마크업 ↔ CSS ↔ JS ──────────────────

def lint_boundaries(skin, css, js):
    """훅이 한쪽에만 있으면 조용히 아무 일도 일어나지 않는다."""
    # data-cat: 마크업이 내보내는가 ↔ CSS가 기대하는가
    css_cats = set(re.findall(r'\[data-cat[\^~|]?="([^"]+)"\]', css or ""))
    if css_cats and "data-cat=" not in skin:
        err("BND001", "CSS가 [data-cat]을 %d개 규칙에서 기대하는데 skin.html이 data-cat을 출력하지 않는다. "
            "카테고리별 기본이미지가 전부 무너진다." % len(css_cats), "src/styles/")
    if "data-cat=" in skin and not css_cats:
        warn("BND002", "skin.html이 data-cat을 출력하지만 CSS에 [data-cat] 규칙이 없다.", "src/skin.html")

    # 카테고리 커버리지: 실제 데이터 ↔ CSS 규칙
    cat_path = os.path.join(ROOT, "data", "categories.json")
    if css_cats and os.path.exists(cat_path):
        cats = json.load(open(cat_path, encoding="utf-8"))["categories"]
        tops = set(c.replace("  (상위)", "") for c in cats if c.endswith("  (상위)"))
        covered = set()
        for c in css_cats:
            covered.add(c.rstrip("/"))
        missing = sorted(t for t in tops if t not in covered)
        if missing:
            warn("BND003", "CSS 기본이미지 규칙이 없는 상위 카테고리: %s. 기본값으로 떨어진다."
                 % ", ".join(missing), "src/styles/")

    # 클래스 훅: JS가 찾는데 마크업에 없는 것
    if js:
        sels = set()
        for m in re.finditer(r"""querySelector(?:All)?\(\s*['"]([^'"]+)['"]""", js):
            sels.add(m.group(1))
        # 마크업이 내보내는 클래스를 **토큰으로** 모은다. 2026-08-27까지는
        # `'class="%s' % cls in skin`(접두 일치)와 `' %s' % cls in skin`(주석·산문의 아무
        # 단어)로 봐서, `entry-body`를 `entry-body-v2`로 개명해도 통과했다.
        markup_classes = set()
        for m in re.finditer(r"""class=["']([^"']+)["']""", re.sub(r"<!--.*?-->", "", skin, flags=re.S)):
            markup_classes.update(m.group(1).split())
        # JS가 만드는 DOM(§5.6·§8 등재)은 마크업에 없는 것이 정상이다 — BND006·007이 본다.
        # 등재 표를 못 읽으면(구조 오류) BND006이 오류로 내므로 여기서는 제외 목록만 비운다 —
        # 그러면 등재 클래스마다 BND004가 뜨는데, 그 원인은 BND006 한 줄이 말한다.
        registry, _, structural = parse_js_dom_registry()
        js_made = set() if structural else set(c[1:] for c in registry if not c.endswith("*"))
        for s in sorted(sels):
            for cls in re.findall(r"\.([a-zA-Z][\w-]*)", s):
                # 티스토리가 렌더링하는 것. selected는 카테고리 트리에서 현재 가지의
                # li에 붙는다 (2026-08-25 실측 /category/Python).
                if cls in ("contents_style", "tt_category", "category_list",
                           "sub_category_list", "link_tit", "link_item",
                           "link_sub_item", "c_cnt", "selected") or cls.startswith("tt-"):
                    continue
                if cls in js_made or cls in markup_classes:
                    continue
                warn("BND004", "JS가 '%s'를 찾지만 skin.html의 class 속성에 '%s'가 없다(정확 일치). "
                     "JS가 만드는 DOM이면 hooks.md §5.6·§8에 등재하라." % (s, cls), "src/js/")

    # 본문 래퍼 정확일치 — 오래된 글이 누락되는 고전적 실수
    for label, body, path in (("CSS", css, "src/styles/"), ("JS", js, "src/js/")):
        if body and re.search(r"""\[class=["']contents_style["']\]""", body):
            err("BND005", "%s가 [class=\"contents_style\"] 정확일치 선택자를 쓴다. "
                "실제 래퍼는 'tt_article_useless_p_margin contents_style'이라 매칭되지 않는다." % label, path)


# ────────── 3a-2. 치환자만 담은 요소의 장식 (BND008) ──────────

# `<span class="x">[##_sub_##]</span>` — 치환자 하나가 알맹이의 전부인 요소.
# 여는 태그와 닫는 태그가 같아야 하고, 치환자 앞뒤에 글자가 없어야 한다.
ONLY_SUB_RE = re.compile(
    r"<(?P<tag>[a-zA-Z][\w-]*)(?P<attrs>[^>]*)>(?P<inner>\s*\[##_[a-zA-Z0-9_]+_##\]\s*)</(?P=tag)>")


def lint_empty_substitution_decor(skin, css):
    """치환자 하나만 담은 요소에 ::before/::after 장식을 달았다면 :empty 가드가 있는가.

    **이 저장소가 같은 실패를 두 번 했다.** 티스토리 치환자는 값이 없으면
    에러가 아니라 **빈 문자열**을 낸다. 그런데 라벨·구분자를 CSS가 그리고 있으면
    값만 사라지고 장식은 남는다 — 화면에는 `댓글`이나 `·`만 떠 있다.

        결정 35  글 하단 태그에 `,`만 남았다
        결정 42  홈 카드 13/13 · 사이드바 5/5에 `댓글`·`·`만 남았다

    ⚠ 이 검사는 치환자가 실제로 값을 내는지 **모른다.** 알 방법도 없다 —
      화이트리스트는 이름의 유효성만 보증하고, 어느 영역에서 무엇이 채워지는지는
      티스토리만 안다. 그래서 "가드가 있는가"만 묻는다. 값이 항상 있는 자리라면
      가드는 죽은 규칙이지 해롭지 않다.

    ⚠ 라벨이 **마크업 안에** 있는 자리는 잡지 않는다 — `<a>댓글 [##_..._##]</a>`처럼
      글자가 섞이면 애초에 이 검사의 대상이 아니다. 그런 자리는 티스토리의 조건
      블록(`<s_rp_count>` 등)이 통째로 지운다.
    """
    if not skin or not css:
        return
    body = strip_comments(css)

    # 장식이 **그 요소 자신**에 붙은 클래스만 모은다.
    # `.entry-tags a::before`는 자손을 꾸미는 것이라 대상이 아니다 — 치환자가
    # 비면 자손 <a>가 아예 생기지 않아 ::before도 같이 사라진다.
    decor_classes = set()
    for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
        if not re.search(r"content\s*:\s*[\"']", rule.group(2)):
            continue
        for sel in rule.group(1).split(","):
            compound = re.search(r"([^\s>+~]+)::(?:before|after)\s*$", sel.strip())
            if compound:
                decor_classes.update(re.findall(r"\.([a-zA-Z][\w-]*)", compound.group(1)))

    missing, dead = [], []
    for m in ONLY_SUB_RE.finditer(skin):
        cls_m = re.search(r"""class=["']([^"']+)["']""", m.group("attrs"))
        if not cls_m:
            continue
        # 치환자 앞뒤에 공백이 있으면 값이 사라져도 공백 텍스트 노드가 남아
        # :empty가 **절대 참이 되지 않는다** (layout.css:9에 적힌 함정).
        padded = m.group("inner") != m.group("inner").strip()
        for cls in cls_m.group(1).split():
            if cls.startswith("[##_"):  # 클래스 자체가 치환자인 자리 (tagcloud-link 등)
                continue
            if cls not in decor_classes:
                continue
            if not re.search(r"\.%s(?::empty|:has\()" % re.escape(cls), body):
                missing.append(cls)
            elif padded and not re.search(r"\.%s:has\(" % re.escape(cls), body):
                dead.append(cls)
    if missing:
        err("BND008", "치환자 하나만 담은 요소 %d종에 ::before/::after 장식이 있는데 "
            ":empty 가드가 없다: %s. 치환자가 빈 문자열을 내면 값은 사라지고 "
            "라벨·구분자만 화면에 남는다 — 결정 35·42가 같은 실패였다."
            % (len(missing), ", ".join(sorted(set(missing)))), "src/styles/")
    if dead:
        err("BND008", "%d종은 :empty 가드가 있지만 skin.html에서 치환자 앞뒤에 공백이 있다: %s. "
            "값이 사라져도 공백 텍스트 노드가 남아 :empty가 **절대 참이 되지 않는다** — "
            "가드가 죽은 채로 초록불이 된다. 치환자를 여는 태그에 붙여 쓰거나 "
            ":has() 가드를 쓴다 (layout.css:9의 함정)."
            % (len(dead), ", ".join(sorted(set(dead)))), "src/skin.html")
    if not missing and not dead:
        info("치환자만 담은 요소의 ::before/::after 장식: 가드 전부 있고 살아 있음")


# ────────── 3b. JS가 만드는 클래스 ↔ 문서 ↔ CSS (docs/hooks.md §5.6) ──────────

HOOKS_MD = os.path.join(ROOT, "docs", "hooks.md")

# 예외 목록의 제목. 이 문자열이 hooks.md에서 사라지면 예외가 통째로 풀려
# BND006이 시끄럽게 실패한다 — 검사가 조용히 꺼지는 것보다 그쪽이 낫다.
NO_CSS_HEADING = "**CSS 규칙이 없는 것이 정상인 클래스**"


# JS가 만드는 이름이 등재되는 절. **§5.6 하나가 아니다.**
#
# 결정 40은 "§5.6이 정본"이라고 못 박고 린트가 그 표만 읽게 했는데, 실제 등재는
# 흩어져 있었다 — 상태 클래스(`.is-ready` `.no-toc` `.is-current` …)는 §8에 있고
# 목차 항목(`.toc-item` `.toc-link`)은 §5.1에 있었다. 그래서 `toc.js`에서
# `.toc-link`를 개명하고 CSS를 안 고쳐도 **아무 검사도 안 켜졌다** —
# 결정 40이 닫으려던 구멍이 절 하나 옆에 그대로 있었던 셈이다 (2026-08-27).
#
# §5.1은 표가 아니라 산문이라 파싱 대상이 아니다. 그쪽 이름은 §5.6 표로 옮겼다.
REGISTRY_SECTIONS = [
    (r"^### 5\.6 [^\n]*\n(.*?)^### ", "§5.6 (JS가 새로 만드는 DOM)"),
    (r"^## 8\. [^\n]*\n(.*?)^### ", "§8 (상태 클래스)"),
]


def parse_js_dom_registry():
    """docs/hooks.md에서 'JS가 만드는 클래스' 목록을 읽는다 (§5.6 + §8).

    표가 정본이다. 목록을 이 파일에 복사해 두면 문서와 갈라지고, 갈라진 뒤에는
    **코드 쪽이 조용히 이긴다** — 문서에 클래스를 더해도 검사는 모른 척한다.

    반환: (클래스 목록, CSS 예외 집합, 구조 오류 메시지 또는 None)
    """
    doc = read(HOOKS_MD)
    if doc is None:
        return [], set(), "docs/hooks.md가 없다"

    names, sec = [], None
    for pattern, label in REGISTRY_SECTIONS:
        m = re.search(pattern, doc, re.S | re.M)
        if not m:
            return [], set(), "docs/hooks.md에서 %s 절을 찾지 못했다" % label
        body = m.group(1)
        if sec is None:
            sec = body        # 예외 목록은 §5.6에만 있다
        found = 0
        for line in body.split("\n"):
            if not line.startswith("|"):
                continue
            cells = line.split("|")
            if len(cells) < 3:
                continue
            for tick in re.findall(r"`([^`]+)`", cells[1].strip()):
                # `body.is-lightbox-open` → .is-lightbox-open,
                # `.code-wrap.has-lines` → .code-wrap + .has-lines,
                # `.hljs-*` → 접두 항목(뒤에서 따로 다룬다)
                for cls in re.findall(r"\.[A-Za-z][\w-]*\*?", tick):
                    found += 1
                    if cls not in names:
                        names.append(cls)
        # 절은 찾았는데 표가 비었다 = 표 모양이 바뀐 것이다. 조용히 줄어들면
        # 검사가 그만큼 꺼진 채로 초록불이 된다.
        if not found:
            return [], set(), "%s 표에서 클래스를 하나도 읽지 못했다 (표 모양이 바뀌었나)" % label

    if not names:
        return [], set(), "등재 표에서 클래스를 하나도 읽지 못했다"

    # 예외는 **이유와 함께** 등재해야 인정한다. 이름만 적힌 줄은 예외가 아니다 —
    # 이유 없는 예외는 "안 한 일"과 "정상"을 구분할 수 없게 만든다.
    exempt, started = set(), False
    if NO_CSS_HEADING in sec:
        for line in sec.split(NO_CSS_HEADING, 1)[1].split("\n"):
            if line.startswith("- "):
                started = True
                mm = re.match(r"- `(\.[A-Za-z][\w-]*)`\s*—\s*\S", line)
                if mm:
                    exempt.add(mm.group(1))
            elif line[:1].isspace():
                continue        # 줄바꿈으로 이어진 항목. 여기서 끊으면 다음 예외를 잃는다
            elif line.strip() and started:
                break           # 들여쓰기 없는 산문 — 목록이 끝났다
    return names, exempt, None


def strip_js_comments(js):
    """블록 주석과 **줄 전체가 주석인 줄**을 지운다.

    줄 끝 주석(`… // 메모`)은 건드리지 않는다 — 문자열 안의 `https://`를
    잘라 내면 같은 줄의 클래스 이름까지 사라져 BND007이 오탐한다.
    상시 경고는 린트를 통째로 무시하게 만든다(`TOK002` 전례)."""
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return "\n".join("" if re.match(r"\s*//", l) else l for l in js.split("\n"))


def lint_js_dom_classes(src_css, js):
    """§5.6이 등재한 'JS가 만드는 클래스'가 CSS와 JS 양쪽에 살아 있는가.

    BND004는 **반대 방향만** 본다 — JS가 *찾는* 클래스가 skin.html에 있는가.
    JS가 *만드는* 클래스는 마크업에 자리가 없어 그 검사에 애초에 안 걸리고,
    JS에서 이름을 바꾸거나 새로 만들면서 CSS를 안 고쳐도 아무 에러도 안 난다.
    스타일 없는 날것 DOM이 뜨고 끝이다 (DECISIONS.md 결정 40).

    두 축을 같이 본다. CSS 축만 보면 **문서가 JS에서 떨어져 나간 순간 검사가
    죽은 이름을 보고 통과한다** — 위조된 통과 신호(docs/HARNESS.md 「핵심 위험」)의 네 번째 판이다.

    CSS는 **src만** 본다. dist는 src의 사본이라, src에서 규칙을 지워도 낡은
    dist에 남아 있으면 통과해 버린다 (TIS00x가 src만 보는 것과 같은 이유).
    """
    if not src_css:
        return
    names, exempt, structural = parse_js_dom_registry()
    if structural:
        err("BND006", "%s. 등재 표(§5.6·§8)가 이 검사의 정본이라 표를 못 읽으면 검사가 "
            "통째로 꺼진다 — 조용히 꺼지지 않게 오류로 낸다." % structural, "docs/hooks.md")
        return

    # 선택자만 남긴다. `content: "…"` 같은 선언 값에 이름이 스쳐도
    # "규칙이 있다"로 세면 안 된다. @media 중첩은 `{` 앞 조각만 모으면 알아서 풀린다.
    selectors = " ".join(re.findall(r"([^{}]*)\{", strip_comments(src_css)))
    # JS도 같다 — 주석에 옛 이름이 남아 있는 것은 그 이름이 살아 있다는 뜻이 아니다.
    js_code = strip_js_comments(js) if js else ""

    no_css, no_js = [], []
    for cls in names:
        if cls.endswith("*"):
            # 접두 항목(`.hljs-*`)은 **라이브러리가 뱉는 묶음**이다. CSS는 그 묶음 중
            # 하나라도 있으면 되고, 우리 src/js는 이 이름들을 문자열로 적지 않으므로
            # JS 축에서는 뺀다.
            if not re.search(re.escape(cls[:-1]) + r"[\w-]+", selectors):
                no_css.append(cls)
            continue
        bare = re.escape(cls[1:])
        if cls not in exempt and not re.search(r"\." + bare + r"(?![\w-])", selectors):
            no_css.append(cls)
        if js_code and not re.search(r"(?<![\w-])" + bare + r"(?![\w-])", js_code):
            no_js.append(cls)

    if no_css:
        err("BND006", "hooks.md 등재 표(§5.6·§8)의 클래스 %d종에 CSS 규칙이 없다: %s. "
            "JS가 만들어 붙여도 스타일 없는 날것 DOM이 뜨고 에러는 안 난다. "
            "규칙이 없는 것이 정상이면 §5.6 「CSS 규칙이 없는 것이 정상인 클래스」 목록에 "
            "이유와 함께 등재한다 — 이름만 적은 줄은 예외로 치지 않는다."
            % (len(no_css), ", ".join(no_css)), "src/styles/")
    if no_js:
        warn("BND007", "hooks.md 등재 표(§5.6·§8)의 클래스 %d종이 src/js 어디에도 없다: %s. "
             "JS에서 이름을 바꿨다면 문서와 CSS가 죽은 이름을 붙들고 있는 것이고, "
             "그러면 BND006은 그 죽은 규칙을 보고 통과한다." % (len(no_js), ", ".join(no_js)),
             "src/js/")
    if not no_css and not no_js:
        info("JS 생성 클래스(§5.6·§8 등재): %d종 전부 CSS 규칙과 JS 사용처가 있다 (CSS 예외 %d종)"
             % (len(names), len(exempt)))


# ────────── 3c. 마크업이 내보내는 클래스 ↔ CSS (BND009) ──────────

MARKUP_EXEMPT_TITLE = "CSS 규칙이 없는 것이 정상인 마크업 클래스"
# **줄 전체**로 맞춘다. 부분문자열로 찾으면 산문에 제목을 인용하기만 해도
# 검사가 «목록을 찾았다»고 착각한다 — 이 검사의 자기 테스트가 그것부터 짚었다.
MARKUP_EXEMPT_HEADING = re.compile(r"^#{2,4}\s*" + re.escape(MARKUP_EXEMPT_TITLE) + r"\s*$", re.M)


def parse_markup_exemptions():
    """docs/hooks.md §7의 예외 목록을 읽는다. 형식은 §5.6과 같다.

    반환: (예외 집합, 구조 오류 메시지 또는 None)
    """
    doc = read(HOOKS_MD)
    if doc is None:
        return set(), "docs/hooks.md가 없다"
    m = MARKUP_EXEMPT_HEADING.search(doc)
    if not m:
        return set(), "docs/hooks.md에서 「%s」 절을 찾지 못했다" % MARKUP_EXEMPT_TITLE
    sec = doc[m.end():]
    sec = re.split(r"^#{2,3} ", sec, maxsplit=1, flags=re.M)[0]

    exempt = set()
    for line in sec.split("\n"):
        if not line.startswith("- "):
            continue
        # 한 줄에 이름을 여럿 적을 수 있다 (`.a` · `.b` — 이유).
        head, sep, reason = line[2:].partition("—")
        if not sep or not reason.strip():
            continue          # 이유 없는 줄은 예외가 아니다 (결정 40)
        exempt |= set(re.findall(r"`(\.[A-Za-z][\w-]*)`", head))
    if not exempt:
        return set(), "예외 목록에서 클래스를 하나도 읽지 못했다 (목록 모양이 바뀌었나)"
    return exempt, None


def lint_markup_css(skin, src_css):
    """skin.html이 내보내는 클래스에 CSS 규칙이 있는가.

    **마크업이 이 저장소에서 가장 큰 표면인데(142종) 검사 축이 비어 있었다.**
    `BND004`는 JS가 *찾는* 이름만 보고, `BND006`은 JS가 *만드는* 이름만 본다 —
    마크업이 내보내는 이름은 어느 쪽에도 안 걸린다. `skin.html`에서 클래스를
    개명하고 CSS를 안 고치면 선택자가 매칭되지 않을 뿐 **에러가 없다.**

    규칙이 없는 것이 정상인 이름이 실제로 많다(컨테이너, 기본 층, 예비 훅).
    그래서 §5.6과 **같은 형식의 예외 목록**을 문서에 두고 여기서 읽는다.
    목록을 이 파일에 복사하지 않는 이유도 같다 — 갈라지면 코드가 조용히 이긴다.

    CSS는 **src만** 본다. dist는 src의 사본이라 src에서 규칙을 지워도 낡은
    dist에 남아 있으면 통과해 버린다 (`BND006`·`TIS00x`와 같은 이유).
    """
    if not skin or not src_css:
        return
    exempt, structural = parse_markup_exemptions()
    if structural:
        err("BND009", "%s. 예외 목록이 이 검사의 정본이라 목록을 못 읽으면 검사가 "
            "통째로 꺼진다 — 조용히 꺼지지 않게 오류로 낸다." % structural, "docs/hooks.md")
        return

    body = re.sub(r"<!--.*?-->", "", skin, flags=re.S)
    names = []
    for m in re.finditer(r"""class=["']([^"']+)["']""", body):
        for cls in m.group(1).split():
            # 클래스 자리가 통째로 치환자인 것(`[##_list_style_##]` 등)은 값이
            # 티스토리에서 오므로 우리가 규칙을 보장할 수 없다.
            if cls.startswith("[##_") or cls in names:
                continue
            names.append(cls)

    # 선택자만 남긴다 (`content: ".post"` 같은 선언 값에 스친 것을 세면 안 된다).
    selectors = " ".join(re.findall(r"([^{}]*)\{", strip_comments(src_css)))
    missing = [c for c in names
               if "." + c not in exempt
               and not re.search(r"\." + re.escape(c) + r"(?![\w-])", selectors)]
    if missing:
        err("BND009", "skin.html이 내보내는 클래스 %d종에 CSS 규칙이 없다: %s. "
            "마크업에서 이름을 바꾸고 CSS를 안 고치면 선택자가 매칭되지 않을 뿐 "
            "에러가 없다 — 스타일 없는 날것이 뜬다. 규칙이 없는 것이 정상이면 "
            "hooks.md §7 「CSS 규칙이 없는 것이 정상인 마크업 클래스」에 **이유와 함께** "
            "등재한다." % (len(missing), ", ".join("." + c for c in missing[:8])),
            "src/styles/")
    else:
        info("마크업 클래스: %d종 전부 CSS 규칙이 있다 (예외 %d종)"
             % (len(names), len(exempt)))


# ───────────────────────── 4. 디자인 토큰 준수 ─────────────────────────

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3,8})\b")


def media_blocks(css):
    """`@media` 블록 목록 [(질의, 본문)] — 중괄호를 세어 자른다. 중첩 블록도 각각 잡힌다."""
    out = []
    for m in re.finditer(r"@media\s*([^{]+)\{", css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        out.append((m.group(1).strip(), css[m.end():i - 1]))
    return out


# ────────── 3d. 썸네일 그룹 안에는 img만 (BND011) ──────────

THUMB_GROUP_RE = re.compile(r"<(s_[a-z0-9_]*_thumbnail)>(.*?)</\1>", re.S)


def lint_thumb_groups(skin):
    """`<s_*_thumbnail>` 그룹 치환자 안에 `<img>` 하나만 있는가 — BND011 (결정 57).

    티스토리는 대표이미지가 없으면 이 그룹을 **블록째** 지운다. 그룹 안에 상자
    (`.related-thumb`·`.side-thumb`·`.postnav-thumb` 같은 span)까지 넣어 두면 상자도
    같이 사라져 그 줄의 제목이 상자 폭만큼 왼쪽으로 튄다 — 라이브 글 페이지
    「'기록'의 다른 글」 4건 중 2건이 그랬다(2026-09-14 실측). 홈 카드는 처음부터
    `.thumb`가 밖, `.thumb-img`가 안이었는데(결정 5) 나머지 셋은 반대였고, 프리뷰가
    그 조건을 그리고 있었는데도 본 사람이 없었다. 구조 규칙이라 린트로 고정한다.

    주석은 벗기고 본다 — 상자를 밖으로 빼며 남긴 설명 주석이 그룹 안에 있을 수 있다.
    """
    if not skin:
        return
    bad = []
    for m in THUMB_GROUP_RE.finditer(skin):
        inner = re.sub(r"<!--.*?-->", "", m.group(2), flags=re.S).strip()
        if not re.fullmatch(r"<img\b[^>]*>", inner):
            bad.append(m.group(1))
    if bad:
        err("BND011", "썸네일 그룹 %d곳 안에 <img> 말고 다른 것이 있다: %s. 대표이미지가 없으면 "
            "그룹이 블록째 사라지므로 상자(span)는 그룹 **밖**에, img만 안에 둔다 — 안 그러면 "
            "그 줄이 상자 폭만큼 왼쪽으로 튄다(결정 57)." % (len(bad), ", ".join(bad)),
            "src/skin.html")


def lint_notice_body(skin):
    """공지 본문 그릇이 서버 HTML에서부터 `contents_style`을 다는가 — BND012 (이슈 #97).

    `[##_notice_rep_desc_##]`가 티스토리 본문 래퍼를 달고 오는지 모른다. 첫 판은
    `notice.js`가 없을 때 붙였는데, 그러면 첫 페인트 뒤에 본문 시트(문단 여백)가 걸려
    공지마다 24px씩 아래가 밀렸다 — 프리뷰 공지 2건에 48px, 3페이지 × 4폭 12경우 전부.
    이 밀림은 `script.js`를 붙잡아야만 보여서 `npm run check`에 나오지 않는다. 그런데 원인은
    「마크업에 클래스가 있는가」 하나라 정적으로 고정할 수 있다. `notice.js`는 이제 티스토리가
    안쪽에 래퍼를 달아 온 경우에만 바깥 것을 뗀다(안쪽이 같은 시트를 받아 기하는 그대로다).

    주석은 벗기고 본다. `.notice-body`를 못 찾으면 통과가 아니라 오류다(결정 40).
    """
    if not skin:
        return
    body = re.sub(r"<!--.*?-->", "", skin, flags=re.S)
    tags = [m.group(1).split() for m in re.finditer(r"""<[a-z][^>]*\bclass=["']([^"']*)["']""", body)]
    notice = [t for t in tags if "notice-body" in t]
    if not notice:
        err("BND012", "skin.html에서 `.notice-body`를 찾지 못했다 — 검사가 꺼진 것이지 통과가 아니다. "
            "이름을 바꿨으면 이 규칙과 notice.js·hooks.md §5.7을 같이 옮긴다.", "src/skin.html")
        return
    if any("contents_style" not in t for t in notice):
        err("BND012", "`.notice-body`에 `contents_style`이 없다. JS가 나중에 붙이면 첫 페인트 뒤에 본문 시트가 "
            "걸려 공지마다 문단 여백만큼 아래가 밀린다(이슈 #97 — 공지 2건에 48px). 서버 HTML에서부터 "
            "`class=\"notice-body contents_style\"`로 단다(hooks.md §5.7).", "src/skin.html")


def lint_const_pairs(skin):
    """두 곳에 적혀야 하는 상수가 같은가 — BND010 (결정 48).

    ① `skin.html`의 `no-toc` 인라인은 `toc.js`·`util.headingsWithIds`의 조건을
       **손으로 복사**한 것이다(첫 페인트 전에 돌아야 해서 번들에 못 넣는다).
       임계(`MIN_HEADINGS`)나 선택자가 한쪽만 바뀌면 목차는 없는데 2칸이거나 그
       반대가 된다 — 결정 48이 없앤 바로 그 시프트가 린트 초록불로 돌아온다.
    ② 목차 접이식 경계는 넷이 같아야 한다 — `toc.js` `COLLAPSIBLE_MQ` max-width,
       `components.css`의 `.toc:not(.is-open)` 블록 max-width, `.toc.is-ready` 블록
       min-width(= max + 1), `layout.css` 3단 블록 min-width. 어긋나면 CSS는 접는데
       JS는 `aria-expanded`를 지운다(QA F2). 1024/1400으로 갈려 있던 것이 이 규칙의 출생이다.
    ③ 목차 DOM 순서와 3단 `order`(결정 64) — `skin.html`에서 `.entry-aside`가 `.entry-main` **앞**이고
       (DOM 순서 = 읽기 순서), `layout.css` 기본 `.entry-aside`에는 `order`가 없으며, 3단 블록(②의 경계)의
       `.entry-aside`가 `order: 1`이어야 한다. aside만 뒤로 되돌리면 Tab이 조용히 본문 뒤로 돌아가고,
       `order: 1`만 지우면 목차가 본문 칸으로 간다 — 둘 다 `npm run check`가 통과했다(결정 64 체크포인트).

    어느 한쪽을 **못 찾으면 통과가 아니라 오류**다 — 검사가 꺼진 것과 통과는 다르다(결정 40).
    """
    toc = read(os.path.join(SRC, "js", "toc.js")) or ""
    util = read(os.path.join(SRC, "js", "util.js")) or ""
    comp = strip_comments(read(os.path.join(SRC, "styles", "components.css")) or "")
    layout = strip_comments(read(os.path.join(SRC, "styles", "layout.css")) or "")
    body = re.sub(r"<!--.*?-->", "", skin, flags=re.S)
    problems = []

    def need(m, what):
        if not m:
            problems.append("%s를 찾지 못했다 — 검사가 꺼진 것이지 통과가 아니다" % what)
        return m

    # ① no-toc 임계·선택자
    js_min = need(re.search(r"const MIN_HEADINGS = (\d+)", toc), "toc.js의 `MIN_HEADINGS`")
    # 인라인 안에 `i<h.length` 같은 `<`가 있으므로 `[^<]*`로 건너뛰면 못 찾는다 —
    # <script> 블록을 먼저 자르고 그 안에서 찾는다.
    inline = None
    for sm in re.finditer(r"<script>(.*?)</script>", body, re.S):
        if "'no-toc'" in sm.group(1):
            inline = re.search(
                r"querySelectorAll\('([^']+)'\).*?n<(\d+)\)document\.body\.classList\.add\('no-toc'\)",
                sm.group(1), re.S)
            break
    inline = need(inline, "skin.html의 no-toc 인라인 스크립트")
    need(re.search(r"querySelectorAll\('h2, h3'\)", util), "util.js `headingsWithIds`의 `'h2, h3'`")
    if js_min and inline:
        if int(js_min.group(1)) != int(inline.group(2)):
            problems.append("no-toc 임계가 다르다: toc.js MIN_HEADINGS=%s ↔ skin.html 인라인 n<%s"
                            % (js_min.group(1), inline.group(2)))
        if inline.group(1) != ".entry-body h2, .entry-body h3":
            problems.append("no-toc 인라인의 선택자가 `.entry-body h2, .entry-body h3`가 아니다: `%s` "
                            "(util.headingsWithIds는 entryRoot 안의 h2, h3를 센다)" % inline.group(1))

    # ② 접이식 경계
    js_mq = need(re.search(r"COLLAPSIBLE_MQ = '\(max-width: (\d+)px\)'", toc), "toc.js의 `COLLAPSIBLE_MQ`")

    def widths(blocks, marker, kind):
        found = []
        for q, b in blocks:
            if marker in b:
                m = re.search(kind + r"-width:\s*(\d+)px", q)
                if m:
                    found.append(int(m.group(1)))
        return found
    css_max = widths(media_blocks(comp), ".toc:not(.is-open)", "max")
    css_min = widths(media_blocks(comp), ".toc.is-ready", "min")
    lay_min = widths(media_blocks(layout), ".no-toc .entry-layout", "min")
    need(css_max, "components.css의 `.toc:not(.is-open)` max-width 블록")
    need(css_min, "components.css의 `.toc.is-ready` min-width 블록")
    need(lay_min, "layout.css의 `.no-toc .entry-layout` 3단 min-width 블록")
    if js_mq and css_max and css_min and lay_min:
        want = int(js_mq.group(1))
        if set(css_max) != {want} or set(css_min) != {want + 1} or set(lay_min) != {want + 1}:
            problems.append("목차 접이식 경계가 어긋난다: toc.js %d ↔ components.css max %s / min %s "
                            "↔ layout.css 3단 min %s (max = toc.js, min = max + 1이어야 한다)"
                            % (want, css_max, css_min, lay_min))

    # ③ 목차 DOM 순서 ↔ 3단 order (결정 64)
    i_aside = body.find('<aside class="entry-aside"')
    i_main = body.find('<div class="entry-main"')
    if need(i_aside >= 0 and i_main >= 0, "skin.html의 `aside.entry-aside`·`div.entry-main`") and i_aside > i_main:
        problems.append("skin.html에서 `.entry-aside`가 `.entry-main` 뒤에 있다 — DOM 순서가 읽기 순서다"
                        "(목차 → 본문, 결정 64). 3단의 오른쪽 열은 layout.css의 order가 만든다")
    top = layout
    for _q, blk in media_blocks(layout):
        top = top.replace(blk, "")
    if any(re.search(r"\border\s*:", m.group(1)) for m in re.finditer(r"\.entry-aside\s*\{([^}]*)\}", top)):
        problems.append("layout.css 기본 `.entry-aside`에 order가 있다 — 1399px 이하 화면 순서는 DOM 순서"
                        "(목차 → 본문)여야 Tab·낭독과 같다(결정 64)")
    bp = (int(js_mq.group(1)) + 1) if js_mq else 1400
    wide = [blk for q, blk in media_blocks(layout) if re.search(r"min-width:\s*%dpx" % bp, q)]
    if need(wide, "layout.css의 3단(min-width %dpx) 블록" % bp) and not any(
            re.search(r"\.entry-aside\s*\{[^}]*\border\s*:\s*1\s*;", blk) for blk in wide):
        problems.append("layout.css 3단 블록의 `.entry-aside`에 `order: 1`이 없다 — DOM에서 목차가 먼저라 "
                        "order 없이는 %dpx 이상에서 목차가 본문 칸(1열)으로 간다(결정 64)" % bp)

    for p in problems:
        err("BND010", p + ". 두 곳에 적히는 상수는 같이 옮긴다 — 어긋나도 화면에 신호가 없다(결정 48).",
            "src/skin.html · src/js/toc.js · src/styles/")


def strip_comments(css):
    """/* … */ 를 걷어낸다.

    주석 안의 hex는 색 지정이 아니라 **설명**이다. tistory.css는 티스토리가 박아 둔
    리터럴(#333 · #909090 …)을 주석에 적어 두는데, 걷어내지 않으면 TOK001이
    그것을 매번 경고한다. 상시 경고는 린트를 통째로 무시하게 만든다 —
    같은 오탐으로 이미 한 번 데었다(`TOK002` 전례 — DECISIONS.md 결정 40)."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def lint_tokens(css):
    if not css:
        return
    # 토큰 정의부(:root 블록)와 인라인 스타일 보정 선택자는 제외한다
    body = strip_comments(css)
    body = re.sub(r":root[^{]*\{[^}]*\}", "", body, flags=re.S)
    body = re.sub(r"\[style\*=\"[^\"]*\"\]", "", body)
    hexes = HEX_RE.findall(body)
    if hexes:
        uniq = sorted(set(h.lower() for h in hexes))
        warn("TOK001", "토큰을 거치지 않은 색 리터럴 %d종: %s. var(--토큰)을 쓰지 않으면 "
             "다크모드에서 바뀌지 않는다." % (len(uniq), ", ".join(uniq[:8])), "src/styles/")

    # 미디어쿼리/[data-theme] 안에서 처음 정의된 색 → stamp 없는 시스템 테마에서 깨진다
    for m in re.finditer(r"(@media[^{]*prefers-color-scheme[^{]*|:root\[data-theme[^{]*)\{(.*?)\n\}",
                         strip_comments(css), re.S):
        block = m.group(2)
        # `[style*="color: #000000"]` 같은 속성 선택자 줄은 **매칭 대상**이지 선언이 아니다.
        # 걷어내지 않으면 인라인 보정 규칙이 통째로 오탐된다.
        lines = [re.sub(r'\[style\*="[^"]*"\]', "", l) for l in block.split("\n")]
        non_token = [l.strip() for l in lines
                     if re.search(r"(?<!-)(?:color|background)\s*:", l) and "--" not in l]
        if non_token:
            err("TOK002", "다크모드 블록 안에서 토큰이 아닌 색을 직접 지정한다: %s. "
                "시스템 테마(stamp 없음) 상태에서 한쪽 테마 글자가 다른 쪽 배경에 얹힌다."
                % non_token[0][:70], "src/styles/")

    if "prefers-color-scheme" not in css:
        err("TOK003", "prefers-color-scheme 미디어쿼리가 없다. 시스템 다크 설정이 반영되지 않는다.",
            "src/styles/")
    if 'data-theme="light"' not in css:
        warn("TOK004", ':root:not([data-theme="light"]) 가드가 없다. '
             "사용자가 라이트를 명시했는데 OS가 다크면 다크가 이긴다.", "src/styles/")
    if not re.search(r"body\s*\{[^}]*background", css, re.S):
        warn("TOK005", "body에 배경색이 지정되지 않았다. 투명 배경은 호스트 색을 그대로 비친다.",
             "src/styles/")


def lint_token_usage(css, has_built):
    """토큰의 **정의 ↔ 참조**를 맞춰 본다.

    두 방향 모두 이 도메인의 조용한 실패다.

    ① 참조는 있는데 정의가 없다 — `var(--cavas)` 오타는 에러가 아니라
       **선언 전체가 무효**가 되어 그 속성이 상속값이나 초기값으로 떨어진다.
       화면에는 "왜 여기만 색이 다르지" 정도로만 나타난다. 오류로 낸다.

    ② 정의는 있는데 참조가 없다 — 해롭지는 않다. 정보로만 낸다. 그런데 이쪽이
       이 검사를 만든 이유다. 2026-08-26 결정 44가 `--error`의 사용처를 옮기고
       "**살아 있는 사용처가 없다**"고 세 문서에 적었는데 **틀렸다** —
       `scripts/build.mjs`의 ACCENT 맵이 본문 인라인색 `#ee2323`을 그 토큰으로
       보내고 있었다. `src/styles`를 grep하면 주석밖에 안 나온다: 사용처가
       **생성기의 문자열 안**에 있고 결과는 `dist/style.css`에만 있다.

    ⚠ **그래서 src만 보면 안 된다.** 빌드 산출물까지 합친 CSS를 받는다.
       dist가 없으면 ①의 판정 근거(생성된 `--ph-*` 정의)가 통째로 빠지므로
       아예 돌지 않는다 — 근거 없이 오류를 내는 것보다 안 도는 편이 낫다.
    """
    if not css or not has_built:
        return
    body = strip_comments(css)
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", body))
    used = set(re.findall(r"var\(\s*(--[a-z0-9-]+)", body))

    undefined = sorted(used - defined)
    if undefined:
        err("TOK006", "정의되지 않은 토큰을 %d종 참조한다: %s. CSS는 에러를 내지 않는다 — "
            "선언 전체가 무효가 되어 그 속성이 상속값으로 떨어진다."
            % (len(undefined), ", ".join(undefined[:8])), "src/styles/")

    unused = sorted(defined - used)
    if unused:
        info("참조가 없는 토큰 %d종: %s. 해롭지는 않다. 다만 «비어 있다»고 "
             "문서에 적기 전에 이 목록을 본다 — 생성기(scripts/build.mjs)가 "
             "문자열로 쓰는 사용처는 src grep에 안 잡힌다 (결정 44 정정)."
             % (len(unused), ", ".join(unused)))
    else:
        info("토큰: 정의 %d종 전부 참조됨, 미정의 참조 0" % len(defined))


def lint_image_refs(built, dist_dir):
    """`dist/style.css`가 가리키는 `images/` 파일이 **실재하는지** 본다.

    기본 이미지가 SVG `data:` 인라인에서 업로드 WebP 30장으로 바뀌면서
    (결정 5·6 개정) 새 침묵이 하나 생겼다 — **변수는 정의돼 있는데 파일이 없다.**
    업로드 누락, 파일명 버전 불일치(`.v1` → `.v2`), 빌드의 복사 실패, 셋이 전부
    같은 얼굴이다. CSS는 `url()`이 404여도 에러를 내지 않는다 —
    `background-image`가 그냥 안 그려지고 카드에 점격자만 남는다.
    파일이 테마별로 나뉘어 있어 **라이트는 멀쩡한데 다크만 비는** 것도 가능하다.

    `TOK006`은 이것을 원리적으로 못 본다 — 변수의 **정의 ↔ 참조**만 보므로
    `--ph-db: url("./images/없는파일.webp")`는 정의도 참조도 멀쩡하다.

    ⚠ **빌드 산출물만 본다.** 경로가 `dist/` 기준 상대경로라 src에는 판정할
       근거가 아예 없다. dist가 없으면 안 돈다 — 근거 없이 오류를 내는 것보다
       안 도는 편이 낫다(`TOK006`과 같은 이유).
    """
    if not built:
        return
    body = strip_comments(built)

    # url() 안의 따옴표는 세 가지가 다 유효하다: url(x) url('x') url("x").
    # data:는 대상이 아니다. 절대 URL은 **경로에 images/<파일>이 있으면** 본다 —
    # 빌드의 PLACEHOLDER_BASE를 CDN으로 바꿔도(미결 1의 탈출구) 파일은 dist/images/에 그대로
    # 남고 CDN은 그것을 비추는 것이라, 접두사가 무엇이든 이 검사가 조용히 꺼져서는 안 된다.
    refs = {}
    for m in re.finditer(r"""url\(\s*(['"]?)([^'")]+?)\1\s*\)""", body):
        target = m.group(2).strip()
        if target.startswith("data:"):
            continue
        rel = re.search(r"(?:^|/)images/([^/?#]+)$", target.split("?")[0].split("#")[0])
        if not rel:
            continue
        name = rel.group(1)
        refs[name] = refs.get(name, 0) + 1

    if not refs:
        # 검사가 꺼진 것과 통과한 것은 다른 일이다 (결정 40).
        info("dist/style.css에 images/ 참조가 없다 — TOK007은 판정하지 않았다. "
             "기본 이미지가 아직 인라인이거나 빌드가 옛 구조다.")
        return

    missing = sorted(n for n in refs if not os.path.isfile(os.path.join(dist_dir, "images", n)))
    if missing:
        err("TOK007", "dist/style.css가 가리키는 images/ 파일 %d종이 dist/images/에 없다: %s. "
            "CSS는 에러를 내지 않는다 — 카드에 점격자만 남는다. 업로드 누락이거나 "
            "파일명 버전 불일치(package.json placeholderVersion)이거나 빌드가 복사에 실패했다."
            % (len(missing), ", ".join(missing[:8])), "dist/images/")
    else:
        info("기본 이미지: dist/style.css의 images/ 참조 %d종(%d회) 전부 dist/images/에 있다."
             % (len(refs), sum(refs.values())))


# ───────────────────── 5. 인라인 스타일 보정 커버리지 ─────────────────────

def lint_inline_coverage(css):
    """DESIGN.md의 열거 목록이 실제 데이터를 다 덮는지 확인한다."""
    if not css:
        return
    covered = set(m.lower() for m in re.findall(r'\[style\*="color:\s*(#[0-9a-fA-F]{6})"\]', css))
    covered |= set(m.lower() for m in
                   re.findall(r'\[style\*="background-color:\s*(#[0-9a-fA-F]{6})"\]', css))
    known = os.path.join(ROOT, "data", "inline-styles.json")
    if not os.path.exists(known):
        info("data/inline-styles.json이 없어 인라인색 커버리지를 검사하지 않았다. "
             "blog-analyst에게 실측을 요청하면 생성된다.")
        return
    d = json.load(open(known, encoding="utf-8"))
    missing = [c for c in d.get("needsFix", []) if c.lower() not in covered]
    if missing:
        err("INL001", "보정 규칙이 없는 인라인 색 %d종: %s. 해당 글에서 글자가 배경에 묻힌다."
            % (len(missing), ", ".join(missing[:10])), "src/styles/")
    else:
        info("인라인색 보정: 실측 %d종 전부 커버됨" % len(d.get("needsFix", [])))


# ────────────────── 5b. 티스토리가 박아 둔 라이트 전용 색 ──────────────────

def lint_tistory_hardcoded(css):
    """data/tistory-hardcoded-colors.json의 각 항목에 우리 덮어쓰기가 있는지 본다.

    인라인색(INL001)과는 원리가 다르다. 저 색들은 글 본문의 style 속성에 있어
    [style*=...]로 잡히지만, 여기 색들은 **티스토리 스타일시트**에서 온다 —
    속성 선택자로는 원리적으로 닿지 않고, 상당수가 #tt-body-page ID 스코프라
    클래스만으로는 특이도도 모자란다. 둘 다 놓치면 다크에서만 조용히 깨진다."""
    known = os.path.join(ROOT, "data", "tistory-hardcoded-colors.json")
    if not os.path.exists(known):
        info("data/tistory-hardcoded-colors.json이 없어 티스토리 하드코딩 색 대응을 "
             "검사하지 않았다.")
        return
    if not css:
        return
    body = strip_comments(css)
    missing, unscoped = [], []
    d = json.load(open(known, encoding="utf-8"))
    for r in d.get("rules", []):
        marker = r["marker"]
        if marker not in body:
            missing.append(r["component"])
            continue
        # 상대가 ID로 시작하면 우리도 ID를 붙인 짝이 있어야 한다.
        # 없으면 규칙은 존재하는데 글 페이지에서만 지는, 가장 찾기 어려운 상태가 된다.
        #
        # 짝을 **문자 그대로** 찾는다. "마커 앞 200자에 #tt-body-page가 있나" 같은
        # 근접 검사를 쓰면, 옆 규칙의 ID가 우연히 걸려 짝이 없는데도 통과한다.
        # 형식을 하나로 못박는 대가로 검사가 확실해진다 — tistory.css의 규칙 2번
        # ("선택자를 그대로 베끼고 앞에만 붙인다")이 곧 이 형식이다.
        if r.get("idScoped") and "#tt-body-page .contents_style " + marker not in body:
            unscoped.append(r["component"])
    if missing:
        err("TIS001", "티스토리가 라이트 전용 색을 박아 둔 컴포넌트 %d종에 덮어쓰기가 없다: %s. "
            "다크에서 해당 요소가 배경에 묻힌다 (src/styles/tistory.css)."
            % (len(missing), ", ".join(missing[:8])), "src/styles/tistory.css")
    if unscoped:
        err("TIS002", "%d종이 #tt-body-page 짝 없이 클래스로만 덮여 있다: %s. "
            "상대 선택자가 ID로 시작하므로 **글 페이지에서만** 진다 — 목록 페이지에서 "
            "멀쩡해 보여 놓치기 쉽다." % (len(unscoped), ", ".join(unscoped[:8])),
            "src/styles/tistory.css")
    if not missing and not unscoped:
        info("티스토리 하드코딩 색: %d종 전부 토큰으로 덮음" % len(d.get("rules", [])))


def lint_tistory_comment_scope(css):
    """댓글·방명록에 우리 규칙이 **실제로 이기는 특이도로** 있는지 본다.

    TIS001/TIS002와 원리가 다르다. 저쪽 상대는 content.css라 크롤로 읽을 수 있고
    상당수가 #tt-body-page ID 스코프다. 여기 상대는 **React가 런타임에 얹는
    시트**다 — 소스 HTML에는 <div data-tistory-react-app="Comment"> 빈 껍데기뿐이라
    크롤로는 존재조차 보이지 않고, 프리뷰에도 나오지 않는다.

    그리고 상대 특이도가 (0,2,0)이다. 클래스 하나(0,1,0)로 쓰면 지고, 둘(0,2,0)로
    써도 순서로 가서 진다 — 순서는 티스토리가 정한다. 조상 둘을 붙여 (0,3,0)을
    만들어야 이긴다 (2026-08-26 라이브 실측).

    실제로 이 검사가 없던 동안 댓글 블록이 **통째로** 지고 있었다. 다크에서
    댓글 본문이 #222로 나와 1.16:1이었는데, 같은 블록의 .tt-box-total과 <input>은
    이기고 있어서 화면에 "전부 무시되고 있다"는 신호가 없었다.

    래퍼가 .comments(글)와 .guestbook(방명록) 둘인데 안쪽 tt-*는 완전히 같다.
    한쪽만 쓰면 다른 쪽 페이지에서만 조용히 진다 — 그래서 짝을 함께 본다."""
    known = os.path.join(ROOT, "data", "tistory-hardcoded-colors.json")
    if not os.path.exists(known) or not css:
        return
    d = json.load(open(known, encoding="utf-8"))
    rules = d.get("commentRules", [])
    if not rules:
        return
    body = strip_comments(css)
    missing, half = [], []
    for r in rules:
        marker = r["marker"]
        # idScoped=true면 상대가 ID로 시작한다 — 조상 둘(0,3,x)로는 못 이긴다.
        # 우리도 body id를 붙인 짝이 있어야 하고, body id는 페이지마다 다르다.
        # 짝을 **문자 그대로** 찾는다(TIS002와 같은 이유 — 근접 검사는 옆 규칙의
        # ID가 우연히 걸려 통과시킨다).
        if r.get("idScoped"):
            pair_c = "#tt-body-page .comments " + marker
            pair_g = "#tt-body-guestbook .guestbook " + marker
        else:
            pair_c = ".comments " + marker
            pair_g = ".guestbook " + marker
        has_c = pair_c in body
        has_g = pair_g in body
        if not has_c and not has_g:
            missing.append(r["component"] + ("(ID 스코프)" if r.get("idScoped") else ""))
        elif not (has_c and has_g):
            half.append("%s(%s만)" % (r["component"], "글" if has_c else "방명록"))
    if missing:
        err("TIS003", "댓글 앱이 라이트 전용 값을 박아 둔 %d종에 (0,3,0) 덮어쓰기가 없다: %s. "
            "클래스 하나로 쓰면 상대 (0,2,0)에 진다 — 다크에서 댓글이 배경에 묻힌다. "
            "(ID 스코프)로 표시된 항목은 상대가 ID로 시작하므로 #tt-body-page / "
            "#tt-body-guestbook 까지 붙여야 한다."
            % (len(missing), ", ".join(missing[:8])), "src/styles/tistory.css")
    if half:
        err("TIS003", "%d종이 .comments / .guestbook 짝 없이 한쪽만 덮여 있다: %s. "
            "안쪽 tt-* 마크업이 양쪽 완전히 같으므로 **다른 쪽 페이지에서만** 진다."
            % (len(half), ", ".join(half[:8])), "src/styles/tistory.css")
    if not missing and not half:
        info("댓글·방명록 하드코딩 값: %d종 전부 .comments/.guestbook 짝으로 덮음" % len(rules))


# 프로필 카드 덮어쓰기의 **유일한 형태**. 데이터(json)에도 같은 문자열이 있고
# 여기서는 그것을 기본값으로만 쓴다 — 둘이 갈라지면 json 쪽을 따른다.
NAMECARD_PREFIX = '.entry-main [data-tistory-react-app="Namecard"] .tt_box_namecard'


def selector_blocks(body, needle):
    """`needle`이 **선택자 하나로 끝나는** 규칙들의 선언 블록을 모은다.

    단순 부분문자열 검사로는 안 된다. `… .tt_btn_subscribe`는
    `… .tt_btn_subscribe.type2`의 부분문자열이기도 해서, 구독 중 상태만 덮고
    기본 상태를 안 덮어도 통과해 버린다 — 「썼는데 절반만 이긴다」가 그렇게 생긴다.
    그래서 뒤에 오는 첫 비공백 문자가 `{` 또는 `,`인 것만 센다.

    **선언 블록까지 돌려주는 이유**: 선택자만 보면 「규칙은 있는데 엉뚱한 것을
    덮는」 상태를 통과시킨다. 2026-09-10 리뷰에서 재현했다 — `.tt_desc`의
    `color`를 `font-size`로 바꿔도 오류가 0이었다. 검사가 확인한 것보다
    많이 말하면 없느니만 못하다.
    """
    out = []
    i = body.find(needle)
    while i != -1:
        j = i + len(needle)
        while j < len(body) and body[j] in " \t\r\n":
            j += 1
        if j < len(body) and body[j] in "{,":
            k = body.find("{", j)
            end = body.find("}", k + 1) if k != -1 else -1
            out.append(body[k + 1:end] if k != -1 and end != -1 else "")
        i = body.find(needle, i + 1)
    return out


# 단축 속성으로 써도 그 자리를 덮은 것으로 인정한다. `min-height`처럼 단축이
# 없는 것은 여기 없다 — 없는 것을 넣으면 검사가 조용히 헐거워진다.
CSS_SHORTHAND = {"background-color": ("background",), "border-color": ("border",)}


def declares(block, prop):
    """선언 블록이 `prop`(또는 그 단축)을 **선언하는가**.

    ⚠ 이름 경계를 본다. `color:`를 그냥 찾으면 `background-color:`·`border-color:`가
       걸려, 배경만 덮고 글자색을 안 덮어도 통과한다.
    """
    for name in (prop,) + CSS_SHORTHAND.get(prop, ()):
        if re.search(r"(?<![-\w])%s\s*:" % re.escape(name), block):
            return True
    return False


def lint_tistory_namecard_scope(css):
    """프로필 카드(Namecard)에 (0,4,0) 덮어쓰기가 있는가.

    TIS003과 같은 부류다 — 상대가 **React가 런타임에 그리는** 앱이라 소스 HTML에는
    `<div data-tistory-react-app="Namecard"></div>` 빈 껍데기뿐이고, 시트도 댓글과
    같은 `static/pc/dist/index.css`에서 온다. 크롤로는 존재가 안 보인다.

    왜 프리뷰가 있는데도 린트가 필요한가 — 2026-09-10부터 프리뷰가 그 시트를 싣고
    카드 픽스처도 그리므로 **눈으로도 보인다.** 그러나 프리뷰는 시트를 우리 **뒤에**
    싣고 라이브 head는 우리 **앞**이다. 순서는 티스토리가 정하고 예고 없이 바뀌므로,
    화면이 멀쩡한 것은 "지금 이 순서에서 이겼다"까지만 말해 준다. 특이도 자체는
    화면에 나타나지 않는다 — 그것을 보는 것이 이 검사다.

    상대 최대 특이도가 (0,3,0)(`.tt_btn_subscribe .tt_txt_g`, `.type2`)이라
    우리는 최소 (0,4,0)이어야 한다. 접두를 **문자 그대로** 대조하는 이유는
    TIS002·TIS003과 같다 — 근접 검색은 옆 규칙이 우연히 걸려 통과시킨다.
    """
    known = os.path.join(ROOT, "data", "tistory-hardcoded-colors.json")
    if not os.path.exists(known) or not css:
        return
    d = json.load(open(known, encoding="utf-8"))
    rules = d.get("namecardRules", [])
    if not rules:
        return
    prefix = d.get("namecardPrefix", NAMECARD_PREFIX)
    body = strip_comments(css)
    missing, weak = [], []
    for r in rules:
        marker = r["marker"]
        needle = prefix + (" " + marker if marker else "")
        blocks = selector_blocks(body, needle)
        if not blocks:
            missing.append(r["component"])
            continue
        # 선택자가 있어도 **그 속성을 덮지 않으면** 상대 값이 그대로 이긴다.
        # 규칙을 여러 개로 쪼개 쓸 수 있으므로 블록 전체를 합쳐서 본다.
        lack = [p for p in r.get("properties", []) if not any(declares(b, p) for b in blocks)]
        if lack:
            weak.append("%s(%s 없음)" % (r["component"], ", ".join(lack)))
    if missing:
        err("TIS005", "프로필 카드(Namecard)에 라이트 전용 값이 박힌 %d종에 (0,4,0) 덮어쓰기가 "
            "없다: %s. 접두를 «%s» 형태 그대로 쓰고 marker를 붙여야 한다 — 클래스 셋 이하로는 "
            "상대 (0,3,0)에 지고, 순서는 티스토리가 정한다. 다크에서 카드가 밝은 회색 판으로 뜬다."
            % (len(missing), ", ".join(missing[:8]), prefix), "src/styles/tistory.css")
    if weak:
        err("TIS005", "%d종은 선택자는 (0,4,0)인데 **덮어야 할 속성을 선언하지 않는다**: %s. "
            "규칙이 있으니 고친 것처럼 보이지만 그 자리는 상대 값이 그대로 이긴다 — "
            "덮어쓰기 중 가장 찾기 어려운 상태다."
            % (len(weak), ", ".join(weak[:8])), "src/styles/tistory.css")
    if not missing and not weak:
        info("Namecard 하드코딩 값: %d종 전부 (0,4,0) 접두 + 해당 속성으로 덮음" % len(rules))


def lint_tistory_typography(css):
    """티스토리 content.css가 **색이 아닌 속성**을 덮는 자리를 본다.

    TIS001/TIS002와 상대는 같은 시트인데 왜 축을 따로 냈나 — 드러나는 방식이
    다르기 때문이다. 색은 다크에서 "안 보인다"로 나타나 사용자가 신고한다.
    굵기·크기는 **두 테마 모두 멀쩡해 보인다.** 우리가 쓴 값이 그냥 반영되지
    않을 뿐이라, 보고 있어도 "원래 저런가 보다"가 된다.

    실제로 그렇게 놓쳤다. content.css의

        #tt-body-page h2[data-ke-size] { font-weight: normal }   (1,1,1)

    이 우리 `.contents_style h2`(0,1,1)를 이겨 소제목이 400으로 나오고 있었다.
    게다가 상대가 [data-ke-size] **있는 것만** 잡아서 60%만 지고 40%는 이겼다 —
    글마다 굵기가 달랐고, 그 불일치가 오히려 "에디터 차이인가" 하고 넘어가게 했다.
    (결정 35의 '부분적으로 동작하는 것이 더 찾기 어렵다'와 같은 모양이다.)

    ⚠ 속성 선택자는 특이도의 **클래스 칸**에 들어간다. marker에서 [data-ke-size]를
       떼면 (1,2,1)이 (1,1,1)로 내려가 상대와 같아지고, 같으면 순서가 정하는데
       순서는 티스토리가 정한다. 그래서 marker를 **문자 그대로** 대조한다
       (TIS002와 같은 이유 — 근접 검사는 옆 규칙이 우연히 걸려 통과시킨다)."""
    known = os.path.join(ROOT, "data", "tistory-hardcoded-colors.json")
    if not os.path.exists(known) or not css:
        return
    d = json.load(open(known, encoding="utf-8"))
    rules = d.get("typographyRules", [])
    if not rules:
        return
    body = strip_comments(css)
    missing, weak = [], []
    for r in rules:
        marker = r["marker"]
        if "#tt-body-page .contents_style " + marker in body:
            continue
        # 짝은 없는데 속성 선택자만 뗀 모양이 있으면 "썼는데 진다"는 상태다.
        # 그냥 없는 것보다 나쁘다 — 고쳤다고 기록될 수 있다.
        stripped = marker.split("[")[0]
        if stripped != marker and "#tt-body-page .contents_style " + stripped in body:
            weak.append("%s(%s)" % (r["component"], stripped))
        else:
            missing.append(r["component"])
    if missing:
        err("TIS004", "티스토리가 색이 아닌 속성을 덮는 %d종에 짝이 없다: %s. "
            "상대가 (1,1,1)이라 `.contents_style` 하나로는 진다 — 두 테마 모두 "
            "멀쩡해 보이는 채로 우리 값이 반영되지 않는다."
            % (len(missing), ", ".join(missing[:8])), "src/styles/tistory.css")
    if weak:
        err("TIS004", "%d종이 속성 선택자를 뗀 채로 덮여 있다: %s. "
            "특이도가 상대와 같아져(1,1,1) 순서 싸움이 되고, 순서는 티스토리가 정한다. "
            "marker를 그대로 베껴야 한다." % (len(weak), ", ".join(weak[:8])),
            "src/styles/tistory.css")
    if not missing and not weak:
        info("티스토리 비색상 덮어쓰기: %d종 전부 (1,2,1) 짝으로 덮음" % len(rules))


def lint_hljs_scope(css):
    """.hljs-* 팔레트가 .hljs 접두를 달고 있는지 본다.

    티스토리는 코드블록이 있는 글에 highlight.js의 atom-one-light를 CDN에서 주입하고,
    그 <link>는 우리 style.css **뒤**에 온다. 거기 규칙도 클래스 하나(0,1,0)라
    접두가 없으면 특이도가 같고, 같으면 뒤가 이긴다 — 우리 팔레트가 통째로 무효가 된다.
    에러도 빈 화면도 없이 라이트 테마 색이 다크 배경에 얹힌다."""
    if not css:
        return
    body = strip_comments(css)
    bare = set()
    for m in re.finditer(r"(^|[,{}\s])(\.hljs-[a-z_-]+)", body, re.M):
        # 바로 앞에 `.hljs `가 붙어 있으면 통과
        start = m.start(2)
        if body[max(0, start - 6):start].endswith(".hljs "):
            continue
        bare.add(m.group(2))
    if bare:
        err("HLJS001", "`.hljs ` 접두가 없는 구문 색 선택자 %d개: %s. 티스토리가 나중에 주입하는 "
            "atom-one-light와 특이도가 같아(0,1,0) 순서로 밀린다 — 팔레트가 화면에 닿지 않는다."
            % (len(bare), ", ".join(sorted(bare)[:6])), "src/styles/components.css")


# 유채색 자리에 허용되는 토큰 — 코드 전용 토큰뿐이다 (결정 44).
# `--ink-body`·`--ink-mute` 둘은 **일부러 무채색으로 남긴 자리**라 예외다.
CODE_NEUTRAL_OK = {"--ink-body", "--ink-mute"}


def lint_hljs_tokens(css):
    """구문 색이 **코드 전용 토큰**을 쓰는지 본다 (결정 44).

    전에는 키워드가 `--link`, 문자열·숫자가 `--ink-body`, 함수명이 `--ink`였다.
    그 결과 두 가지가 조용히 일어났다 — 문자열·숫자가 기본 코드색보다 흐렸고,
    함수명은 기본색과 **완전히 같아** 구분이 0이었다.

    더 비싼 것은 **결합**이다. 범용 토큰을 빌려 쓰면 누가 그것을 다른 이유로
    조정할 때 코드블록이 같이 움직인다. 2026-08-26에 실제로 청구됐다 —
    `--link`를 "링크니까 흰 배경 기준으로" 잡았다가 코드블록 배경 위에서
    AA 미달이 드러났다(DESIGN.md §8.1).

    ⚠ 이 검사는 **색이 예쁜지 모른다.** 어느 토큰을 쓰는지만 본다.
      대비값은 결정 44의 표가 정본이고 손으로 잰 것이다.
    """
    if not css:
        return
    body = strip_comments(css)
    bad = []
    for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", body):
        sels = rule.group(1)
        if ".hljs-" not in sels:
            continue
        for m in re.finditer(r"color\s*:\s*var\(\s*(--[a-z0-9-]+)", rule.group(2)):
            tok = m.group(1)
            if tok.startswith("--code-") or tok in CODE_NEUTRAL_OK:
                continue
            bad.append((sels.strip().split(",")[0].strip()[:40], tok))
    if bad:
        err("HLJS002", "구문 색 %d곳이 코드 전용 토큰이 아닌 것을 쓴다: %s. "
            "범용 토큰을 빌려 쓰면 누가 그것을 다른 이유로 조정할 때 코드블록이 "
            "조용히 같이 움직인다 (결정 44). 무채색으로 남기는 자리는 "
            "`--ink-body`·`--ink-mute`만 허용한다."
            % (len(bad), ", ".join("%s → %s" % b for b in bad[:5])),
            "src/styles/components.css")
    else:
        info("구문 색: 유채색 자리 전부 --code-* 토큰")


# ─────────────────────────── 5c. 읽기 고정값 (TYP001~003) ───────────────────────────

def strip_media(css, only=None):
    """`@media` 블록을 통째로 뺀 나머지 — 기본값은 전부 빼 화면 폭과 무관하게 늘 걸리는 규칙만 남긴다.
    `only`(질의 문자열 → 참/거짓)를 주면 그 질의의 블록만 뺀다(예: 인쇄 전용 블록)."""
    out, pos = [], 0
    for m in re.finditer(r"@media\s*([^{]+)\{", css):
        if m.start() < pos:
            continue
        depth, i = 1, m.end()
        while i < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        if only is not None and not only(m.group(1)):
            continue
        out.append(css[pos:m.start()])
        pos = i
    out.append(css[pos:])
    return "".join(out)


def css_rules(css):
    """[(선택자 하나, 선언 블록)] — 가장 안쪽 블록만 잡으므로 `@media` 안의 규칙도 나온다.
    선택자 목록(`a, b`)은 하나씩 푼다."""
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        for sel in m.group(1).split(","):
            sel = sel.strip()
            if sel and not sel.startswith("@"):
                out.append((sel, m.group(2)))
    return out


def last_compound_is(sel, tag):
    """선택자의 마지막 복합 선택자가 그 태그인가 — `.contents_style h2 code`·`:not(pre) > code`는 참,
    `code.hljs`나 `.code-wrap`은 거짓이다(태그 뒤에 무엇이 붙으면 다른 대상이라 본다)."""
    return re.search(r"(^|[\s>+~])%s(:[\w-]+(\([^)]*\))?)*$" % tag, sel) is not None


# 화면에 걸리는 640px 문턱으로 인정하는 질의 — 공백을 지우고 비교한다. `print and …`·`… and (hover: hover)`는
# 폰 화면을 보장하지 않으므로 받지 않는다(코드 리뷰 2026-10-11).
SCREEN_640 = {"(max-width:640px)", "screenand(max-width:640px)", "onlyscreenand(max-width:640px)"}


def lint_reading_fixed(src_css):
    """되돌려도 아무 검사도 켜지지 않던 읽기 고정값 셋을 본다 (결정 71, 이슈 #157·#165).

    TYP001  인라인 코드에 `word-break: break-all`이 없다. 있으면 안 넘치는 식별자도 한가운데서
            끊겨 조각마다 상자를 가진다 — 「타이밍 어택」 h2의 `==`가 `=` 상자 둘(라이브 390px 24개 중 5개).
            기본 규칙만이 아니라 **더 구체적인 선택자**(`.contents_style h2 code` 등)로 되살린 것도 잡는다.
    TYP002  코드블록·인라인 코드가 `font-variant-ligatures: none`을 선언하고, 그것을 되돌리는 규칙이 없다.
            없으면 JetBrains Mono의 `calt`가 `!=`를 `≠`로 그린다. `no-common-ligatures`로는 안 꺼지므로
            `none`만 인정한다. **`font` 단축 속성도 합자를 `normal`로 되돌린다** — 같은 블록에서 단축 뒤에
            `none`이 다시 오지 않거나, `pre` 밖의 `code`가 `font: inherit`로 문단·소제목의 `normal`을 받으면 잡는다.
    TYP003  640px 이하에서 「'카테고리'의 다른 글」 제목이 2줄이고 날짜가 아래 줄이다 — 그 질의 안에
            `.related-text` `-webkit-line-clamp: 2`, `.related-link` `display: grid`, `.related-thumb` `grid-row: span 2`,
            그리고 기본 `.related-text`가 clamp가 듣는 `display: -webkit-box`·`-webkit-box-orient: vertical`이다.
            1줄이면 390px 제목 칸 205px에서 연재 편이 같은 문장으로 잘렸다(K8s 4편 글 끝 4줄 중 3줄).

    셋 다 2026-10-11 체크포인트가 «무엇을 되돌려도 `npm run check`가 초록»이라고 재현했다.

    ⚠ **선언이 있는가**만 본다. 그 선언이 화면에서 이기는지는 프리뷰 본문 픽스처(`render.py`의
      `==`·`!=`·긴 URL 인라인 코드, kotlin 코드블록)를 눈으로 본다 — 이 검사는 되돌림을 막는다.
      특이도는 재지 않는다. 우회 경로(더 구체적인 선택자·`font` 단축·화면에 안 걸리는 질의)는 코드 리뷰가 낸
      것만 막았다.
    src만 본다 — dist는 사본이라 낡은 dist에 옛 규칙이 남으면 통과한다(TIS001과 같은 이유).
    """
    if not src_css:
        return
    body = strip_comments(src_css)
    rules = css_rules(body)
    hit = False
    WB_ALL = r"(?<![-\w])word-break\s*:\s*break-all"
    LIG = r"(?<![-\w])font-variant-ligatures\s*:\s*([^;}]+)"
    LIG_NONE = r"(?<![-\w])font-variant-ligatures\s*:\s*none\b"
    FONT = r"(?<![-\w])font\s*:\s*([^;}]+)"

    # ── TYP001 ──
    code_blocks = selector_blocks(body, ".contents_style code")
    if not code_blocks:
        hit = True
        err("TYP001", "`.contents_style code` 규칙을 찾지 못했다 — 인라인 코드의 줄바꿈·합자 규칙이 "
            "어디로 갔는지 모른다. 선택자를 바꿨다면 이 검사도 같이 옮긴다.", "src/styles/content.css")
    bad = sorted({sel for sel, blk in rules
                  if last_compound_is(sel, "code") and not re.search(r"(^|[\s>+~])pre\b", sel)
                  and re.search(WB_ALL, blk)})
    if bad:
        hit = True
        err("TYP001", "인라인 코드에 `word-break: break-all`이 있다: %s. 한 줄에 들어가는 식별자도 "
            "한가운데서 끊겨 조각마다 상자를 가진다(소제목의 `==`가 `=` 상자 둘). `normal` + "
            "`overflow-wrap: anywhere`면 넘칠 때만 끊긴다 (결정 71)." % ", ".join(bad[:4]),
            "src/styles/content.css")

    # ── TYP002 ──
    pre_blocks = selector_blocks(body, ".contents_style pre")
    lack = [name for name, blocks in ((".contents_style pre", pre_blocks), (".contents_style code", code_blocks))
            if not any(re.search(LIG_NONE, b) for b in blocks)]
    undo = set()
    for sel, blk in rules:
        if not (last_compound_is(sel, "code") or last_compound_is(sel, "pre")):
            continue
        for m in re.finditer(LIG, blk):
            if m.group(1).strip() != "none":
                undo.add("%s (font-variant-ligatures: %s)" % (sel, m.group(1).strip()))
        for m in re.finditer(FONT, blk):
            val = m.group(1).strip()
            in_pre = re.search(r"(^|[\s>+~])pre\b", sel) and last_compound_is(sel, "code")
            if val == "inherit":
                if not in_pre:
                    undo.add("%s (font: inherit — 부모의 normal을 받는다)" % sel)
            elif not re.search(LIG_NONE, blk[m.end():]):
                undo.add("%s (font 단축이 합자를 normal로 되돌린다)" % sel)
    if lack or undo:
        hit = True
        parts = []
        if lack:
            parts.append("합자를 끄지 않은 기본 규칙: %s" % ", ".join(lack))
        if undo:
            parts.append("합자를 되돌리는 규칙: %s" % ", ".join(sorted(undo)[:4]))
        err("TYP002", "%s. JetBrains Mono의 `calt`가 `!=`를 `≠`로, `==`를 긴 등호로 그려 원문과 다른 글자가 "
            "보인다. `font-variant-ligatures: none` — `no-common-ligatures`로는 안 꺼지고, `font` 단축은 "
            "이 값을 `normal`로 되돌린다 (결정 71)." % ". ".join(parts), "src/styles/content.css")

    # ── TYP003 ──
    def in_640(sel_name, pattern):
        return any(re.search(pattern, b)
                   for q, mbody in media_blocks(body) if re.sub(r"\s+", "", q.lower()) in SCREEN_640
                   for b in selector_blocks(mbody, sel_name))
    base = strip_media(body)
    need = [
        ("640px 질의 안 `.related-text` `-webkit-line-clamp: 2`",
         in_640(".related-text", r"(?<![-\w])-webkit-line-clamp\s*:\s*2\b")),
        ("640px 질의 안 `.related-link` `display: grid`(날짜를 제목 아래 줄로)",
         in_640(".related-link", r"(?<![-\w])display\s*:\s*grid\b")),
        ("640px 질의 안 `.related-thumb` `grid-row: span 2`(상자가 두 행에 걸친다)",
         in_640(".related-thumb", r"(?<![-\w])grid-row\s*:\s*span\s+2\b")),
        ("기본 `.related-text`의 `display: -webkit-box`·`-webkit-box-orient: vertical`(없으면 clamp가 안 듣는다)",
         any(re.search(r"(?<![-\w])display\s*:\s*-webkit-box\b", b)
             and re.search(r"-webkit-box-orient\s*:\s*vertical\b", b)
             for b in selector_blocks(base, ".related-text"))),
    ]
    miss = [name for name, ok in need if not ok]
    if miss:
        hit = True
        err("TYP003", "640px 이하 「'카테고리'의 다른 글」 2줄 규칙이 빠졌다: %s. 한 줄에 날짜와 나눠 쓰면 "
            "390px에서 제목 칸이 205px라 연재 편이 같은 문장으로 잘린다 (이슈 #157, DESIGN §4 문턱 표). "
            "질의는 화면에 걸리는 `(max-width: 640px)`만 인정한다." % "; ".join(miss),
            "src/styles/components.css")

    if not hit:
        info("읽기 고정값: 인라인 코드 break-all 없음 · 코드 합자 끔(되돌리는 규칙 없음) · 640px 이하 관련 글 2줄 + 날짜 아래")


# ─────────────────────── 5d. 작은 썸네일 상자의 카테고리 삽화 (BND013) ───────────────────────

# 삽화(--ph-cat)를 그리는 세 자리와, 대표이미지가 있으면 그것을 끄는 가드. 선택자는 공백을 하나로 접어 비교한다.
PH_TARGETS = (".post .thumb::before", ".related-thumb", ".postnav-thumb")
PH_GUARDS = (
    (".post .thumb:has(> .thumb-img)::before", r"(?<![-\w])display\s*:\s*none\b"),
    (".related-thumb:has(> .related-thumb-img)", r"(?<![-\w])background-image\s*:\s*none\b"),
    (".postnav-thumb:has(> .postnav-thumb-img)", r"(?<![-\w])background-image\s*:\s*none\b"),
)


def lint_placeholder_fill(skin, src_css):
    """대표이미지 없는 글의 상자를 카테고리 삽화로 채우는 사슬이 이어져 있는가 — BND013 (이슈 #161, 결정 5·57).

    사슬은 넷이고, 어느 고리가 빠져도 화면은 「빈 상자」나 「기본 삽화」로 **조용히** 돌아간다.
    ① `article.entry`의 `data-cat="[##_article_rep_category_##]"` — 없으면 관련 글·이전/다음이 전부
       기본 삽화로 떨어진다. BND001은 `data-cat=` 문자열을 파일 전체에서 봐서 홈 카드 `.post` 쪽으로 만족된다.
    ② 세 자리(`.post .thumb::before`·`.related-thumb`·`.postnav-thumb`)가 `background-image: var(--ph-cat`을 읽는다.
    ③ 그 세 자리를 겨누는 규칙에 `background` 단축형이 없다 — 단축형은 `background-image`를 되돌리고,
       `var(--ph-cat)`을 넣으면 치환 뒤 위치·크기가 아래 겹(SVG 폴백)에만 붙어 WebP가 원본 크기로 깔린다.
    ④ 대표이미지가 있으면 로딩 중에도 삽화를 그리지 않는 `:has()` 가드 셋(결정 57 ②).

    2026-10-11 체크포인트가 «넷 중 무엇을 되돌려도 `npm run check`가 초록»임을 재현했다(M4~M7).
    ⚠ 선언이 있는가만 본다 — 특이도와 화면에서 이기는지는 프리뷰 `page_toc`(대표이미지 없는 이전 글·관련 글)를 눈으로 본다.
    src만 본다(TIS001과 같은 이유).
    """
    hit = False
    if skin:
        body = re.sub(r"<!--.*?-->", "", skin, flags=re.S)
        tags = re.findall(r"<article\b[^>]*>", body)
        entry = [t for t in tags if re.search(r'\bclass="[^"]*\bentry\b[^"]*"', t)]
        if not entry:
            hit = True
            err("BND013", "skin.html에서 `<article class=\"entry\">`를 찾지 못했다 — 검사가 꺼진 것이지 통과가 아니다.",
                "src/skin.html")
        elif not any('data-cat="[##_article_rep_category_##]"' in t for t in entry):
            hit = True
            err("BND013", "`article.entry`에 `data-cat=\"[##_article_rep_category_##]\"`가 없다. 관련 글·이전/다음 상자가 "
                "이 글의 카테고리 삽화 대신 전부 기본 삽화로 떨어진다 (이슈 #161).", "src/skin.html")
    if src_css:
        css = strip_comments(src_css)
        norm = lambda sel: re.sub(r"\s+", " ", sel).strip()
        base = [(norm(sel), blk) for sel, blk in css_rules(strip_media(css))]
        every = [(norm(sel), blk) for sel, blk in css_rules(css)]
        miss = [t for t in PH_TARGETS
                if not any(sel == t and re.search(r"(?<![-\w])background-image\s*:\s*var\(\s*--ph-cat\b", blk)
                           for sel, blk in base)]
        short = sorted({sel for sel, blk in every
                        if any(sel == t or sel.endswith(" " + t) or sel.endswith(">" + t) for t in PH_TARGETS)
                        and re.search(r"(?<![-\w])background\s*:", blk)})
        guards = [g for g, pat in PH_GUARDS if not any(sel == g and re.search(pat, blk) for sel, blk in base)]
        parts = []
        if miss:
            parts.append("`background-image: var(--ph-cat…)`를 읽지 않는 자리: %s" % ", ".join(miss))
        if short:
            parts.append("`background` 단축형을 쓰는 규칙: %s — 삽화를 되돌리거나 WebP를 원본 크기로 깐다"
                         % ", ".join(short[:4]))
        if guards:
            parts.append("대표이미지가 있으면 삽화를 끄는 `:has()` 가드가 없다: %s — 로딩 중 삽화가 비쳤다가 "
                         "사진으로 바뀐다(결정 57 ②)" % ", ".join(guards))
        if parts:
            hit = True
            err("BND013", "%s (이슈 #161, DESIGN §6.2)." % ". ".join(parts), "src/styles/components.css")
    if not hit and skin and src_css:
        info("카테고리 삽화: article.entry data-cat · 세 자리 var(--ph-cat) · 단축형 없음 · :has 가드 셋")

# ─────────────────────────── 5e. 네이버 텍스트 광고 카드 (TIS006) ───────────────────────────

NAVERAD = '[data-tistory-react-app="NaverAd"]'


def hex_rgb(v):
    """`#rgb`·`#rrggbb` 리터럴만 읽는다. 그 밖(`var()`·이름·rgb())은 None — 판정 불가로 돌려준다."""
    m = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", v.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def contrast(a, b):
    """WCAG 2 대비비."""
    def lum(rgb):
        out = []
        for c in rgb:
            c = c / 255
            out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# 광고 카드에 박혀 오는 인라인 글자색 중 **읽어야 하는** 셋 — 주소 줄 #999는 흰 면 위에서도 2.85인 설계값이라 뺀다.
NAVERAD_INKS = {"설명 #333": (0x33, 0x33, 0x33), "배지 #666": (0x66, 0x66, 0x66), "제목 #016dd7": (0x01, 0x6d, 0xd7)}


def lint_naverad_surface(src_css):
    """네이버 텍스트 광고 카드에 **어느 테마에서든 밝은** 토큰 바탕이 있는가 — TIS006 (결정 72, 이슈 #159).

    티스토리가 글 본문 안(인벤토리 `<ins>` 바로 뒤 — 본문 래퍼 앞 또는 공감 버튼 앞)에
    `<div data-tistory-react-app="NaverAd">`를 두고 React가 광고 카드를 채울 때가 있다. 색은 전부 **인라인**(설명 `#333`·
    배지 `#666`·제목 `#016dd7`)이고 카드에 바탕이 없어, 다크 캔버스가 비치면 설명 줄이 1.57:1로 묻혔다.
    우리는 광고 색을 건드리지 않고 카드에 바탕만 돌려준다.

    TIS001(시트 리터럴 ↔ 덮어쓰기 선택자 짝)로는 못 본다 — 이 색은 시트가 아니라 광고 서버가 정하는 인라인 값이다.
    그래서 넷을 본다:
      ① **기본 규칙**(`@media` 밖, 테마 도장 `[data-theme…]` 없이)이 카드(`그릇 > div`)에 `background(-color): var(--토큰)`을
         선언한다 — 인쇄·좁은 폭 질의 안으로 옮기거나 한 테마에만 걸면 다른 쪽에서 바탕이 사라진다
      ② 그 토큰의 **모든 정의**(라이트 `:root`·다크 두 블록)가 hex이고, 그 위에서 설명 `#333`·배지 `#666`·제목 `#016dd7`이
         각각 4.5:1 이상이다 — 다크 블록에서 어둡게 재정의하거나 중간 회색으로 바꾸면 빨간불이다
      ③ 인쇄 전용 블록(`print`·`only print`로 시작하는 질의 — `not print`는 화면이라 본다) 밖에서 그릇 안을 겨누는 규칙이 바탕을
         **그 토큰 말고 다른 값**(`transparent`·`none`·다른 토큰)으로 선언하지 않는다
      ④ **마지막 복합 선택자가 그릇인 규칙**(`그릇`·`그릇:empty`·`그릇::before`·`그릇:not(…)`)에는 `display` 말고 아무 선언도 없다 —
         빈 그릇은 모든 글에 있고(서버 HTML 6/6) 높이 0이어야 한다. 면·여백·그림자·크기·가상 요소 어느 것이든 글 위에 띠를 만든다
    ⚠ **못 보는 것** — 그릇 이름을 쓰지 않는 범용 선택자(`.entry-body div { background: transparent }` 같은 것)가 카드를 덮는 경로,
      그리고 특이도. 인라인 style에 background가 없어 지금은 싸움이 없다(2026-10-11 실측)는 것까지가 근거다. 화면은 프리뷰
      `page`(카드 앞)·`page_toc`(카드 뒤)·`page_bare`(빈 그릇)를 눈으로 본다. 2026-10-11 체크포인트·코드 리뷰가 낸 우회 중
      위 넷으로 표현되는 것은 막았고, 범용 선택자 경로는 막지 못했다.
    """
    if not src_css:
        return
    body = strip_comments(src_css)
    card_sel = r"%s\s*>\s*div$" % re.escape(NAVERAD)
    bg = r"(?<![-\w])background(?:-color)?\s*:\s*([^;}]+)"
    problems = []
    tokens = set()
    for sel, blk in css_rules(strip_media(body)):
        if re.search(card_sel, sel) and "[data-theme" not in sel:
            for m in re.finditer(bg, blk):
                t = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", m.group(1).strip())
                if t:
                    tokens.add(t.group(1))
    if not tokens:
        problems.append("기본 규칙(`@media` 밖, 테마 도장 없이)이 광고 카드(`%s > div`)에 토큰 바탕 "
                        "`background-color: var(--…)`을 선언하지 않는다" % NAVERAD)
    for tok in sorted(tokens):
        vals = [m.group(1).strip() for m in re.finditer(r"(?<![-\w])%s\s*:\s*([^;}]+)" % re.escape(tok), body)]
        if not vals:
            problems.append("`%s` 정의가 없다(선언 전체가 무효가 되어 바탕이 투명으로 돌아간다)" % tok)
        for v in vals:
            rgb = hex_rgb(v)
            if rgb is None:
                problems.append("`%s: %s`를 판정할 수 없다 — hex 리터럴만 잰다" % (tok, v))
                continue
            low = ["%s %.2f" % (name, contrast(rgb, ink)) for name, ink in NAVERAD_INKS.items() if contrast(rgb, ink) < 4.5]
            if low:
                problems.append("`%s: %s` 위에서 %s:1" % (tok, v, " · ".join(low)))
    def print_only(q):
        n = re.sub(r"\s+", "", q.lower())
        return n.startswith("print") or n.startswith("onlyprint")
    undo = set()
    for sel, blk in css_rules(strip_media(body, only=print_only)):
        if NAVERAD not in sel or sel.rstrip().endswith(NAVERAD):
            continue
        for m in re.finditer(bg, blk):
            t = re.fullmatch(r"var\(\s*(--[\w-]+)\s*\)", m.group(1).strip())
            if not (t and t.group(1) in tokens):
                undo.add("%s (%s)" % (sel, m.group(1).strip()))
    if undo:
        problems.append("그릇 안 바탕을 되돌리는 규칙: %s" % ", ".join(sorted(undo)[:4]))
    box = set()
    for sel, blk in css_rules(body):
        last = re.split(r"\s*[>+~]\s*|\s+", sel.strip())[-1]
        if NAVERAD in last:
            for m in re.finditer(r"(?<![-\w])([a-z-]+)\s*:", blk):
                if m.group(1) != "display":
                    box.add("%s (%s)" % (sel, m.group(1)))
    if box:
        problems.append("그릇 자체에 `display` 말고 선언이 있다: %s — 빈 그릇이 모든 글 위에 띠로 뜬다"
                        % ", ".join(sorted(box)[:4]))
    if problems:
        err("TIS006", "네이버 텍스트 광고 카드: %s. 광고 색은 전부 인라인이라, 바탕이 없거나 어두우면 다크에서 "
            "설명 줄이 묻힌다(1.57:1 실측). 광고 색은 건드리지 않고 테마 공통 밝은 면만 카드에 준다 (결정 72)."
            % "; ".join(problems), "src/styles/tistory.css")
    else:
        info("네이버 텍스트 광고 카드: 토큰 %s — 모든 정의 위 #333·#666·#016dd7 4.5:1 이상, 되돌리는 규칙 없음, 빈 그릇은 선언 없음"
             % ", ".join(sorted(tokens)))


# ─────────────────────────── 5f. 인쇄에서 본문 안 광고 (TIS007) ───────────────────────────

# (인쇄 블록에서 지울 선택자, 인라인 display를 이겨야 하는가, 되살리는 규칙을 찾을 패턴 — 마지막 복합 선택자에 대고 잰다).
# 이름은 티스토리·구글 마크업이다(라이브 서버 HTML 2026-10-11). 패턴은 같은 그릇을 다르게 쓰는 모양까지 받는다 —
# 따옴표 없는·홑따옴표 속성값, 클래스 없이 태그만 쓴 `ins`(코드 리뷰 2026-10-11).
PRINT_ADS = (
    ('[data-tistory-react-app="NaverAd"]', False, r"\[\s*data-tistory-react-app\s*=\s*(['\"]?)NaverAd\1\s*\]"),
    (".revenue_unit_wrap", False, r"\.revenue_unit_wrap(?![\w-])"),
    ("ins.adsbygoogle", True, r"^ins(?![\w-])|\.adsbygoogle(?![\w-])"),
)


def top_media_blocks(css):
    """**맨 위 단계**의 `@media` 블록만 [(질의, 본문)] — `@media (min-width:99999px) { @media print { … } }`나
    `@supports (…) { @media print { … } }`처럼 다른 조건 안에 든 블록은 그 조건이 참일 때만 걸리므로 빼고 센다."""
    out, depth, i = [], 0, 0
    while i < len(css):
        c = css[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0 and css.startswith("@media", i):
            k = css.find("{", i)
            if k == -1:
                break
            d, j = 1, k + 1
            while j < len(css) and d:
                d += {"{": 1, "}": -1}.get(css[j], 0)
                j += 1
            out.append((css[i + 6:k].strip(), css[k + 1:j - 1]))
            i = j
            continue
        i += 1
    return out


def lint_print_ads(src_css):
    """인쇄에서 글 본문 안 광고 셋이 지워지는가 — TIS007 (결정 73, 이슈 #172).

    인쇄 블록은 우리 `.ad` 그릇만 지우고, 티스토리가 `.entry-body`에 직접 넣는 광고는 종이에 찍혔다(라이브 print 에뮬레이션
    2026-10-11: `.revenue_unit_wrap` 280·99·280px, NaverAd 카드 291px). 셋 다 티스토리 마크업이라 우리 마크업 린트(BND)도,
    화면 프리뷰도 못 본다 — 인쇄 블록의 선택자 목록이 유일한 근거다.

    둘을 본다:
      ① **맨 위 단계의 조건 없는 인쇄 블록**(`@media print`·`only print` — `print and (…)`, 다른 `@media`·`@supports` 안에 든 블록은
         모든 종이에 걸린다는 보장이 없어 받지 않는다) 안에서 각 선택자가 정확히 그 이름으로, 같은 블록의 **마지막** `display`가
         `none`이다. 인벤토리 애드센스 `ins.adsbygoogle`는 그릇 없이 인라인 `display:block`으로 오므로 `!important`까지
      ② 화면 전용 블록(쉼표로 나눈 질의 **전부**가 `screen`·`only screen`·`not print`로 시작 — `screen, print`는 종이에도 걸린다) 밖에서
         그 그릇을 겨누는(마지막 복합 선택자가 `PRINT_ADS`의 패턴에 맞는) 규칙이 `display`를 `none` 말고 다른 값으로 선언하지 않는다
    ⚠ **못 보는 것** — 라이브에서 그릇 이름이 바뀌는 것, 애드센스가 광고를 채우며 인라인을 `display:block !important`로 다시 쓰는 것
      (그러면 인라인이 이긴다 — 라이브 광고 페이지를 헤드리스로 여는 측정은 무효 트래픽 위험이라 하지 않았다, 이슈 #176),
      패턴에 안 걸리는 범용 선택자(`.entry-body > *` 같은 것)의 되살리기, 특이도.
    """
    if not src_css:
        return
    body = strip_comments(src_css)
    norm = lambda q: re.sub(r"\s+", "", q.lower())
    print_rules = [(re.sub(r"\s+", " ", sel), blk) for q, mbody in top_media_blocks(body) if norm(q) in ("print", "onlyprint")
                   for sel, blk in css_rules(mbody)]
    DISPLAY = r"(?<![-\w])display\s*:\s*([^;}]+)"
    miss, weak = [], []
    for needle, need_imp, _ in PRINT_ADS:
        hides = []
        for sel, blk in print_rules:
            if sel != needle:
                continue
            decls = re.findall(DISPLAY, blk)
            if decls and re.match(r"none\b", decls[-1].strip()):
                hides.append(decls[-1])
        if not hides:
            miss.append(needle)
        elif need_imp and not any(re.search(r"!\s*important", d) for d in hides):
            weak.append(needle)
    screen_only = lambda q: all(norm(part).startswith(("screen", "onlyscreen", "notprint")) for part in q.split(","))
    paper = strip_media(body, only=screen_only)
    undo = set()
    for sel, blk in css_rules(paper):
        last = re.split(r"\s*[>+~]\s*|\s+", sel.strip())[-1]
        if any(re.search(pat, last) for _, _, pat in PRINT_ADS):
            for d in re.findall(DISPLAY, blk):
                if not re.match(r"none\b", d.strip()):
                    undo.add("%s (display: %s)" % (sel, d.strip()))
    if miss:
        err("TIS007", "맨 위 단계의 조건 없는 인쇄 블록이 본문 안 광고를 지우지 않는다(마지막 `display`가 `none`인 규칙이 없다): %s. "
            "티스토리가 `.entry-body`에 직접 넣는 광고라 우리 `.ad` 규칙이 닿지 않고, 종이에 280px 안팎으로 찍힌다 (결정 73)."
            % ", ".join(miss), "src/styles/components.css")
    if weak:
        err("TIS007", "%s는 인쇄 블록에서 `display: none`인데 `!important`가 없다 — 인라인 `display:block`으로 오는 그릇이라 "
            "시트의 보통 선언은 특이도와 무관하게 진다. 규칙이 있는데 종이에 그대로 찍힌다 (결정 73)." % ", ".join(weak),
            "src/styles/components.css")
    if undo:
        err("TIS007", "종이에도 걸리는 곳에서 광고 그릇을 되살리는 규칙: %s — 인쇄 블록의 `display: none`을 뒤에서 덮는다 (결정 73)."
            % ", ".join(sorted(undo)[:4]), "src/styles/components.css")
    if not miss and not weak and not undo:
        info("인쇄 본문 광고: NaverAd 그릇 · .revenue_unit_wrap · ins.adsbygoogle(!important) 모두 인쇄에서 지움, 되살리는 규칙 없음")


# ─────────────────────────── 5g. 카테고리 토글 자리 (TIS008) ───────────────────────────

def lint_cat_toggle_reserve(src_css):
    """카테고리 레일의 토글 자리를 첫 페인트부터 비우고, 그 폭을 토글 상자와 **같은 토큰**으로 쓰는가 — TIS008 (결정 74, 이슈 #169).

    `category.js`가 상위 줄에 접기 버튼(`.cat-toggle`, 24px + 왼쪽 여백 4px)을 달고, 토글 없는 줄에는 `.cat-tree`로 같은
    28px를 비운다 — 둘 다 JS가 붙이는 클래스라 첫 페인트에는 없어, 1025px 이상 모든 페이지에서 글 수 배지가 JS 뒤 28px 왼쪽으로
    움직였다(프리뷰 실측 240.3 → 212.3). 결정 62의 방식대로 `html.js`일 때 CSS가 그 자리를 미리 비운다.

    «예약 = 실물»을 정적으로 볼 수 있는 자리를 본다:
      ① 토큰 사슬 — `--cat-toggle-reserve`가 `var(--cat-toggle-size)`와 `var(--cat-toggle-gap)`에서 나온다
      ② `.cat-toggle`의 width·height가 `var(--cat-toggle-size)`, margin-left가 `var(--cat-toggle-gap)` — 상자와 식의 항이 같은 이름이다
         (margin-left만 바꾸면 JS 뒤 4px 움직였다 — 체크포인트 변이 실측)
      ③ **`@media` 밖**의 `.js`로 시작하는 미리 비우기 둘 — 토글이 올 줄 `> a`의 `margin-right: calc(reserve − pill)`(목록이
         `:not(.cat-tree)`일 때만 — 빠지면 JS 뒤에도 예약이 남아 토글 줄 배지가 28px 더 들어간다), 토글이 안 올 줄 `> a`의
         `padding-right: calc(reserve + pill)` — 알약 보정 `var(--cat-pill-x…)`가 빠지면 현재 줄에서 8px 움직였다
      ④ JS 이후의 `.cat-tree > li:not(.has-toggle) > a`도 `padding-right`에 reserve와 pill을 쓴다
    그리고 카테고리 규칙(`.side-category`·`.tt_category`·`.cat-tree`·`.cat-toggle`)의 padding·margin에 손으로 적은 `28px`가 남지
    않았는지. 미리 비우기는 `.js`·`html.js`·`:root.js` 어느 접두로 써도 받고, 규칙이 여럿이면 **전부**가 조건을 지켜야 한다 —
    맞는 규칙 하나가 틀린 규칙을 가리지 않게(코드 리뷰). 결정 62 — «손으로 맞춘 두 숫자는 갈라진다».
    ⚠ **못 보는 것** — 선택자 구조가 실제 트리를 잡는지(구조를 바꿔 아무것도 못 잡게 해도 선언은 남는다), 첫 페인트와 JS 뒤의 위치가
      실제로 같은지(기하 — 브라우저 검사 단계는 미뤄 둔 상태).
    """
    if not src_css:
        return
    body = strip_comments(src_css)
    rules = css_rules(body)
    R = r"var\(\s*--cat-toggle-reserve\s*\)"
    PILL = r"var\(\s*--cat-pill-x"
    problems = []
    defs = re.findall(r"(?<![-\w])--cat-toggle-reserve\s*:\s*([^;}]+)", body)
    if not re.search(r"(?<![-\w])--cat-toggle-size\s*:", body) or not re.search(r"(?<![-\w])--cat-toggle-gap\s*:", body) or not defs:
        problems.append("토큰 `--cat-toggle-size`·`--cat-toggle-gap`·`--cat-toggle-reserve` 정의가 없다")
    elif not all(re.fullmatch(r"calc\(\s*var\(\s*--cat-toggle-size\s*\)\s*\+\s*var\(\s*--cat-toggle-gap\s*\)\s*\)", d.strip())
                 for d in defs):
        problems.append("`--cat-toggle-reserve`가 정확히 `calc(var(--cat-toggle-size) + var(--cat-toggle-gap))`가 아니다(%s)" % defs[0].strip())
    toggle = [blk for sel, blk in rules if sel.strip() == ".cat-toggle"]
    want = (("width", "--cat-toggle-size"), ("height", "--cat-toggle-size"), ("margin-left", "--cat-toggle-gap"))
    bad = [p for p, tok in want
           if not any(re.search(r"(?<![-\w])%s\s*:\s*var\(\s*%s\s*\)" % (p, tok), b) for b in toggle)]
    if not toggle or bad:
        problems.append("`.cat-toggle`의 %s가 토큰이 아니다(width·height `--cat-toggle-size`, margin-left `--cat-toggle-gap`)"
                        % ("·".join(bad) or "규칙"))
    pre = [(sel.strip(), blk) for sel, blk in css_rules(strip_media(body))
           if re.match(r"(?:html|:root)?\.js\s", sel.strip()) and ".side-category" in sel and sel.strip().endswith("> a")]
    m_rules = [(sel, b) for sel, b in pre if re.search(r"(?<![-\w])margin-right\s*:[^;}]*" + R, b)]
    p_rules = [(sel, b) for sel, b in pre if re.search(r"(?<![-\w])padding-right\s*:[^;}]*" + R, b)]
    if not m_rules:
        problems.append("`@media` 밖에 토글이 올 줄을 미리 비우는 `.js …> a { margin-right: …var(--cat-toggle-reserve)… }`가 없다")
    else:
        if not all(":not(.cat-tree)" in sel and "li:has(> ul) > a" in re.sub(r"\s+", " ", sel) for sel, _ in m_rules):
            problems.append("토글이 올 줄의 미리 비우기가 «목록 `:not(.cat-tree)` · 하위를 가진 `li:has(> ul)`»로 좁혀지지 않았다 — "
                            "JS 뒤에도 예약이 남거나 토글이 안 올 줄까지 비운다")
        if not all(re.search(r"margin-right\s*:[^;}]*-\s*" + PILL, b) for _, b in m_rules):
            problems.append("토글이 올 줄의 미리 비우기에 알약 보정(`- var(--cat-pill-x…)`)이 없다")
    if not p_rules:
        problems.append("`@media` 밖에 토글이 안 올 줄을 미리 비우는 `.js …> a { padding-right: …var(--cat-toggle-reserve)… }`가 없다")
    else:
        if not all(re.search(r"padding-right\s*:[^;}]*\+\s*" + PILL, b) for _, b in p_rules):
            problems.append("토글이 안 올 줄의 미리 비우기에 알약 보정(`+ var(--cat-pill-x…)`)이 없다")
        if not all(":has(> li > ul)" in re.sub(r"\s+", " ", sel) and "li:not(:has(> ul)) > a" in re.sub(r"\s+", " ", sel)
                   for sel, _ in p_rules):
            problems.append("토글이 안 올 줄의 미리 비우기가 «하위를 가진 목록 `:has(> li > ul)` · 하위 없는 줄»로 좁혀지지 않았다 — "
                            "하위가 하나도 없는 블로그에서 토글 없이 28px가 영영 빈다")
    post = [blk for sel, blk in rules if re.search(r"\.cat-tree\s*>\s*li:not\(\.has-toggle\)\s*>\s*a$", sel.strip())]
    if not any(re.search(r"(?<![-\w])padding-right\s*:[^;}]*" + R + r"[^;}]*" + PILL, b) for b in post):
        problems.append("`.cat-tree > li:not(.has-toggle) > a`의 padding-right가 reserve + pill이 아니다")
    lit = sorted({sel.strip() for sel, blk in rules
                  if re.search(r"\.side-category|\.tt_category|\.cat-tree|\.cat-toggle", sel)
                  and re.search(r"(?<![-\w])(?:padding|margin)(?:-right)?\s*:[^;}]*(?<![\d.])28px", blk)})
    if lit:
        problems.append("카테고리 규칙에 손으로 적은 28px 예약이 남았다: %s" % ", ".join(lit[:3]))
    if problems:
        err("TIS008", "카테고리 토글 자리: %s. 첫 페인트와 category.js 뒤가 갈라져 글 수 배지가 옆으로 움직이거나, 상자 폭과 "
            "예약 폭이 따로 놀아 조용히 어긋난다 (결정 62·74, 이슈 #169)." % "; ".join(problems), "src/styles/tistory.css")
    else:
        info("카테고리 토글 자리: size+gap → reserve, .cat-toggle·미리 비우기 둘(:not(.cat-tree)·알약 보정)·.cat-tree 모두 같은 토큰")


# ─────────────────────────── 6. 접근성·안정성 ───────────────────────────

def lint_robustness(js, skin):
    if js:
        if "localStorage" in js and "catch" not in js:
            err("ROB001", "localStorage를 try/catch 없이 쓴다. 시크릿 모드·사이트데이터 차단 환경에서 "
                "예외가 나 스크립트 전체가 죽는다.", "src/js/")
        if "MutationObserver" not in js and "comment" in js.lower():
            warn("ROB002", "댓글 영역을 조작하는 것 같은데 MutationObserver가 없다. "
                 "댓글은 React가 나중에 렌더링하므로 초기 쿼리로는 잡히지 않는다.", "src/js/")
        if "prefers-reduced-motion" not in js and "scroll" in js.lower():
            info("prefers-reduced-motion 처리를 JS에서 찾지 못했다. CSS에 있다면 무시해도 된다.")
    if skin:
        if "<html" in skin and not re.search(r'<html[^>]*\blang=', skin):
            warn("A11Y001", "<html>에 lang 속성이 없다. 스크린리더가 언어를 판단하지 못한다.",
                 "src/skin.html")
        if 'name="viewport"' not in skin:
            err("A11Y002", "viewport 메타 태그가 없다. 반응형이 동작하지 않는다.", "src/skin.html")


# ────────────────────── 7. SEO — 크롤러에게 보이는 것 ──────────────────────

# 한 페이지에 여러 번 렌더되는 블록. 여기 h1이 들어가면 h1이 항목 수만큼 생긴다.
# data/substitutions.json의 그룹 62종 중 "_rep"·"_item" 계열을 훑어 추린 것이다.
REPEATING_BLOCKS = [
    "s_index_article_rep", "s_list_rep", "s_article_related_rep",
    "s_rctps_rep", "s_rctps_popular_rep", "s_notice_rep", "s_rct_notice_rep",
    "s_cover_item", "s_cover_rep", "s_paging_rep", "s_page_rep",
    "s_tag_rep", "s_rp_rep", "s_rp2_rep", "s_rctrp_rep",
    "s_guest_rep", "s_guest_reply_rep",
    "s_sidebar_element",   # 사이드바 모듈마다 한 번씩 — 이름에 _rep이 없어 놓치기 쉽다
]

# <s_article_rep>은 문맥에 따라 갈린다. <s_index_article_rep> 안에서는 글 수만큼
# 반복되지만, <s_permalink_article_rep> 안에서는 딱 한 번 렌더된다 — 거기서는
# h1이 오히려 정답이다. 그래서 위 목록에 넣지 않고 따로 판정한다.
CONTEXTUAL_SINGLE = "s_permalink_article_rep"

# 글 페이지의 내부링크를 만드는 치환자. 셋 다 없으면 글끼리 링크가 0이 된다.
INTERNAL_LINK_GROUPS = ["s_article_related", "s_article_prev", "s_article_next"]


def lint_seo(skin):
    """화면은 멀쩡한데 유입만 사라지는 결함. skin-qa-check가 보는 것 중
    유일하게 '보기에 맞는가'로는 절대 드러나지 않는 부류다."""
    if not skin:
        return
    # 주석 안의 <h1>·<img>는 렌더되지 않는다. 그걸 오류로 잡으면 아무것도
    # 출력하지 않는 마크업이 배포를 막는다. 줄 번호를 보존하려고 지우지 않고
    # 같은 길이의 공백으로 덮는다.
    skin = re.sub(r"<!--.*?-->",
                  lambda m: re.sub(r"[^\n]", " ", m.group(0)), skin, flags=re.S)

    # SEO001 — 반복 블록 안의 h1
    repeating_spans = []
    for tag in REPEATING_BLOCKS:
        for m in re.finditer(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (tag, tag), skin, re.S | re.I):
            repeating_spans.append((m.start(), m.end()))
            if re.search(r"<h1[\s>]", m.group(1), re.I):
                line = skin[:m.start()].count("\n") + 1
                err("SEO001", "<%s>는 한 페이지에서 반복 렌더되는 블록인데 그 안에 <h1>이 있다. "
                    "h1이 항목 수만큼 생긴다. h2 이하로 내려라." % tag,
                    "src/skin.html:%d" % line)

    # SEO001 — <s_article_rep>은 문맥에 따라 갈린다.
    #
    # 두 배치가 다 쓰인다:
    #   <s_article_rep><s_permalink_article_rep><h1>…  (글 템플릿 하나에 페이지별 분기)
    #   <s_permalink_article_rep><s_article_rep><h1>…  (페이지 영역 안에 글 템플릿)
    # 그래서 "블록이 글 상세 안에 있는가"로 물으면 첫 배치의 올바른 h1이 오류가 된다.
    # 물어야 할 것은 h1 **자신**이 글 상세 영역 안에 있는가다.
    single_spans = [(m.start(), m.end()) for m in re.finditer(
        r"<%s(?:\s[^>]*)?>.*?</%s>" % (CONTEXTUAL_SINGLE, CONTEXTUAL_SINGLE),
        skin, re.S | re.I)]
    for m in re.finditer(r"<s_article_rep(?:\s[^>]*)?>(.*?)</s_article_rep>", skin, re.S | re.I):
        body_start = m.start(1)
        for h in re.finditer(r"<h1[\s>]", m.group(1), re.I):
            at = body_start + h.start()
            if any(a <= at < b for a, b in single_spans):
                continue   # 글 상세 영역 안의 h1 — 한 번만 렌더되므로 맞다
            if any(a <= at < b for a, b in repeating_spans):
                continue   # 위 루프가 이미 신고한 h1이다. 같은 결함을 두 번 적지 않는다
            line = skin[:at].count("\n") + 1
            err("SEO001", "<s_article_rep> 안의 <h1>이 <%s> 영역 밖에 있다. 홈·목록에서는 "
                "이 블록이 글 수만큼 반복되므로 h1도 그만큼 생긴다. 글 상세에서만 h1을 쓰려면 "
                "<%s> 안으로 넣어라." % (CONTEXTUAL_SINGLE, CONTEXTUAL_SINGLE),
                "src/skin.html:%d" % line)

    # SEO002 — 내부링크 치환자
    present = [g for g in INTERNAL_LINK_GROUPS if re.search(r"<%s[\s>]" % g, skin, re.I)]
    if not present:
        err("SEO002", "관련글·이전글·다음글 치환자(%s)가 하나도 없다. 글에서 글로 가는 "
            "내부링크가 0이 되고, 모든 글이 고아 페이지가 된다. 내부링크는 스킨이 쥔 "
            "가장 큰 SEO 레버다 (DECISIONS.md 결정 28)."
            % ", ".join("<%s>" % g for g in INTERNAL_LINK_GROUPS), "src/skin.html")
    elif len(present) < len(INTERNAL_LINK_GROUPS):
        missing = [g for g in INTERNAL_LINK_GROUPS if g not in present]
        warn("SEO002", "내부링크 치환자 중 %s 가 없다. 글끼리 연결이 그만큼 얇아진다."
             % ", ".join("<%s>" % g for g in missing), "src/skin.html")

    # SEO003 — <title>
    m = re.search(r"<title>(.*?)</title>", skin, re.S | re.I)
    if not m:
        err("SEO003", "<title>이 없다.", "src/skin.html")
    else:
        t = m.group(1)
        if "[##_page_title_##]" not in t:
            warn("SEO003", "<title>이 [##_page_title_##]을 쓰지 않는다. 모든 페이지의 제목이 "
                 "같아지면 카테고리·태그·검색 페이지가 서로 구분되지 않는다.", "src/skin.html")
        elif "[##_title_##]" in t:
            # 티스토리의 page_title은 홈에서 블로그 제목 그 자체다. 뒤에 [##_title_##]을
            # 또 붙이면 홈 제목이 "상쾌한기분 — 상쾌한기분"이 된다 (2026-08-25 라이브 실측).
            warn("SEO003", "<title>에 [##_page_title_##]과 [##_title_##]이 같이 있다. "
                 "홈에서는 page_title이 이미 블로그 제목이라 '블로그명 — 블로그명'이 된다. "
                 "현재 라이브가 정확히 이 상태다. page_title 하나만 쓰거나, "
                 "홈만 <s_if_...>로 분기하라.", "src/skin.html")

    # SEO004 — img alt
    noalt = [i for i in re.findall(r"<img[^>]*>", skin, re.I)
             if not re.search(r"\balt\s*=", i, re.I)]
    if noalt:
        warn("SEO004", "스킨이 출력하는 <img> %d개에 alt가 없다. 썸네일이면 "
             'alt="[##_..._title_##]" 처럼 제목을 넣는다.' % len(noalt), "src/skin.html")

    # SEO005 — BreadcrumbList
    if "BreadcrumbList" not in skin:
        info("SEO005 — BreadcrumbList JSON-LD가 없다. 티스토리는 글 페이지에 BlogPosting만 "
             "주입하고 빵부스러기는 카테고리 페이지에만 넣는다. 글 페이지 빵부스러기는 "
             "스킨이 채울 수 있는 자리다 (DECISIONS.md 결정 28). 필수는 아니다.")


# ─────────────────────────────── main ───────────────────────────────

# ─────────────────────────── 문서 인용 (DOC001) ───────────────────────────

# `파일:줄` 인용. 확장자 뒤에 `:숫자`(선택적으로 `-숫자`·`~숫자` 범위). 경로는 단어 문자나 `.`로
# 시작해야 하고 그 앞이 `/`·`.`·`:`·단어 문자면 안 된다 — URL 안(`https://cdn…/x.js:1`)은 모든
# 위치가 그 조건에 걸려 매칭되지 않는다. 첫 판은 `:` 뒤의 `//cdn…`에서 시작해 URL을 잡았다(테스트가 잡았다).
LINE_REF = re.compile(r"(?<![\w/.:-])([\w.][\w./-]*\.(?:js|mjs|css|html|py|xml|json|md|txt)):(\d+)(?:[-~]\d+)?\b")
DOC_SKIP_DIRS = {"node_modules", ".git", "dist", "_preview", "backup"}


def lint_doc_line_refs(root):
    """문서의 `파일:줄번호` 인용을 막는다 (결정 54).

    줄번호는 그 위에 한 줄만 들어가도 조용히 다른 줄을 가리킨다 — 2026-08-26 한 세션에서
    5건, 2026-08-27 전체 대조에서 20건 중 1건이 이미 썩어 있었고, 그중 둘은 쓴 PR에서
    리뷰가 놓쳤다. 심볼 인용(`` `code.js`의 `LANGS` ``)은 줄이 밀려도 안 썩는다.
    심볼의 존재까지는 검사하지 않는다 — 이름을 바꾸면 저장소 전체를 훑는 규범이 이미 있다."""
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in DOC_SKIP_DIRS and not d.startswith("_workspace"))
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root)
            for i, line in enumerate(read(path).split("\n"), 1):
                for m in LINE_REF.finditer(line):
                    err("DOC001",
                        "문서가 `%s:%s`처럼 줄번호로 인용한다 — 위에 한 줄만 들어가도 다른 줄을 가리키는데 "
                        "화면에 신호가 없다. `` `%s`의 `심볼` `` 형태로 쓴다 (결정 54)"
                        % (m.group(1), m.group(2), os.path.basename(m.group(1))),
                        "%s %d행" % (rel, i))



# 결정 번호 참조 — `결정 36-b`의 36은 잡고, `사용자 결정 2026-10-08` 같은 날짜는 안 잡는다. 여러 번호를 한 번에 쓴
# `결정 5·6`·`결정 53·68`·`결정 63~68`(범위는 양 끝)도 번호마다 본다 — 첫 번호만 보면 둘째 이후가 빠진다(코드 리뷰).
DECISION_REF = re.compile(r"결정\s*(\d{1,3}(?:\s*[·,~]\s*\d{1,3})*)(?!\d|-\d)")
# 참조를 찾는 파일 — 문서와 코드 주석이 결정을 가리킨다.
DECISION_REF_EXT = (".md", ".css", ".js", ".mjs", ".py", ".html", ".xml", ".json", ".txt")
# `posts/`는 블로그 원고, `worktrees`는 Claude Code가 `.claude/worktrees/`에 두는 **다른 브랜치의** 체크아웃이다 —
# 거기서 먼저 적은 결정이 이 체크아웃엔 없어 로컬에서만 빨개진다(CI엔 그 폴더가 없다).
DECISION_REF_SKIP_DIRS = DOC_SKIP_DIRS | {"posts", "worktrees"}
# blog-census가 크롤로 쓰는 파일 — 글 제목·카테고리 이름 같은 산문이라 「결정」이 섞일 수 있다.
DECISION_REF_SKIP_FILES = {os.path.join("data", "posts.json"), os.path.join("data", "categories.json")}


def defined_decisions(text):
    """`DECISIONS.md`가 **정의한** 결정 번호 — §1(`## 2.` 앞)만 본다.

    정의 형식이 둘이다 — 결정 표의 행(머리 첫 칸이 `#`인 표의 첫 칸, 결정 1~38·46·47)과 굵은 머리 `**결정 N — …`
    (결정 36·39 이후). 머리 첫 칸이 `#`가 아닌 표(같은 절의 폭 실측 `| 1240 | 24 | …`)는 결정이 아니다. §1 밖의 굵은 머리
    (§4 미결의 후보 같은 것)는 정해지지 않은 것이라 세지 않는다.
    """
    head = text.split("\n## 2.", 1)[0]
    found, table = set(), None   # table: None = 표 밖, True/False = 결정 표인가
    for line in head.split("\n"):
        if not line.startswith("|"):
            table = None
            continue
        first = line.strip().strip("|").split("|")[0].strip()
        if table is None:
            table = first == "#"   # 머리 행에서 이 표가 결정 표인지 정한다
        elif table and re.fullmatch(r"\d+", first):
            found.add(int(first))
    found |= {int(n) for n in re.findall(r"^\*\*결정 (\d+) —", head, re.M)}
    return found


def decision_numbers(ref):
    """`5·6` → [5, 6], `63~68` → [63, 68](범위는 양 끝만 — 사이의 걷은 번호 23·24가 범위 안에 있어도 탓하지 않는다)."""
    return [int(n) for n in re.findall(r"\d+", ref)]


def lint_decision_refs(root):
    """소스·문서가 가리키는 `결정 N`이 `DECISIONS.md`에 정의돼 있는가 — DOC002 (이슈 #166).

    2026-10-11 `code-wrap-related-clamp` 체크포인트에서 `content.css` 주석과 `DESIGN.md` 세 곳이 「결정 71」을 가리키는데
    `DECISIONS.md`는 결정 70에서 끝나 있었고, `npm run check`는 19단계 모두 초록이었다. 결정 번호는 여러 브랜치가 동시에
    붙이면 겹치고(CLAUDE.md 「번호로 식별하는 목록」), 결정을 적기 전에 코드가 먼저 그 번호를 가리키는 부류도 생긴다 —
    둘 다 «없는 결정을 가리키는» 같은 모양으로 드러난다.

    ⚠ **번호가 있는가**만 본다. 그 결정이 그 문장의 내용과 맞는지(엉뚱한 번호를 가리키는지)는 모른다.
      걷어 낸 번호(23·24 — 재사용하지 않는다)를 가리키면 그것도 잡힌다 — 걷은 결정을 아직 근거로 대는 문장이다.
      UTF-8이 아닌 파일은 깨진 글자를 버리고 읽는다 — 한 파일 때문에 린트 전체가 죽지 않게.
    """
    dec = read(os.path.join(root, "DECISIONS.md"))
    if not dec:
        return
    defined = defined_decisions(dec)
    if not defined:
        err("DOC002", "`DECISIONS.md` §1에서 정의된 결정을 하나도 못 찾았다 — 정의 형식(머리 첫 칸이 `#`인 결정 표·"
            "`**결정 N —`)이 바뀌었으면 이 검사도 같이 옮긴다.", "DECISIONS.md")
        return
    bad = {}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in DECISION_REF_SKIP_DIRS and not d.startswith("_workspace"))
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root)
            if not f.endswith(DECISION_REF_EXT) or rel in DECISION_REF_SKIP_FILES:
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for i, line in enumerate(text.split("\n"), 1):
                for m in DECISION_REF.finditer(line):
                    for n in decision_numbers(m.group(1)):
                        if n not in defined:
                            bad.setdefault(n, []).append("%s %d행" % (rel, i))
    for n in sorted(bad):
        err("DOC002", "「결정 %d」을 가리키는데 `DECISIONS.md`에 그 결정이 없다(정의된 최대 %d) — 결정을 먼저 적거나 참조를 "
            "고친다. 동시 작업이 같은 번호를 집었을 수도 있다: %s%s"
            % (n, max(defined), ", ".join(bad[n][:4]), " 외 %d곳" % (len(bad[n]) - 4) if len(bad[n]) > 4 else ""),
            bad[n][0])


def emit_and_exit(as_json):
    """결과를 내고 끝낸다 — 스킨이 없어 문서 규칙만 돈 경로와 전체 경로가 같은 형식을 쓴다."""
    if as_json:
        print(json.dumps({"errors": ERRORS, "warnings": WARNINGS, "info": INFO},
                         ensure_ascii=False, indent=1))
    else:
        for it in ERRORS:
            print("❌ [%s] %s\n     %s" % (it["code"], it["message"], it["where"]))
        for it in WARNINGS:
            print("⚠️  [%s] %s\n     %s" % (it["code"], it["message"], it["where"]))
        for m in INFO:
            print("ℹ️  %s" % m)
        print("\n오류 %d · 경고 %d" % (len(ERRORS), len(WARNINGS)))
    sys.exit(1 if ERRORS else 0)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    skin = read(os.path.join(SRC, "skin.html"))
    xml = read(os.path.join(SRC, "index.xml"))
    if skin is None:
        # 검사할 대상이 없는 것은 실패가 아니다. 구현 전에도 npm run check가 통과해야
        # 문서·인프라 변경을 커밋할 수 있다. 다만 문서 규칙(DOC001·DOC002)은 스킨이 없어도 돈다 —
        # 전에는 여기서 바로 빠져나가 「skin.html이 없어도 돈다」던 SKILL.md 문장이 거짓이었다.
        lint_doc_line_refs(ROOT)
        lint_decision_refs(ROOT)
        info("src/skin.html이 없어 스킨 규칙은 건너뛰었다(문서 규칙만 돌았다). 아직 구현 전이면 정상이다.")
        emit_and_exit(args.json)

    # src/styles와 dist/style.css를 모두 읽는다.
    # 인라인 스타일 보정 규칙은 빌드가 data/inline-styles.json에서 생성해
    # dist에만 존재하므로, src만 보면 INL001이 오탐한다.
    css_dir = os.path.join(SRC, "styles")
    src_css = ""
    if os.path.isdir(css_dir):
        for f in sorted(os.listdir(css_dir)):
            if f.endswith(".css"):
                src_css += "\n" + read(os.path.join(css_dir, f))
    css = src_css
    built = read(os.path.join(ROOT, "dist", "style.css"))
    if built:
        css += "\n" + built
    elif src_css:
        info("dist/style.css가 없어 생성된 인라인 보정 규칙을 검사하지 못했다. "
             "npm run build 후 다시 실행하라.")

    js_dir = os.path.join(SRC, "js")
    js = ""
    if os.path.isdir(js_dir):
        for root, _, fs in os.walk(js_dir):
            for f in sorted(fs):
                if f.endswith(".js"):
                    js += "\n" + read(os.path.join(root, f))

    wl = json.load(open(os.path.join(ROOT, "data", "substitutions.json"), encoding="utf-8"))

    lint_html_balance(skin)
    lint_index_xml(xml)
    lint_substitutions(skin, xml, wl)
    lint_area_scope(skin)
    lint_boundaries(skin, css, js)
    lint_empty_substitution_decor(skin, src_css or css)
    lint_js_dom_classes(src_css, js)
    lint_markup_css(skin, src_css)
    lint_const_pairs(skin)
    lint_thumb_groups(skin)
    lint_notice_body(skin)
    lint_tokens(css)
    # 빌드 산출물이 있을 때만 돈다 — 생성된 --ph-* 정의와 생성기가 문자열로 쓰는
    # var(--error)·var(--link) 참조가 dist에만 있다.
    lint_token_usage(css, built is not None)
    # 같은 이유로 dist가 있을 때만 돈다 — images/ 경로는 dist 기준 상대경로다.
    lint_image_refs(built, os.path.join(ROOT, "dist"))
    lint_inline_coverage(css)
    # 이 둘은 **src만** 본다. dist는 src의 사본이라, src를 망가뜨려도 낡은 dist에
    # 옛 규칙이 남아 있으면 검사가 통과해 버린다(실제로 개발 중에 겪었다).
    # INL001과 달리 이 둘은 빌드가 생성하는 규칙을 보지 않으므로 src면 충분하다.
    lint_tistory_hardcoded(src_css)
    lint_tistory_comment_scope(src_css)
    lint_tistory_namecard_scope(src_css)
    lint_tistory_typography(src_css)
    lint_hljs_scope(src_css)
    lint_hljs_tokens(src_css)
    lint_reading_fixed(src_css)
    lint_placeholder_fill(skin, src_css)

    lint_naverad_surface(src_css)
    lint_cat_toggle_reserve(src_css)
    lint_print_ads(src_css)
    lint_robustness(js, skin)
    lint_seo(skin)
    # 문서는 skin.html이 없어도 검사한다 — 인용이 썩는 것은 구현 여부와 무관하다.
    lint_doc_line_refs(ROOT)
    lint_decision_refs(ROOT)

    emit_and_exit(args.json)


if __name__ == "__main__":
    main()
