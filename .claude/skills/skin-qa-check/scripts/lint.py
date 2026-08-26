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
    """홈 목록과 일반 목록의 접두사가 섞이면 조용히 빈 화면이 된다."""
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

    if "s_list_rep" in skin and "s_index_article_rep" not in skin:
        warn("AREA003", "<s_list_rep>는 있는데 <s_index_article_rep>가 없다. 홈 목록이 비게 된다.",
             "src/skin.html")

    if "[##_body_id_##]" not in skin:
        warn("AREA004", "[##_body_id_##]가 없다. body_id로 페이지별 CSS 분기를 할 수 없다.",
             "src/skin.html")


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
    lint_tokens(css)
    lint_inline_coverage(css)
    # 이 둘은 **src만** 본다. dist는 src의 사본이라, src를 망가뜨려도 낡은 dist에
    # 옛 규칙이 남아 있으면 검사가 통과해 버린다(실제로 개발 중에 겪었다).
    # INL001과 달리 이 둘은 빌드가 생성하는 규칙을 보지 않으므로 src면 충분하다.
    lint_tistory_hardcoded(src_css)
    lint_tistory_comment_scope(src_css)
    lint_hljs_scope(src_css)
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
