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
        for s in sorted(sels):
            for cls in re.findall(r"\.([a-zA-Z][\w-]*)", s):
                # 티스토리가 렌더링하는 것. selected는 카테고리 트리에서 현재 가지의
                # li에 붙는다 (2026-08-25 실측 /category/Python).
                if cls in ("contents_style", "tt_category", "category_list",
                           "sub_category_list", "link_tit", "link_item",
                           "link_sub_item", "c_cnt", "selected") or cls.startswith("tt-"):
                    continue
                if ('class="%s' % cls) not in skin and ("class='%s" % cls) not in skin \
                        and (" %s" % cls) not in skin:
                    warn("BND004", "JS가 '%s'를 찾지만 skin.html에서 클래스 '%s'를 찾을 수 없다. "
                         "JS가 만드는 DOM이면 무시해도 된다." % (s, cls), "src/js/")

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
    스타일 없는 날것 DOM이 뜨고 끝이다 (TODO `js-class-css-drift`).

    두 축을 같이 본다. CSS 축만 보면 **문서가 JS에서 떨어져 나간 순간 검사가
    죽은 이름을 보고 통과한다** — 위조된 통과 신호(CLAUDE.md)의 네 번째 판이다.

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


def strip_comments(css):
    """/* … */ 를 걷어낸다.

    주석 안의 hex는 색 지정이 아니라 **설명**이다. tistory.css는 티스토리가 박아 둔
    리터럴(#333 · #909090 …)을 주석에 적어 두는데, 걷어내지 않으면 TOK001이
    그것을 매번 경고한다. 상시 경고는 린트를 통째로 무시하게 만든다 —
    같은 오탐으로 이미 한 번 데었다(CLAUDE.md 2026-08-25 TOK002 항목)."""
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    skin = read(os.path.join(SRC, "skin.html"))
    xml = read(os.path.join(SRC, "index.xml"))
    if skin is None:
        # 검사할 대상이 없는 것은 실패가 아니다. 구현 전에도 npm run check가 통과해야
        # 문서·인프라 변경을 커밋할 수 있다.
        print("ℹ️  src/skin.html이 없어 검사할 대상이 없다. 아직 구현 전이면 정상이다.")
        sys.exit(0)

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

    lint_substitutions(skin, xml, wl)
    lint_area_scope(skin)
    lint_boundaries(skin, css, js)
    lint_empty_substitution_decor(skin, src_css or css)
    lint_js_dom_classes(src_css, js)
    lint_markup_css(skin, src_css)
    lint_tokens(css)
    # 빌드 산출물이 있을 때만 돈다 — 생성된 --ph-* 정의와 생성기가 문자열로 쓰는
    # var(--error)·var(--link) 참조가 dist에만 있다.
    lint_token_usage(css, built is not None)
    lint_inline_coverage(css)
    # 이 둘은 **src만** 본다. dist는 src의 사본이라, src를 망가뜨려도 낡은 dist에
    # 옛 규칙이 남아 있으면 검사가 통과해 버린다(실제로 개발 중에 겪었다).
    # INL001과 달리 이 둘은 빌드가 생성하는 규칙을 보지 않으므로 src면 충분하다.
    lint_tistory_hardcoded(src_css)
    lint_tistory_comment_scope(src_css)
    lint_tistory_typography(src_css)
    lint_hljs_scope(src_css)
    lint_hljs_tokens(src_css)
    lint_robustness(js, skin)
    lint_seo(skin)

    if args.json:
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


if __name__ == "__main__":
    main()
