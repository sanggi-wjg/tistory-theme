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
                if cls in ("contents_style", "tt_category") or cls.startswith("tt-"):
                    continue          # 티스토리가 렌더링하는 것
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


def lint_tokens(css):
    if not css:
        return
    # 토큰 정의부(:root 블록)와 인라인 스타일 보정 선택자는 제외한다
    body = re.sub(r":root[^{]*\{[^}]*\}", "", css, flags=re.S)
    body = re.sub(r"\[style\*=\"[^\"]*\"\]", "", body)
    hexes = HEX_RE.findall(body)
    if hexes:
        uniq = sorted(set(h.lower() for h in hexes))
        warn("TOK001", "토큰을 거치지 않은 색 리터럴 %d종: %s. var(--토큰)을 쓰지 않으면 "
             "다크모드에서 바뀌지 않는다." % (len(uniq), ", ".join(uniq[:8])), "src/styles/")

    # 미디어쿼리/[data-theme] 안에서 처음 정의된 색 → stamp 없는 시스템 테마에서 깨진다
    for m in re.finditer(r"(@media[^{]*prefers-color-scheme[^{]*|:root\[data-theme[^{]*)\{(.*?)\n\}",
                         css, re.S):
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
    css = ""
    if os.path.isdir(css_dir):
        for f in sorted(os.listdir(css_dir)):
            if f.endswith(".css"):
                css += "\n" + read(os.path.join(css_dir, f))
    built = read(os.path.join(ROOT, "dist", "style.css"))
    if built:
        css += "\n" + built
    elif css:
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
    lint_robustness(js, skin)

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
