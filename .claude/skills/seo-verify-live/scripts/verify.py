#!/usr/bin/env python3
"""배포 후 프로덕션 실물 SEO 검증.

소스 린트(skin-qa-check)는 "소스가 맞는가"까지만 본다. 이 스크립트는
"라이브가 맞는가"를 본다. 이 프로젝트는 배포가 스킨 편집기 수동 복붙이라
붙여넣다 잘린 마크업·안 올라간 파일·반영 안 된 CSS는 소스 린트가 잡지 못한다.

사용:
  python3 .claude/skills/seo-verify-live/scripts/verify.py --base https://sanggi-jayg.tistory.com
  python3 .claude/skills/seo-verify-live/scripts/verify.py --base ... --save-baseline
  python3 .claude/skills/seo-verify-live/scripts/verify.py --base ... --compare
  python3 .claude/skills/seo-verify-live/scripts/verify.py --base ... --json
  python3 .claude/skills/seo-verify-live/scripts/verify.py --base ... --protected-path /300
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

UA_PC = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

# .claude/skills/seo-verify-live/scripts/verify.py 에서 디렉터리 네 단계 위
# (scripts → seo-verify-live → skills → .claude → 루트)가 저장소 루트다.
# os.getcwd()를 쓰면 다른 디렉터리에서 돌릴 때 엉뚱한 곳에 baseline을 만들고,
# 배포 전/후 두 실행이 서로 다른 파일을 보게 된다.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
# baseline은 data/에 둔다. _workspace/는 .gitignore 대상이라
# "배포 전 저장 → 배포 후 비교" 사이에 세션이 바뀌면 기준선이 조용히 사라진다.
# data/*.json은 git으로 공유되는 자리다.
BASELINE = os.path.join(ROOT, "data", "seo-baseline.json")

ERRORS, WARNINGS, INFO, UNVERIFIED = [], [], [], []

# 응답이 아예 없던 페이지. "죽은 페이지"와 "네트워크가 흔들린 페이지"를
# 구분하지 않으면 점검 중에 돌린 검증이 없는 회귀를 만들어 낸다.
UNREACHED = set()

# 이번 실행에서 실제로 요청을 시도한 페이지 이름. 타깃 목록에 없던 페이지를
# "죽었다"고 신고하지 않으려면 이 구분이 필요하다.
ATTEMPTED = set()


def err(code, msg, where=""):
    ERRORS.append({"level": "error", "code": code, "message": msg, "where": where})


def warn(code, msg, where=""):
    WARNINGS.append({"level": "warning", "code": code, "message": msg, "where": where})


def info(msg):
    INFO.append(msg)


def unverified(code, msg, where=""):
    """검증하지 못한 것. 통과로 적지 않는다 — skin-qa-check와 같은 리포트 규칙."""
    UNVERIFIED.append({"level": "unverified", "code": code, "message": msg, "where": where})


# ─────────────────────────────── HTTP ───────────────────────────────

def fetch(url, ua=UA_PC, retries=2):
    """(status, body, final_url)을 돌려준다. 네트워크 실패는 status=None."""
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.status, r.read().decode("utf-8", "replace"), r.geturl()
        except urllib.error.HTTPError as e:
            # 4xx·5xx는 재시도해도 같다. 응답 자체가 검증 대상이다.
            return e.code, "", url
        except Exception as e:
            if i == retries:
                sys.stderr.write("  [네트워크 실패] %s — %s\n" % (url, e))
                return None, "", url
            time.sleep(1.5 * (i + 1))
    return None, "", url


# ─────────────────────────── HTML 파싱 보조 ───────────────────────────

# (?:^|[\s]) 로 앵커한다. \b 는 data-href 의 '-' 와 'h' 사이에서도 걸려
# data-href 를 진짜 href 로 읽는다.
HREF_RE = re.compile(r"""(?:^|\s)href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.I)


def href_of(tag):
    """큰따옴표·작은따옴표·따옴표 없음을 모두 받는다. HTML 엔티티도 푼다."""
    m = HREF_RE.search(tag)
    if not m:
        return None
    v = next((g for g in m.groups() if g is not None), "")
    return htmllib.unescape(v) or None


def load_json(path, what):
    """깨진 파일 하나가 리포트 전체를 날리지 않게 한다. 리포트는 main 끝에서
    한 번에 출력되므로, 중간에 예외가 나면 이미 모은 결과가 전부 사라진다."""
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception as e:
        unverified("V015", "%s 를 읽지 못했다 (%s). 파일이 깨졌거나 없다."
                   % (what, e.__class__.__name__), path)
        return None


def head_of(doc):
    return doc.split("</head>")[0] if "</head>" in doc else doc


def body_of(doc):
    """첫 </head> 뒤 전체. [-1]을 쓰면 본문에 인용된 </head> 뒤만 남아,
    그 앞의 링크와 잔존 치환자가 통째로 검사에서 빠진다."""
    return doc.split("</head>", 1)[1] if "</head>" in doc else doc


COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def strip_comments(doc):
    """HTML 주석은 티스토리 렌더링에도 그대로 남는다. 주석 처리해 둔 <h1>이
    살아 있는 h1으로 세어지면 매 페이지에서 V003이 거짓 오류를 낸다."""
    return COMMENT_RE.sub(" ", doc)


def count_tag(doc, tag):
    return len(re.findall(r"<%s[\s>]" % tag, strip_comments(doc), re.I))


def links_in(doc):
    """<a>의 href를 따옴표 형태와 무관하게 모은다. 본문은 에디터가 쓴 HTML이
    그대로 나오므로 작은따옴표 링크가 섞인다."""
    out = []
    for tag in re.findall(r"<a\b[^>]*>", doc, re.I):
        h = href_of(tag)
        if h:
            out.append(h)
    return out


# 티스토리 글 주소는 두 형태다 — 관리 → 블로그 → 주소 설정이 "문자"면 /entry/{제목},
# "숫자"면 /{번호}. 둘 다 200을 내고 canonical은 항상 문자 형태를 가리킨다.
# 한 형태만 세면 설정을 바꾸는 순간 "내부링크 0" 오경보가 난다.
# 모바일 접두사도 받는다. 모바일 페이지의 글 링크는 전부 접두사가 붙은 형태라,
# 이걸 빼면 V010이 "링크 0개"를 실제와 무관하게 항상 보고한다.
POST_PATH_RE = re.compile(r"^/(?:m/)?(?:entry/.+|\d+)$")
MOBILE_PREFIX = "/m/"


def normalize_post_path(path):
    return path[len(MOBILE_PREFIX) - 1:] if path.startswith(MOBILE_PREFIX) else path


def same_host(netloc, base_host):
    """부분문자열 비교는 evil-example.com을 example.com의 내부로 만든다.
    호스트명은 정확히 맞춰야 한다 (포트만 허용)."""
    return netloc.split(":")[0].lower() == base_host.split(":")[0].lower()


def entry_links(doc, base_host, self_path=None):
    """**다른** 글로 가는 내부링크의 (정규화 경로 집합, 형태별 개수).

    PC와 모바일 경로를 같은 글로 세려고 모바일 접두사를 벗긴다. 그리고 자기 자신은
    뺀다 — 글 페이지는 제목 링크·공유 버튼으로 자기 자신을 링크하므로(실측 2회),
    이걸 세면 관련글·이전/다음이 전부 죽어도 개수가 0이 아니게 되어
    V006의 하드 오류가 영영 뜨지 않는다."""
    out, forms = set(), {"entry": 0, "num": 0}
    me = normalize_post_path(urllib.parse.urlparse(self_path or "").path)
    # 주석 처리된 <a>는 살아 있는 링크가 아니다. 세면 baseline에 굳어
    # 나중에 주석을 지울 때 유령 회귀가 된다.
    for l in links_in(strip_comments(body_of(doc))):
        p = urllib.parse.urlparse(l)
        if p.netloc and not same_host(p.netloc, base_host):
            continue
        if not POST_PATH_RE.match(p.path):
            continue
        path = normalize_post_path(p.path)
        if me and path == me:
            continue
        if path not in out:
            forms["entry" if path.startswith("/entry/") else "num"] += 1
        out.add(path)
    return out, forms


PARSE_ERROR = "__PARSE_ERROR__"


def jsonld_types(doc):
    """JSON-LD의 @type을 전부 모은다.

    @type은 문자열일 수도 배열일 수도 있고(둘 다 유효하다), 노드가 @graph로
    감싸여 있을 수도 있다. 배열을 그대로 담으면 뒤의 set()에서 TypeError가 나
    검증 전체가 죽는다."""
    types = []

    def walk(node):
        if isinstance(node, list):
            for n in node:
                walk(n)
            return
        if not isinstance(node, dict):
            return
        t = node.get("@type")
        if isinstance(t, list):
            types.extend(str(x) for x in t)
        elif t:
            types.append(str(t))
        graph = node.get("@graph")
        if graph:
            walk(graph)

    for raw in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', doc, re.S | re.I):
        try:
            # unescape하지 않는다. <script>는 raw text라 엔티티가 디코드되지 않으며,
            # 티스토리가 제목의 "를 &quot;로 넣어 둔 것을 풀면 JSON이 깨진다.
            data = json.loads(raw.strip())
        except Exception:
            types.append(PARSE_ERROR)
            continue
        walk(data)
    return types


def canonical_of(doc):
    """HTML 속성 순서는 자유다. rel이 href보다 뒤에 와도 잡아야 한다."""
    for tag in re.findall(r"<link\b[^>]*>", head_of(doc), re.I):
        if not re.search(r"""\brel\s*=\s*["']?canonical\b""", tag, re.I):
            continue
        h = href_of(tag)
        if h:
            return h
    return None


# ──────────────────── 검증할 글·카테고리 고르기 ────────────────────

# data/posts.json은 **본 블로그** 실측이다. 테스트 블로그를 검증하면서 그 경로를
# 그대로 붙이면 있지도 않은 글·카테고리를 두드려 404가 나고, --save-baseline은
# V014로 아무것도 저장하지 못한다. 2026-08-25 실측: git-rich-quick.tistory.com에
# /entry/타이밍어택…과 /category/AI를 요청해 둘 다 404, baseline 저장 실패.
# 그래서 **대상 블로그가 실측과 다르면 대상 블로그에서 직접 찾는다.**
_RESOLVED = {}


def host_of(value):
    """'sanggi-jayg.tistory.com'도 'https://sanggi-jayg.tistory.com/'도 받는다."""
    v = (value or "").strip()
    if not v:
        return ""
    if "//" not in v:
        v = "//" + v
    return urllib.parse.urlparse(v).netloc


def census_targets(base_host):
    """실측에서 글 경로·상위 카테고리를 꺼낸다. 다른 블로그면 (None, None, 사유)."""
    posts_path = os.path.join(ROOT, "data", "posts.json")
    if not os.path.exists(posts_path):
        return None, None, ("data/posts.json이 없다. 검증할 글·카테고리를 "
                            "대상 블로그에서 직접 찾는다.")
    d = load_json(posts_path, "data/posts.json") or {}
    blog = host_of(d.get("blog"))
    if blog and not same_host(blog, base_host):
        return None, None, ("data/posts.json은 %s 실측인데 검증 대상은 %s 다. "
                            "실측의 글·카테고리는 이 블로그에 없으므로 쓰지 않고 "
                            "대상 블로그에서 직접 찾는다." % (blog, base_host))
    posts = d.get("posts") or []
    url = (posts[0].get("url") or "") if posts else ""
    path = None
    if url:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        if not path.startswith("/"):
            path = "/" + path
    cats = sorted({p.get("category", "").split("/")[0]
                   for p in posts if p.get("category")})
    return path, (cats[0] if cats else None), None


def category_names(doc, base_host):
    """문서에 나온 카테고리 이름을 등장 순서대로. 상위 카테고리를 앞에 둔다.

    상위를 앞에 두는 이유 — V013의 페이징 검사는 글이 많은 목록이라야 2페이지가
    있다. 하위 카테고리를 집으면 글이 적어 2페이지가 없고, 검사가 조용히 미검증이 된다."""
    top, sub = [], []
    for l in links_in(doc):
        p = urllib.parse.urlparse(l)
        if p.netloc and not same_host(p.netloc, base_host):
            continue
        path = p.path[2:] if p.path.startswith(MOBILE_PREFIX) else p.path
        if not path.startswith("/category/"):
            continue
        name = urllib.parse.unquote(path[len("/category/"):]).strip("/")
        if not name:
            continue
        (top if "/" not in name else sub).append(name.split("/")[0])
    return top + sub


def discover_targets(base, base_host):
    """대상 블로그에서 글 경로·카테고리를 직접 찾는다. 홈 → sitemap.xml 순."""
    post = cat = None
    status, doc, _ = fetch(base + "/")
    if status == 200 and doc:
        paths, _forms = entry_links(doc, base_host)
        if paths:
            post = sorted(paths)[0]
        names = category_names(doc, base_host)
        if names:
            cat = names[0]
    if post and cat:
        return post, cat
    # 홈이 비었거나(이전 스킨이 목록을 안 깔았거나) 카테고리 모듈이 꺼져 있을 수 있다.
    # sitemap.xml은 티스토리가 만들어 주므로 스킨과 무관하게 남아 있다.
    status, sm, _ = fetch(base + "/sitemap.xml")
    if status == 200 and sm:
        for loc in re.findall(r"<loc>([^<]+)</loc>", sm):
            p = urllib.parse.urlparse(loc)
            if p.netloc and not same_host(p.netloc, base_host):
                continue
            path = normalize_post_path(p.path)
            if not post and POST_PATH_RE.match(path):
                post = path
            if not cat and path.startswith("/category/"):
                name = urllib.parse.unquote(path[len("/category/"):]).strip("/")
                if name:
                    cat = name.split("/")[0]
            if post and cat:
                break
    return post, cat


def resolve_targets(base, base_host, cli_post=None, cli_cat=None):
    """검증에 쓸 (글 경로, 상위 카테고리 이름)을 한 번 정하고 재사용한다.

    우선순위: 명령줄 지정 > 실측(같은 블로그일 때) > 대상 블로그에서 발견."""
    if _RESOLVED:
        return _RESOLVED

    post, cat = cli_post, cli_cat
    post_src = "--post-path" if post else ""
    cat_src = "--category" if cat else ""

    if not (post and cat) and os.path.exists(BASELINE):
        # 기준선이 본 대상을 그대로 이어 쓴다. 실측(posts.json)은 글이 늘면 첫 글이
        # 바뀌고, 발견도 홈 목록이 바뀌면 따라 바뀐다. 어느 쪽이든 배포 전/후가
        # 다른 글을 비교하게 되므로, 같은 블로그의 기준선이 있으면 그것이 우선이다.
        saved = load_json(BASELINE, "기존 baseline") or {}
        if (saved.get("base") or "").rstrip("/") == base.rstrip("/"):
            saved_t = saved.get("targets") or {}
            if not post and saved_t.get("post"):
                post, post_src = saved_t["post"], "baseline"
            if not cat and saved_t.get("category"):
                cat, cat_src = saved_t["category"], "baseline"

    if not (post and cat):
        c_post, c_cat, why = census_targets(base_host)
        if why:
            info(why)
        if not post and c_post:
            post, post_src = c_post, "data/posts.json"
        if not cat and c_cat:
            cat, cat_src = c_cat, "data/posts.json"

    if not (post and cat):
        # 실측이 못 채운 것만 찾는다. 본 블로그를 검증할 때는 이 요청이 아예 없다.
        d_post, d_cat = discover_targets(base, base_host)
        if not post and d_post:
            post, post_src = d_post, "대상 블로그에서 발견"
        if not cat and d_cat:
            cat, cat_src = d_cat, "대상 블로그에서 발견"

    if post:
        info("검증할 글: %s (%s)" % (post, post_src))
    else:
        unverified("V000", "검증할 글 URL을 찾지 못했다. 홈에도 sitemap.xml에도 글 링크가 "
                   "없다. --post-path /entry/... 로 직접 지정하라.", base + "/")
    if cat:
        info("검증할 카테고리: %s (%s)" % (cat, cat_src))
    else:
        unverified("V000", "검증할 카테고리를 찾지 못했다. 카테고리가 없거나 모듈이 꺼져 "
                   "있을 수 있다. --category 이름 으로 직접 지정하라.", base + "/")

    _RESOLVED.update({"post": post, "category": cat})
    return _RESOLVED


# ─────────────────────────── 검증할 URL 목록 ───────────────────────────

def page_targets(base, base_host):
    """라이브 URL 8종.

    skin-preview는 12개를 렌더하지만 그중 page_toc·tag_cloud는 **같은 URL 타입의 다른 상태**다
    (목차 유/무, 태그 목록/클라우드). 여기서 세는 것은 URL 종류이므로 8이 맞다.
    """
    t = resolve_targets(base, base_host)
    targets = [("index", base + "/")]
    if t["post"]:
        targets.append(("page", base + t["post"]))
    if t["category"]:
        targets.append(("category", base + "/category/" + urllib.parse.quote(t["category"])))
    targets += [
        ("archive",   base + "/archive"),
        ("tag",       base + "/tag"),
        ("search",    base + "/search/" + urllib.parse.quote("리팩토링")),
        ("empty",     base + "/search/" + urllib.parse.quote("존재하지않는검색어zzz")),
        ("guestbook", base + "/guestbook"),
    ]
    return targets


# ─────────────────────────────── 검증 ───────────────────────────────

def verify_page(name, url, doc, status, base_host, stats, final=None):
    """페이지 하나를 검증하고 baseline용 지표를 stats에 채운다."""
    where = "%s (%s)" % (name, url)

    # V001 — 응답
    if status is None:
        UNREACHED.add(name)
        unverified("V001", "응답이 없다. 네트워크·차단·점검 중일 수 있다. "
                   "실패로 단정하지 않는다.", where)
        return
    if status != 200:
        err("V001", "HTTP %d. 이 페이지 타입이 죽어 있다." % status, where)
        return

    # 리다이렉트를 따라가 다른 페이지를 받았다면, 그 페이지를 이 페이지 타입으로
    # 검증하면 안 된다. 방명록을 끄면 /guestbook → / 가 되고, 홈 마크업으로
    # h1·canonical이 전부 통과해 "이 페이지 타입은 멀쩡하다"고 보고하게 된다.
    if final and urllib.parse.urlparse(final).path.rstrip("/") != urllib.parse.urlparse(url).path.rstrip("/"):
        warn("V001", "요청한 주소가 %s 로 넘어갔다. 이 페이지 타입이 꺼져 있거나 "
             "다른 곳으로 리다이렉트된다 — 아래 지표는 넘어간 쪽의 것이다." % final, where)

    h1 = count_tag(doc, "h1")
    elinks, forms = entry_links(doc, base_host, self_path=final or url)
    ld = jsonld_types(doc)
    stats[name] = {
        "status": status, "h1": h1, "entryLinks": len(elinks),
        "linkForms": forms, "jsonld": sorted(set(ld) - {PARSE_ERROR}), "bytes": len(doc),
        "url": url,
    }

    # V002 — 미치환 치환자 잔존
    # 검사 범위를 좁힌다. 이 블로그는 개발 블로그라 본문에서 티스토리 치환자를
    # 예시로 인용하고, 티스토리는 그 본문 평문으로 <meta description>과 JSON-LD를
    # 만든다. head까지 훑으면 치환자를 다룬 글 한 편이 "붙여넣다 잘렸다"는
    # 하드 오류를 만든다. 그래서 body만, 그중에서도 코드블록·스크립트·주석은 뺀다.
    scannable = strip_comments(body_of(doc))
    scannable = re.sub(r"<(pre|code|script|style)\b.*?</\1>", " ", scannable, flags=re.S | re.I)
    # <title>은 검사하지 않는다. 티스토리가 글 제목을 그대로 넣으므로,
    # 제목에 치환자를 쓴 글("[##_article_rep_title_##] 정리" 같은)이 곧바로
    # 오탐이 된다 — 바로 위에서 피하겠다고 한 그 오탐이다.
    leftovers = (re.findall(r"\[##_[a-zA-Z0-9_]+_##\]", scannable)
                 + re.findall(r"</?s_[a-zA-Z0-9_]+>", scannable))
    if leftovers:
        uniq = sorted(set(leftovers))[:5]
        if name == "page":
            err("V002", "치환자가 그대로 출력됐다: %s. 티스토리가 해석하지 못한 것이고, "
                "방문자에게도 보인다." % ", ".join(uniq), where)
        else:
            # 목록 페이지의 요약문은 본문에서 마크업을 걷어낸 평문이라
            # <pre>/<code> 제거가 통하지 않는다. 치환자를 인용한 글 한 편이
            # 여러 목록을 동시에 터뜨리므로 경고로 둔다.
            warn("V002", "치환자로 보이는 문자열이 있다: %s. 목록 페이지의 글 요약은 "
                 "마크업이 걷힌 평문이라, 치환자를 인용한 글이 실렸을 수도 있다 — "
                 "글 페이지에서 함께 떴는지 보고 판단하라." % ", ".join(uniq), where)

    # V003 — 헤딩 계층
    #
    # 홈도 h1을 갖는다. 2026-08-25 실측으로 <s_list>가 홈에서도 렌더되는 것을 확인했고
    # (list_conform이 "전체 글"로 채워진다), 그 .list-title이 홈의 h1이다.
    # 그전까지 "홈은 h1 0개가 정상"이라는 예외를 두고 있었는데, 그건 홈 목록을
    # <s_index_article_rep>로 그리려다 그 영역이 통째로 죽어서 생긴 착시였다
    # (DECISIONS.md 결정 29). 예외를 지웠다 — 이제 홈의 h1 0개는 진짜 결함이다.
    if h1 == 0:
        err("V003", "h1이 없다. 이 페이지가 무엇에 관한 문서인지 크롤러가 알 수 없다.", where)
    elif h1 > 1:
        err("V003", "h1이 %d개다. 페이지당 정확히 1개여야 한다. "
            "헤더처럼 전 페이지에 있는 자리에 h1을 두면 반드시 이렇게 된다." % h1, where)

    # V004 — lang
    if not re.search(r"<html[^>]*\blang=", doc, re.I):
        warn("V004", "<html>에 lang 속성이 없다.", where)

    # V005 — canonical
    if not canonical_of(doc):
        warn("V005", "canonical이 없다. 티스토리가 넣어 주던 것이므로, 없다면 "
             "스킨이 <head>를 깨뜨렸을 가능성이 있다.", where)

    # V006 — 글 페이지 내부링크
    if name == "page":
        if len(elinks) == 0:
            err("V006", "다른 글로 가는 링크가 하나도 없다. 관련글·이전/다음 치환자가 "
                "렌더되지 않았다. 내부링크는 스킨이 쥔 가장 큰 SEO 레버다.", where)
        elif len(elinks) < 3:
            warn("V006", "다른 글로 가는 링크가 %d개뿐이다. 관련글·이전/다음 중 일부가 "
                 "비어 있는지 확인하라." % len(elinks), where)
        if forms["num"] and not forms["entry"]:
            warn("V006", "내부 글 링크 %d개가 전부 /{번호} 형태다. canonical은 "
                 "/entry/{제목}을 가리키므로 내부링크가 전부 비정규 주소를 향한다. "
                 "관리 → 블로그 → 주소 설정을 '문자'로 두는 편이 낫다." % forms["num"], where)

        # V007 — 구조화 데이터
        if "__PARSE_ERROR__" in ld:
            err("V007", "JSON-LD가 파싱되지 않는다. 스킨이 넣은 블록의 문법 오류이거나, "
                "치환자가 따옴표를 깨뜨렸다.", where)
        if "BlogPosting" not in ld:
            warn("V007", "BlogPosting JSON-LD가 없다. 티스토리가 넣어 주던 것이다.", where)
        if "BreadcrumbList" not in ld:
            info("%s — 글 페이지에 BreadcrumbList JSON-LD가 없다. 티스토리는 카테고리 "
                 "페이지에만 넣어 주므로, 글 페이지 빵부스러기는 스킨이 채울 수 있는 "
                 "자리다 (DECISIONS.md 결정 28)." % name)

        # V008 — 이미지 alt (콘텐츠 이슈. 스킨으로 고칠 수 없으므로 보고만 한다)
        imgs = re.findall(r"<img[^>]*>", strip_comments(body_of(doc)), re.I)
        if imgs:
            alt_re = re.compile(r"""(?:^|\s)alt\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s"'>]+))""", re.I)
            with_alt = sum(1 for i in imgs if alt_re.search(i))
            if with_alt < len(imgs):
                info("V008 — %s — 이미지 %d장 중 alt가 있는 것은 %d장. 본문 이미지는 에디터에서 "
                     "쓰므로 스킨으로 고칠 수 없다. 사용자에게 보고할 항목."
                     % (name, len(imgs), with_alt))


def skin_css_of(doc, base):
    """문서가 거는 스킨 스타일시트의 (표준경로 URL, 대체후보)를 돌려준다.

    V009와 V010이 같은 기준을 써야 한다 — 한쪽은 미검증으로, 다른 쪽은 오류로
    처리하면 같은 상황이 실행마다 다른 결론이 된다."""
    live_url, fallback = None, None
    for tag in re.findall(r"<link\b[^>]*>", head_of(doc), re.I):
        h = href_of(tag)
        if not h or not h.endswith(".css") and ".css?" not in h:
            continue
        if "/skin/style.css" in h:
            # 루트상대·프로토콜상대·절대 URL을 전부 흡수한다.
            live_url = urllib.parse.urljoin(base + "/", h)
            break
        # 티스토리가 스스로 붙이는 시트는 후보가 아니다. 실물 홈에서 첫 style.css는
        # 항상 .../static/plugin/BusinessLicenseInfo/style.css 다.
        if "style.css" in h and fallback is None and "tistory_admin" not in h:
            fallback = h
    return live_url, fallback


def verify_skin_applied(base, home_doc):
    """V009 — 라이브 CSS가 우리가 빌드한 것인가. 찾은 스킨 CSS URL을 돌려준다."""
    live_url, fallback = skin_css_of(home_doc, base)
    dist = os.path.join(ROOT, "dist", "style.css")
    if not os.path.exists(dist):
        # 절대경로로 알린다. dist/는 .gitignore라 체크아웃 밖으로 나가지 않는데,
        # 상대경로만 찍으면 "빌드를 안 했다"와 "빌드한 곳이 아닌 체크아웃에서 돌렸다"가
        # 똑같이 보인다. 후자가 실제로 일어난다(2026-08-25).
        unverified("V009", "dist/style.css가 없어 스킨 반영 여부를 대조하지 못했다. "
                   "이 체크아웃에서 npm run build 를 먼저 돌려라 — 다른 체크아웃에서 "
                   "빌드했다면 그 dist/는 여기서 보이지 않는다.", dist)
        return live_url
    if not live_url:
        if fallback:
            # 스킨 CSS인지 단정할 수 없다. 오류로 적으면 멀쩡한 배포를 막는다.
            unverified("V009", "티스토리 표준 경로(/skin/style.css)의 스타일시트를 찾지 "
                       "못했다. 대신 %s 가 걸려 있다 — 이것이 스킨 CSS인지 눈으로 "
                       "확인하라." % fallback, base + "/")
        else:
            err("V009", "홈에 스킨 스타일시트가 하나도 없다. 커스텀 스킨이 적용되지 "
                "않았거나 <head>가 깨졌다.", base + "/")
        return None
    status, live_css, _ = fetch(live_url)
    if status != 200 or not live_css:
        unverified("V009", "라이브 style.css를 받지 못했다 (HTTP %s)." % status, live_url)
        return live_url
    local = open(dist, encoding="utf-8").read()
    # 스킨 편집기는 textarea라 제출 시 개행이 CRLF로 정규화될 수 있다.
    # 그걸 차이로 세면 멀쩡한 배포가 "붙여넣기가 잘렸다"가 된다.
    norm = lambda t: t.replace("\r\n", "\n").replace("\r", "\n").strip()
    if norm(live_css) == norm(local):
        info("스킨 CSS가 dist/style.css와 일치한다 (%d bytes)." % len(local))
    else:
        err("V009", "라이브 style.css가 dist/style.css와 다르다 (라이브 %d bytes / 로컬 %d bytes). "
            "붙여넣기가 잘렸거나 이번 빌드가 아직 반영되지 않았다."
            % (len(live_css), len(local)), live_url)
    return live_url


def verify_mobile(base, post_url, pc_skin_css=None):
    """V010 — 모바일 우선 색인. 이 프로젝트의 최대 SEO 리스크다.

    pc_skin_css는 PC 홈이 실제로 건 스킨 CSS URL이다. 스마트폰이 같은 것을
    받는지 대조해야 "같은 스킨"이라 말할 수 있다 — 경로가 있다는 것만으로는
    티스토리 기본 스킨과 구별되지 않는다."""
    if not post_url:
        unverified("V010", "글 URL이 없어 모바일 동등성을 확인하지 못했다.", "")
        return
    status, doc, final = fetch(post_url, ua=UA_MOBILE)
    if status is None:
        unverified("V010", "모바일 UA 요청이 응답하지 않았다.", post_url)
        return
    if status != 200 or not doc:
        # 실패한 요청은 리다이렉트가 없었던 것처럼 보인다. 그걸 "모바일웹 OFF"로
        # 읽으면 이 프로젝트 최대 리스크를 근거 없이 해결됐다고 선언하게 된다.
        unverified("V010", "모바일 UA 요청이 HTTP %s를 냈다. 모바일웹 설정을 판단할 수 "
                   "없다 — 차단이나 점검일 수 있다." % status, post_url)
        return
    if MOBILE_PREFIX not in final:
        # 리다이렉트가 없다고 곧 OFF는 아니다. UA를 보고 같은 URL에 다른 스킨을
        # 줄 수도 있다. PC가 건 스킨 CSS와 같은 것을 받았는지로 판정한다.
        mob_h1 = count_tag(doc, "h1")
        mob_css, _ = skin_css_of(doc, base)
        if pc_skin_css and mob_css and mob_css == pc_skin_css:
            info("모바일웹 OFF 확인 — 스마트폰 UA가 PC와 같은 스킨 CSS를 받는다 "
                 "(%s, h1 %d개). 반응형 스킨이 양쪽을 담당한다 (DECISIONS.md 결정 2)."
                 % (mob_css, mob_h1))
        elif pc_skin_css and mob_css and mob_css != pc_skin_css:
            err("V010", "리다이렉트는 없는데 스마트폰이 PC와 다른 스타일시트를 받는다 "
                "(PC %s / 모바일 %s). 같은 URL에서 UA로 다른 스킨을 주고 있다 — "
                "h1 %d개. 모바일 우선 색인이 보는 쪽이 이 문서다."
                % (pc_skin_css, mob_css, mob_h1), final)
        else:
            # 한쪽이라도 스킨 CSS를 못 찾았다. V009와 같은 기준으로 미검증이다.
            unverified("V010", "리다이렉트는 없으나 PC/모바일 스킨 CSS를 대조하지 못해 "
                       "(PC %s / 모바일 %s) 동등성을 단정할 수 없다 — h1 %d개. "
                       "눈으로 확인하라."
                       % (pc_skin_css or "없음", mob_css or "없음", mob_h1), final)
        return
    # /m/ 으로 넘어갔다 = 모바일웹 자동 연결이 켜져 있다
    h1 = count_tag(doc, "h1")
    elinks = len(entry_links(doc, urllib.parse.urlparse(base).netloc, self_path=final)[0])
    has_skin = skin_css_of(doc, base)[0] is not None
    err("V010", "모바일웹 자동 연결이 켜져 있다. 스마트폰 UA가 %s 로 302되고, 거기서 "
        "커스텀 스킨은 %s. 구글은 모바일 우선 색인이므로 크롤러가 보는 쪽은 이 페이지다 "
        "— h1 %d개, 다른 글로 가는 링크 %d개. 관리 → 꾸미기 → 모바일 → "
        "모바일웹 자동 연결을 꺼야 한다 (DECISIONS.md 결정 2). "
        "코드로 고칠 수 없다 — 사용자 조치 항목이다."
        % (final, "로드된다" if has_skin else "로드되지 않는다", h1, elinks), post_url)


def verify_paging_canonical(base):
    """V013 — 목록 2페이지의 canonical이 어디를 가리키는가.

    2026-08-25 실측: /category/{X}?page=2 의 canonical이 /category/{X}가 아니라
    사이트 루트를 가리킨다. 2페이지 이후 목록은 독립 색인되지 않는다는 뜻이다.
    티스토리 소관이라 스킨으로 못 고치지만, 모르면 "페이징으로 크롤링되겠지"라고
    잘못 설계한다. 티스토리가 고치면 이 검사가 알려 준다."""
    cat = _RESOLVED.get("category")
    if not cat:
        return
    url = base + "/category/" + urllib.parse.quote(cat) + "?page=2"
    status, doc, _ = fetch(url)
    if status != 200 or not doc:
        unverified("V013", "목록 2페이지를 받지 못했다 (HTTP %s)." % status, url)
        return
    canon = canonical_of(doc)
    if not canon:
        warn("V013", "목록 2페이지에 canonical이 없다. 다른 페이지에는 티스토리가 "
             "넣어 주므로 확인이 필요하다.", url)
        return
    if urllib.parse.urlparse(canon).path.rstrip("/") in ("", "/"):
        info("목록 2페이지의 canonical이 사이트 루트를 가리킨다 (%s → %s). 티스토리 동작이고 "
             "스킨으로 못 고친다. 2페이지 이후 목록은 독립 색인되지 않으므로, 깊은 글로 가는 "
             "경로를 페이징에만 의존하면 안 된다." % (url, canon))
    else:
        info("목록 2페이지의 canonical: %s" % canon)


def paging_shape(doc, ignore=frozenset()):
    """`nav.paging` → (토큰들, 번호 목록). nav가 없으면 None.

    토큰은 티스토리가 상태를 싣는 자리만 남긴다(결정 53) — 이전·다음은 (종류, 상태 클래스, href 유무),
    번호는 ("num", href 유무, 안쪽 span의 class, 숫자면 "N" 아니면 글자). 번호 목록은 생략 부호를 None으로.
    숫자를 "N"으로 지우는 것은 총 페이지 수가 프리뷰(PAGING_TOTAL)와 달라도 모양은 같게 보려는 것이다.
    ignore: 스킨이 글자 그대로 쓴 class(`skin_paging`) — 티스토리가 아니라 우리가 정한 것이라 상태에서 뺀다.
    속성 이름은 `(?:^|\\s)`로 붙인다 — `\b`는 `data-href`의 `-` 뒤에서도 맞는다(HREF_RE와 같은 함정).
    """
    m = re.search(r'<nav\b[^>]*\sclass\s*=\s*["\'][^"\']*\bpaging\b[^"\']*["\'][^>]*>(.*?)</nav>', doc or "", re.S | re.I)
    if not m:
        return None
    toks, nums = [], []
    for a in re.finditer(r"<a\b([^>]*)>(.*?)</a>", m.group(1), re.S | re.I):
        attrs, inner = a.group(1), a.group(2)
        c = re.search(r'(?:^|\s)class\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        classes = (c.group(1) if c else "").split()
        href = bool(re.search(r"(?:^|\s)href\s*=", attrs, re.I))
        if "paging-num" in classes:
            sp = re.search(r'<span\b[^>]*?\sclass\s*=\s*["\']([^"\']*)["\'][^>]*>(.*?)</span>', inner, re.S | re.I)
            span_cls = sp.group(1).strip() if sp else None
            text = re.sub(r"<[^>]+>|\s+", "", sp.group(2) if sp else inner)
            nums.append(int(text) if text.isdigit() else None)
            toks.append(("num", href, span_cls, "N" if text.isdigit() else text))
        else:
            kind = next((k for k in ("paging-prev", "paging-next") if k in classes), "?")
            toks.append((kind, " ".join(sorted(x for x in classes if x != kind and x not in ignore)), href))
    return toks, nums


def paging_drift(fixture_html, live_html, cur, live_total, paging_items, ignore=frozenset()):
    """프리뷰가 그린 페이징과 라이브 페이징이 갈린 곳들(문장 목록). 비면 같다.

    둘을 본다 — ① 모양(토큰)이 같은가, ② 라이브 번호 목록이 렌더러의 규칙(`paging_items` — 첫·끝 + 현재 ±3,
    끊기면 ···)과 같은가. ①만 보면 티스토리가 창을 ±2로 줄여도 모르고, ②만 보면 클래스가 바뀌어도 모른다.
    """
    fx, lv = paging_shape(fixture_html, ignore), paging_shape(live_html, ignore)
    if lv is None:
        return ["라이브 %d페이지에 nav.paging이 없다" % cur]
    if fx is None:
        return ["프리뷰가 %d페이지 페이징을 그리지 않는다" % cur]
    out = []
    if fx[0] != lv[0]:
        diff = next(i for i in range(max(len(fx[0]), len(lv[0])))
                    if i >= len(fx[0]) or i >= len(lv[0]) or fx[0][i] != lv[0][i])
        out.append("%d페이지 모양이 다르다 — %d번째 칸: 프리뷰 %s / 라이브 %s" % (
            cur, diff + 1, fx[0][diff] if diff < len(fx[0]) else "(없음)",
            lv[0][diff] if diff < len(lv[0]) else "(없음)"))
    want = paging_items(cur, total=live_total)
    if lv[1] != want:
        out.append("%d페이지 번호 목록이 렌더러 규칙과 다르다 — 규칙 %s / 라이브 %s" % (
            cur, " ".join(str(n) if n else "···" for n in want), " ".join(str(n) if n else "···" for n in lv[1])))
    return out


def load_renderer():
    """프리뷰 렌더러(render.py)를 모듈로 — 픽스처를 **그 코드 그대로** 그리려고. 실패하면 None.

    ⚠ importlib로 불러오지 않고 소스를 직접 컴파일한다. importlib는 `__pycache__`에 바이트코드를 남기고
    「소스 mtime(초)·크기」가 같으면 그것을 다시 쓴다 — 같은 초 안에 같은 길이로 바뀐 소스(`no-more-prev`→
    `no_more_prev`)를 옛 코드로 돌렸다(2026-10-09, 변이를 되돌린 뒤 test:paging이 변이를 봤다).
    """
    import types
    try:
        mod = types.ModuleType("preview_render")
        mod.__file__ = RENDER_PY
        with open(RENDER_PY, encoding="utf-8") as f:
            exec(compile(f.read(), RENDER_PY, "exec"), mod.__dict__)
    except (Exception, SystemExit):
        return None
    mod.ROOT, mod.SRC = ROOT, os.path.join(ROOT, "src")  # render.py는 cwd를 저장소 루트로 가정한다
    return mod


def skin_paging():
    """skin.html의 `<s_paging>` 블록과, 그 안 앵커에 스킨이 **글자 그대로** 쓴 class들(종류 class 셋은 남긴다).

    티스토리가 싣는 상태는 `[##_no_more_*_##]` 치환 결과뿐이다. 스킨이 `paging-arrow` 같은 class를 더하면
    라이브는 배포 전까지 그것이 없어 「갈림」이 된다 — 우리 쪽 변경을 티스토리의 변경으로 읽지 않게 뺀다.
    """
    skin = open(os.path.join(ROOT, "src", "skin.html"), encoding="utf-8").read()
    m = re.search(r"<s_paging>.*?</s_paging>", skin, re.S)
    if not m:
        return None, frozenset()
    lit = set()
    for c in re.findall(r'<a\b[^>]*?\sclass\s*=\s*["\']([^"\']*)["\']', m.group(0), re.I):
        lit |= {t for t in c.split() if "[##" not in t and "##]" not in t}
    return m.group(0), frozenset(lit - {"paging-prev", "paging-next", "paging-num"})


def fixture_navs(mod, block):
    """프리뷰가 그리는 페이징 — {현재 페이지: html}. 홈(1)·카테고리(9)·보관함(마지막) — 라이브 1·9·끝과 짝이다."""
    posts, cats = mod.load_fixtures()
    out = {}
    for page in ("index", "category", "archive"):
        ctx = mod.globals_for(page, posts, cats, {})
        out[mod.PAGING_CURRENT[page]] = mod.render(block, ctx, page, posts)
    return out


def verify_paging_fixture(base, home_doc):
    """V018 — 프리뷰 페이징 픽스처가 라이브 마크업과 같은가(이슈 #88).

    결정 53: 티스토리는 현재 페이지를 `span.selected`로, 생략 부호를 href 없는 `a.paging-num`으로,
    끝을 `no-more-prev`·`no-more-next`(하이픈, href 없음)로 낸다. 2026-09-10까지 CSS가 밑줄
    이름을 보고 있었는데 아무 검사도 몰랐다 — 프리뷰가 그 모양을 그리지 않았기 때문이다. 지금은
    프리뷰가 그리지만, 티스토리가 출력을 바꾸면 CSS와 픽스처가 **같이** 낡은 채 프리뷰는 계속
    통과한다. 그래서 라이브 홈 1·9·끝 페이지를 받아 프리뷰가 같은 페이지에 그리는 것과 대조한다.
    예외로 멈추면 미검증으로 남긴다 — 뒤의 검사와 리포트까지 잃지 않게.
    """
    try:
        _verify_paging_fixture(base, home_doc)
    except Exception as e:
        unverified("V018", "페이징 대조가 예외로 멈췄다 (%s: %s)." % (type(e).__name__, e), RENDER_PY)


def _verify_paging_fixture(base, home_doc):
    import inspect
    mod = load_renderer()
    if mod is None or not hasattr(mod, "paging_items"):
        unverified("V018", "프리뷰 렌더러(render.py)를 불러오지 못해 페이징 픽스처를 대조하지 못했다.", RENDER_PY)
        return
    block, lit = skin_paging()
    if block is None:
        unverified("V018", "skin.html에서 <s_paging> 블록을 찾지 못했다.", os.path.join(ROOT, "src", "skin.html"))
        return
    fixtures = fixture_navs(mod, block)
    middle, last = mod.PAGING_CURRENT["category"], mod.PAGING_TOTAL
    if sorted(fixtures) != [1, middle, last]:
        unverified("V018", "프리뷰가 그리는 페이지가 1·%d·%d가 아니다(%s) — 라이브와 짝을 지을 수 없다."
                   % (middle, last, sorted(fixtures)), RENDER_PY)
        return
    first = paging_shape(home_doc, lit)
    if first is None:
        unverified("V018", "라이브 홈에 nav.paging이 없어 페이징 모양을 대조하지 못했다.", base + "/")
        return
    live_total = max([n for n in first[1] if n] or [0])
    if live_total != last:
        info("라이브 홈은 %d페이지, 프리뷰 PAGING_TOTAL은 %d다. 모양 대조에는 상관없지만 render.py를 맞추면 "
             "프리뷰 번호가 실물과 같아진다." % (live_total, last))
    # 1페이지는 총수와 상관없이 늘 대조한다 — 홈의 번호가 깨져 총수를 못 읽어도 갈림은 경고로 나와야 한다
    problems = [p + " (" + base + "/)" for p in paging_drift(fixtures[1], home_doc, 1, live_total, mod.paging_items, lit)]
    compared = [1]
    # 가운데 페이지가 양쪽 생략 부호를 다 가지려면 middle + window < 끝 - 1
    window = inspect.signature(mod.paging_items).parameters["window"].default
    if live_total < middle + window + 2:
        unverified("V018", "라이브가 %d페이지뿐이라 프리뷰의 %d페이지 모양(양끝 생략 부호)·끝 페이지와 대조할 수 없다."
                   % (live_total, middle), base + "/")
    else:
        for cur, live_cur in ((middle, middle), (last, live_total)):
            url = base + "/?page=%d" % live_cur
            status, doc, _ = fetch(url)
            time.sleep(0.4)
            if status != 200 or not doc:
                unverified("V018", "라이브 %d페이지를 받지 못했다 (HTTP %s)." % (live_cur, status), url)
                continue
            problems += [p + " (" + url + ")"
                         for p in paging_drift(fixtures[cur], doc, live_cur, live_total, mod.paging_items, lit)]
            compared.append(live_cur)
    for p in problems:
        warn("V018", "프리뷰 페이징 픽스처가 라이브와 갈렸다 — " + p + ". 티스토리가 페이징 출력을 바꿨다면 "
             "render.py 픽스처와 CSS(.paging의 selected·:not([href])·no-more-*)를 같이 고친다(결정 53).")
    if not problems:
        # 실제로 대조한 페이지만 적는다 — 못 받은 페이지를 「같다」에 넣으면 그것이 위조된 통과 신호다
        info("페이징 — 라이브 %s페이지가 프리뷰 픽스처와 같은 모양이다%s." % (
            "·".join(map(str, compared)), "" if len(compared) == 3 else " (나머지는 대조하지 못했다 — 미검증 참조)"))


def verify_category_tree(base, home_doc):
    """V016 — 라이브 카테고리 트리가 리스트형인가.

    2026-08-25 첫 배포에서 폴더형([##_category_##])이 나갔다 (DECISIONS.md 결정 31).
    린트 CAT001이 소스를 막지만 **배포는 손으로 하는 복붙이라 소스가 맞아도
    프로덕션이 틀릴 수 있다** — 이 스킬이 존재하는 이유가 정확히 그것이다.

    폴더형이 나가면 사이드바에서 가장 큰 모듈의 내부링크가 통째로 0이 된다.
    링크가 <a href>가 아니라 onclick이라 크롤러도 키보드도 닿지 않는다.
    V010의 내부링크 집계는 홈 전체를 세므로 이 손실을 개별로 짚어 주지 못한다.
    """
    if not home_doc:
        unverified("V016", "홈을 받지 못해 카테고리 트리 형식을 확인하지 못했다.", base + "/")
        return

    doc = strip_comments(home_doc)
    folder = re.search(r'id=["\']treeComponent["\']', doc, re.I)
    listed = re.search(r'class=["\'][^"\']*\btt_category\b', doc, re.I)

    if folder:
        err("V016", "카테고리 트리가 **폴더형**으로 렌더됐다 (table#treeComponent). "
            "링크가 onclick이라 사이드바 카테고리의 내부링크가 0개이고, 인라인 색이 "
            "다크모드를 이긴다. skin.html의 [##_category_##]를 [##_category_list_##]로 "
            "바꿔 CSS 탭이 아니라 **HTML 탭**을 다시 올려라 (DECISIONS.md 결정 31).",
            base + "/")
        return

    if not listed:
        unverified("V016", "홈에서 카테고리 트리를 찾지 못했다 (ul.tt_category 없음). "
                   "사이드바 카테고리 모듈이 꺼져 있으면 정상이다.", base + "/")
        return

    # 리스트형이 맞다면 트리 안의 /category 링크 수를 세어 둔다.
    # 상위 14 + 하위 21 + 분류 전체보기 1 = 36이 이 블로그의 기대값이다.
    n = len(re.findall(r'<a[^>]+href=["\'][^"\']*/category', doc, re.I))
    info("카테고리 트리 — 리스트형(ul.tt_category), /category 링크 %d개." % n)
    if n == 0:
        err("V016", "리스트형 트리인데 /category 링크가 하나도 없다. 마크업이 잘려 "
            "붙여넣어졌을 수 있다.", base + "/")


def verify_platform_assets(base):
    """V011 — 티스토리 소관 자산. 우리가 만들지는 않지만 죽으면 유입이 죽는다."""
    for name, path in (("robots.txt", "/robots.txt"), ("sitemap.xml", "/sitemap.xml")):
        status, doc, _ = fetch(base + path)
        if status is None:
            unverified("V011", "%s 를 받지 못했다." % name, base + path)
        elif status != 200:
            err("V011", "%s 가 HTTP %d다. 티스토리가 제공하던 것이므로 원인을 "
                "확인해야 한다." % (name, status), base + path)
        elif name == "sitemap.xml":
            locs = re.findall(r"<loc>(.*?)</loc>", doc)
            info("sitemap.xml — URL %d개 (그중 /m/ %d개)."
                 % (len(locs), sum(1 for l in locs if "/m/" in l)))


RENDER_PY = os.path.join(ROOT, ".claude", "skills", "skin-preview", "scripts", "render.py")


def preview_sheet_url(name):
    """render.py의 TISTORY_*_CSS 상수 — 괄호로 이어붙인 문자열 리터럴을 합친다."""
    src = open(RENDER_PY, encoding="utf-8").read() if os.path.exists(RENDER_PY) else ""
    m = re.search(name + r"\s*=\s*\((.*?)\)", src, re.S)
    return "".join(re.findall(r'"([^"]+)"', m.group(1))) if m else None


def verify_tistory_sheets(base, home_doc, post_doc):
    """V017 — 프리뷰가 싣는 티스토리 시트가 라이브와 같은가.

    프리뷰는 티스토리 content.css를 **우리 앞에** 실어 특이도 싸움을 재현한다(결정 32·35).
    그런데 그 URL이 render.py에 해시째 박혀 있어, 티스토리가 시트를 배포하면 프리뷰는
    낡은 상대와 싸우면서 통과 신호를 낸다 — 아무 검사도 모르는 채로. 여기서 라이브 홈이
    링크한 URL과 대조하고, URL이 다르면 바이트까지 대조한다.

    시트는 셋이다 — content.css, `static/pc/dist/index.css`(**댓글·프로필 카드 React 앱의
    시트**), `static/style/tistory.css`(**티스토리 툴바** — 결정 59의 헤더 예약이 이 시트의
    `right`·`max-width:1260px`에 맞춰져 있고, 결정 68이 이 시트의 라이트 전용 색을 다크에서 덮는다). 셋 다 **홈 head**에서 찾는다 — 2026-09-10 재실측에서
    index.css 링크는 홈·방명록·글 페이지 셋 다 각 1건이었다. 한때 "글 페이지에만 온다"고 적고 `post_doc`에서만 찾았는데
    틀렸다 — 글 페이지를 못 받은 실행에서 대조가 통째로 미검증이 됐다. 글 페이지 전용인 것은
    시트가 아니라 **Namecard div**다. index.css는 TIS003·TIS005의 상대인데, 그 둘은 소스에
    빈 껍데기뿐이라 크롤로도 프리뷰로도 존재가 안 보인다. 시트가 갈리면 프리뷰의 카드·댓글이
    **없는 상대와 싸우고** 통과 신호를 낸다.

    atom-one-light(결정 32의 두 번째 전제)은 2026-08-27 실측에서 글 페이지 소스 HTML에
    **없었다.** 있든 없든 info로 남긴다 — 프리뷰가 그 시트를 우리 뒤에 싣는 것은 더 엄격한
    조건이라 해롭지 않지만, 전제가 흔들린 것은 적어 둬야 다음 사람이 안다.
    """
    def compare(const, path_fragment, label, doc, doc_url, codes):
        want = preview_sheet_url(const)
        live = None
        for tag in re.findall(r"<link\b[^>]*>", head_of(doc or ""), re.I):
            h = href_of(tag)
            if h and path_fragment in h:
                live = urllib.parse.urljoin(base + "/", h)
                break
        if not want:
            unverified("V017", "render.py에서 %s를 읽지 못했다 — 상수 모양이 바뀌었나." % const, RENDER_PY)
            return live
        if not doc:
            unverified("V017", "%s를 받지 못해 티스토리 %s를 대조하지 못했다." % (doc_url, label), doc_url)
        elif not live:
            unverified("V017", "라이브 head에서 티스토리 %s 링크를 찾지 못했다(%s). "
                       "티스토리가 시트 경로를 바꿨다면 render.py 상수도 같이 봐야 한다."
                       % (label, doc_url), doc_url)
        elif live == want:
            info("V017 — 프리뷰가 싣는 티스토리 %s가 라이브와 같은 URL이다." % label)
        else:
            s1, b1, _ = fetch(live)
            s2, b2, _ = fetch(want)
            if s1 is None or s2 is None:
                # 네트워크 실패를 «내용이 다르다»로 읽으면 render.py를 고치라는 거짓 지시가 된다.
                unverified("V017", "티스토리 %s를 받지 못해(라이브 HTTP %s / render.py HTTP %s) "
                           "내용을 대조하지 못했다. URL은 다르다 — 라이브: %s"
                           % (label, s1, s2, live), RENDER_PY)
            elif s1 == 200 and s2 == 200 and b1 == b2:
                info("V017 — 티스토리 %s 해시가 바뀌었지만 내용은 같다(%d bytes). render.py "
                     "%s를 %s 로 갱신해 두라." % (label, len(b1.encode("utf-8")), const, live))
            else:
                warn("V017", "프리뷰가 싣는 티스토리 %s가 라이브와 다르다 — render.py: %s (HTTP %s) / "
                     "라이브: %s (HTTP %s). 프리뷰의 특이도 싸움이 낡은 상대와 벌어진다. 상수를 갱신하고 "
                     "data/tistory-hardcoded-colors.json을 새 시트와 다시 대조하라(%s)."
                     % (label, want, s2, live, s1, codes), RENDER_PY)
        return live

    compare("TISTORY_CONTENT_CSS", "/static/style/content.css", "content.css",
            home_doc, base + "/", "TIS001~004")
    # React 앱 시트(댓글 Comment · 프로필 카드 Namecard). **모든 페이지**에 링크된다
    # (2026-09-10 실측: 홈·방명록·글 페이지 각 1건). 그래서 content.css와 똑같이 홈에서
    # 찾는다 — 글 페이지를 못 받아도 대조가 선다. TIS003·TIS005의 상대가 이 파일이고,
    # 그 둘은 프리뷰로도 크롤로도 존재가 안 보이는 부류라 이 대조가 유일한 신호다.
    home_idx = compare("TISTORY_INDEX_CSS", "/static/pc/dist/index.css", "index.css",
                       home_doc, base + "/", "TIS003·TIS005")
    # 툴바 시트(.menu_toolbar — 1261px부터 오른쪽 위에 고정). 결정 59의 헤더 예약은 이 시트의
    # 숫자 셋(right 20px · max-width 1260px · 툴바 폭)에 맞춘 것이라, 티스토리가 바꾸면 예약이 조용히
    # 어긋난다. 프리뷰가 이 시트로 툴바 픽스처를 그리므로 URL이 낡으면 겹침이 다시 숨는다.
    compare("TISTORY_TOOLBAR_CSS", "/static/style/tistory.css", "tistory.css",
            home_doc, base + "/", "결정 59 헤더 예약 · 결정 68 다크 덮어쓰기(TIS001)")
    # 글 페이지에도 같은 URL로 오는지는 덤이다. 다르면 두 페이지가 서로 다른 배포를
    # 받고 있다는 뜻이라, 프리뷰가 어느 쪽과 싸우는지부터 다시 정해야 한다.
    # ⚠ 대조 상대는 **라이브 홈의** URL이다. 2026-10-06까지 render.py 상수와 비교해 놓고 메시지는
    #    「홈과 글 페이지가 다르다」라고 냈다 — 상수가 낡기만 해도 두 페이지가 갈린 것처럼 경고했다.
    #    홈 링크를 못 찾았을 때만 상수로 물러난다.
    if post_doc:
        want_idx = home_idx or preview_sheet_url("TISTORY_INDEX_CSS")
        live_idx = None
        for tag in re.findall(r"<link\b[^>]*>", head_of(post_doc), re.I):
            h = href_of(tag)
            if h and "/static/pc/dist/index.css" in h:
                live_idx = urllib.parse.urljoin(base + "/", h)
                break
        if live_idx and want_idx and live_idx == want_idx:
            info("V017 — 글 페이지의 index.css도 같은 URL이다(Namecard·댓글이 여기서 온다).")
        elif live_idx:
            warn("V017", "index.css가 홈과 글 페이지에서 다르다 — 글 페이지: %s. 두 페이지가 "
                 "서로 다른 배포를 받고 있다." % live_idx, RENDER_PY)
        else:
            info("V017 — 글 페이지 head에서 index.css 링크를 찾지 못했다. 2026-09-10 실측과 "
                 "다르다(그때는 홈·방명록·글 셋 다 있었다) — 티스토리가 주입 방식을 바꿨을 수 있다.")
    if post_doc:
        if re.search(r"highlight\.js/[\d.]+/styles/atom-one-light", post_doc):
            info("V017 — 글 페이지 소스 HTML에 티스토리의 atom-one-light 링크가 있다(결정 32의 전제 유효).")
        else:
            info("V017 — 글 페이지 소스 HTML에 atom-one-light 링크가 **없다**(2026-08-27 실측과 같다). "
                 "결정 32·HLJS001의 전제(티스토리가 우리 뒤에 싣는다)는 런타임 주입이거나 사라진 것일 수 "
                 "있다. 프리뷰가 그 시트를 우리 뒤에 싣는 것은 더 엄격한 조건이라 해롭지 않다.")


# ─────────────────────── 프로필 카드(Namecard) ───────────────────────
#
# V017은 Namecard의 **시트**(index.css)를 대조한다. 카드의 **마크업**은 시트가 아니라 스크립트 번들
# (`static/pc/dist/index.js`)의 React 컴포넌트가 만든다 — 프리뷰 픽스처(`render.py` `namecard_box`)와 린트
# TIS005의 marker는 그 컴포넌트에서 옮긴 것이다(#89). 번들이 클래스를 바꾸면 픽스처·TIS005가 같이 낡은 채
# 통과한다(결정 42 부류, #131). 그래서 V019가 라이브 번들의 Namecard 컴포넌트를 픽스처와 대조한다.

NAMECARD_BUNDLE_PATH = "/static/pc/dist/index.js"


def js_skip_string(s, i):
    """s[i]가 따옴표(", ', `)일 때 그 문자열 바로 다음 인덱스. 닫히지 않으면 len(s)."""
    q, i = s[i], i + 1
    while i < len(s):
        if s[i] == "\\":
            i += 2
            continue
        if s[i] == q:
            return i + 1
        i += 1
    return len(s)


def js_match(s, i):
    """s[i]의 여는 괄호(`(` `[` `{`)에 짝인 닫는 괄호의 인덱스. 문자열 안의 괄호는 건너뛴다. 못 찾으면 -1.

    ⚠ 정규식 리터럴과 템플릿 안의 `${` 중첩은 모른다 — 압축된 번들의 컴포넌트 하나를 자르는 데만 쓴다.
       짝이 틀어지면 -1이 나와 V019가 미검증으로 물러난다(통과로 읽히지 않는다).
    """
    close = {"(": ")", "[": "]", "{": "}"}
    stack = []
    while i < len(s):
        c = s[i]
        if c in "\"'`":
            i = js_skip_string(s, i)
            continue
        if c in close:
            stack.append(close[c])
        elif c in ")]}":
            if not stack or stack.pop() != c:
                return -1
            if not stack:
                return i
        i += 1
    return -1


def bundle_component(js, app="Namecard"):
    """번들에서 `data-tistory-react-app="<app>"`에 물리는 컴포넌트의 소스. 못 찾으면 None.

    번들은 앱 이름 → 컴포넌트 표(`{Comment:g8,Namecard:_8,…}`)로 그릇을 채운다(2026-10-10 @e0a0fbc).
    `Comment:`가 같이 있는 표만 믿는다 — `Namecard:` 키는 다른 객체에도 우연히 있을 수 있다.
    정의는 `function X(){…}`이거나 `X=(…)=>{…}`다. 둘 다 아니면 None — 대조기가 낡은 것이다.
    """
    name = None
    for m in re.finditer(r"\{[^{}]*?(?<![\w$])%s:([\w$]+)[^{}]*\}" % re.escape(app), js or ""):
        if re.search(r"(?<![\w$])Comment:", m.group(0)):
            name = m.group(1)
            break
    if not name:
        return None
    n = re.escape(name)
    found = []
    for d in re.finditer(r"(?<![\w$.])function\s+%s\s*\(" % n, js):
        p = js_match(js, d.end() - 1)
        b = p + 1 if p != -1 else -1
        while 0 <= b < len(js) and js[b].isspace():
            b += 1
        if 0 <= b < len(js) and js[b] == "{":
            e = js_match(js, b)
            if e != -1:
                found.append(js[d.start():e + 1])
    for d in re.finditer(r"(?<![\w$.])%s\s*=(?![=>])\s*" % n, js):
        i = d.end()
        if i < len(js) and js[i] == "(":
            i = js_match(js, i) + 1
            if i == 0:
                continue
        else:
            a = re.match(r"[\w$]+", js[i:])
            if not a:
                continue
            i += a.end()
        arrow = re.match(r"\s*=>\s*", js[i:])
        if not arrow:
            continue
        b = i + arrow.end()
        if b < len(js) and js[b] in "{(":
            e = js_match(js, b)
            if e != -1:
                found.append(js[d.start():e + 1])
    # 압축기는 짧은 이름을 다른 스코프에서 다시 쓴다. 정의가 둘 이상이면 어느 것이 앱 표의 그것인지
    # 여기서는 가리지 못한다 — 아무거나 고르면 엉뚱한 컴포넌트와 대조하고 통과할 수 있어 None(미검증)으로 물러난다.
    return found[0] if len(found) == 1 else None


def bundle_nodes(src):
    """컴포넌트 소스의 jsx 호출마다 (호출 위치, props 객체의 닫는 괄호 위치 또는 -1, 서명 또는 None, 태그).

    서명은 `태그.클래스.클래스`(클래스 정렬 — 순서는 상태가 아니다). className이 없는 원소(svg·path·그릇 div)는
    서명이 None이다 — 집합 대조는 클래스만 보지만, 자리 대조는 그 태그를 길에 남긴다(`namecard_drift`). 그 밖의 경우:
    - `className`이 문자열 리터럴이 아니면 `태그.{동적}` — 조건부 클래스로 바뀐 것도 갈림으로 잡혀야 한다.
    - props가 객체 리터럴이 아니면(`E.jsx("a",p)`) 클래스를 알 수 없어 `태그.{동적}` — 건너뛰면 그 원소가
      대조에서 조용히 빠진다.
    - 태그가 문자열이 아니라 다른 컴포넌트(`E.jsx(Xy,{…})`)면 `<Xy>` — 카드가 하위 컴포넌트로 쪼개지면
      그 안의 클래스가 이 소스에 없어 대조가 헐거워지므로, 그 사실 자체를 갈림으로 낸다.
    - props의 짝을 못 맞추면 `태그.{잘림}`(그 원소는 자식을 품을 수 없어 자리 대조를 미검증으로 돌린다).
    `E.jsx("a",{…})`와 esbuild식 `(0,E.jsx)("a",{…})` 둘 다 읽는다.
    """
    nodes = []
    for m in re.finditer(r"\.jsxs?\)?\(\s*(?:\"([\w-]+)\"|([\w$.]+))\s*,\s*(\{)?", src or ""):
        tag, comp = m.group(1), m.group(2)
        end = js_match(src, m.end() - 1) if m.group(3) else -1
        if comp:
            nodes.append((m.start(), end, "<%s>" % comp, "<%s>" % comp))
            continue
        if not m.group(3):
            nodes.append((m.start(), -1, "%s.{동적}" % tag, tag))
            continue
        if end == -1:
            nodes.append((m.start(), -1, "%s.{잘림}" % tag, tag))
            continue
        i, depth, sig = m.end(), 0, None
        while i < end:
            c = src[i]
            if c in "\"'`":
                i = js_skip_string(src, i)
                continue
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and src.startswith("className", i) and src[i - 1] in "{,":
                v = re.match(r"className\s*:\s*(?:\"([^\"\\]*)\"|'([^'\\]*)')\s*[,}]", src[i:end + 1])
                cls = (v.group(1) if v.group(1) is not None else v.group(2)).split() if v else None
                sig = ".".join([tag] + sorted(cls)) if cls else ("%s.{동적}" % tag if cls is None else None)
                break
            i += 1
        nodes.append((m.start(), end, sig, tag))
    return nodes


def bundle_signatures(src):
    """컴포넌트 소스의 jsx 원소 서명 집합 — {"태그.클래스.클래스", …}. 서명 규칙은 `bundle_nodes`."""
    return {n[2] for n in bundle_nodes(src) if n[2]}


def bundle_tree(src):
    """번들 컴포넌트 → 원소 목록 [{"label", "sig", "parent"(인덱스 또는 None), "children"(인덱스 목록)}].

    부모는 **그 jsx 호출의 props 객체 안에 든** 가장 안쪽 호출이다(`children`·조건식 `a&&E.jsx(…)`·삼항이
    전부 props 안이다). 호출은 소스 순서로 오므로 열린 props 범위의 스택 하나로 찾는다. label은 서명이
    있으면 서명, 없으면 태그(svg·그릇 div)다.
    """
    out, stack = [], []
    for pos, end, sig, tag in bundle_nodes(src):
        while stack and out[stack[-1]]["end"] < pos:
            stack.pop()
        parent = stack[-1] if stack else None
        out.append({"label": sig or tag, "sig": sig, "parent": parent, "children": [], "end": end})
        if parent is not None:
            out[parent]["children"].append(len(out) - 1)
        if end != -1:
            stack.append(len(out) - 1)
    return out


class _FixtureTree(HTMLParser):
    """픽스처 HTML → `bundle_tree`와 같은 모양의 원소 목록. `data-tistory-react-app` 그릇은 **경계**다 —
    그릇은 티스토리 서버 HTML이고 번들 컴포넌트는 그 안만 그리므로, 그릇 안의 첫 원소가 뿌리가 된다.

    ⚠ 브라우저의 암묵적 닫기(`<p>` 안의 `<div>` 등)는 흉내 내지 않는다 — 픽스처는 우리가 쓰는 마크업이라
       그런 모양을 쓰지 않는다.
    """
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack = [], []   # stack: (태그, 원소 인덱스 또는 None=경계)

    def _open(self, tag, attrs, void):
        a = dict(attrs)
        if a.get("data-tistory-react-app") is not None:
            if not void:
                self.stack.append((tag, None))
            return
        cls = (a.get("class") or "").split()
        sig = ".".join([tag] + sorted(cls)) if cls else None
        parent = self.stack[-1][1] if self.stack else None
        self.nodes.append({"label": sig or tag, "sig": sig, "parent": parent, "children": []})
        if parent is not None:
            self.nodes[parent]["children"].append(len(self.nodes) - 1)
        if not void:
            self.stack.append((tag, len(self.nodes) - 1))

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, tag in self.VOID)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def fixture_tree(html):
    p = _FixtureTree()
    p.feed(html or "")
    p.close()
    return p.nodes


def fixture_signatures(html):
    """프리뷰 픽스처 HTML → {"태그.클래스.클래스", …}. 자리 대조와 **같은 파서**(`fixture_tree`)에서 뽑는다."""
    return {n["sig"] for n in fixture_tree(html) if n["sig"]}


def tree_paths(tree, common):
    """원소마다 「가장 가까운 **공통** 조상 > 사이의 원소들 > 자기」. 조상이 없으면 `^`부터.

    공통(양쪽에 다 있는 서명)이 아닌 조상은 길에 남는다 — 클래스 없는 그릇 div가 새로 끼었거나, 부모의
    이름이 바뀌었는데 자식이 그 밖으로 옮겨진 것이 둘 다 길이 달라져 잡힌다(#134 코드 리뷰). 공통인 원소만
    시작점으로 쓴다 — 한쪽에만 있는 원소는 위에서 이미 갈림으로 나왔다.
    """
    out = set()
    for n in tree:
        if n["sig"] not in common:
            continue
        hops, p = [], n["parent"]
        while p is not None and tree[p]["sig"] not in common:
            hops.append(tree[p]["label"])
            p = tree[p]["parent"]
        head = tree[p]["sig"] if p is not None else "^"
        out.add(" > ".join([head] + hops[::-1] + [n["sig"]]))
    return out


def tree_orders(tree, common):
    """{부모 서명: [자식 서명 순서, …]} — 공통 서명끼리만. 같은 부모 서명이 여럿이면 순서 목록이 여럿이다."""
    out = {}
    for n in tree:
        if n["sig"] in common:
            seq = [tree[c]["sig"] for c in n["children"] if tree[c]["sig"] in common]
            if len(seq) > 1:
                out.setdefault(n["sig"], []).append(seq)
    return out


def is_subsequence(short, long):
    it = iter(long)
    return all(x in it for x in short)


def namecard_drift(bundle_js, fixture_htmls):
    """(갈림 문장 목록, 번들 서명 수, 자리 대조를 못 한 이유 또는 None). 컴포넌트를 못 찾으면 (None, 0, None).

    셋을 본다.
    ① **원소 집합** — 픽스처는 상태 넷(구독 여부 × 크리에이터 여부)의 **합집합**으로 본다. 번들 컴포넌트는 조건
       분기를 전부 담고 있어서다. 번들에만 있으면 픽스처가 그리지 않는 원소(다크 덮어쓰기가 프리뷰에서 매칭될
       상대가 없다), 픽스처에만 있으면 실물에 없는 원소(죽은 덮어쓰기를 살아 있다고 보여 준다).
    ② **자리** — 양쪽에 다 있는 원소의 「가장 가까운 공통 조상 > 사이 원소 > 자기」 길(#134). 집합만 보면 클래스가
       그대로인 채 다른 부모로 옮겨지거나 클래스 없는 그릇이 새로 낀 것을 놓친다.
    ③ **형제 순서** — 상태마다 픽스처의 자식 순서가 번들 자식 순서의 부분열이어야 한다(번들은 삼항의 두 갈래를
       나란히 담으므로 부분열로 본다). 썸네일이 왼쪽으로 옮겨진 것 같은 좌우 반전이 여기서 잡힌다.
    ②③은 번들 트리를 확정할 수 있을 때만 — 뿌리가 둘 이상이면(원소를 변수로 먼저 만들어 `children`에 넘겼다)
    소스 위치가 DOM 위치가 아니고, `{잘림}` 원소는 자식을 품지 못한다. 그때는 이유를 돌려 미검증으로 남긴다.
    """
    src = bundle_component(bundle_js)
    if src is None:
        return None, 0, None
    btree = bundle_tree(src)
    ftrees = [fixture_tree(h) for h in fixture_htmls]
    live = {n["sig"] for n in btree if n["sig"]}
    fx = {n["sig"] for t in ftrees for n in t if n["sig"]}
    out = []
    only_live, only_fx = sorted(live - fx), sorted(fx - live)
    if only_live:
        out.append("번들에만 있다: " + ", ".join(only_live))
    if only_fx:
        out.append("프리뷰 픽스처에만 있다: " + ", ".join(only_fx))

    roots = [n["label"] for n in btree if n["parent"] is None]
    cut = sorted(n["label"] for n in btree if n["label"].endswith(".{잘림}"))
    if len(roots) > 1:
        return out, len(live), ("번들 컴포넌트의 최상위 원소가 %d개다(%s) — 원소를 변수로 먼저 만들어 넘기면 소스 위치가 "
                                "DOM 위치가 아니라 자리를 확정할 수 없다" % (len(roots), ", ".join(roots)))
    if cut:
        return out, len(live), "props를 끝까지 읽지 못한 원소가 있다(%s) — 그 자식들의 자리를 확정할 수 없다" % ", ".join(cut)

    common = live & fx
    live_paths = tree_paths(btree, common)
    fx_paths = set()
    for t in ftrees:
        fx_paths |= tree_paths(t, common)
    moved_live, moved_fx = sorted(live_paths - fx_paths), sorted(fx_paths - live_paths)
    if moved_live or moved_fx:
        out.append("자리가 다르다 — 번들: %s / 프리뷰: %s" % (
            ", ".join(moved_live) or "(없음)", ", ".join(moved_fx) or "(없음)"))

    live_orders = tree_orders(btree, common)
    bad = {}   # 부모마다 첫 위반 하나만 — 상태 넷이 같은 위반을 네 줄로 늘어놓지 않게
    for t in ftrees:
        for parent, seqs in tree_orders(t, common).items():
            for seq in seqs:
                if parent in live_orders and parent not in bad and not any(
                        is_subsequence(seq, l) for l in live_orders[parent]):
                    bad[parent] = "%s 안: 프리뷰 %s / 번들 %s" % (
                        parent, " → ".join(seq), " → ".join(live_orders[parent][0]))
    if bad:
        out.append("형제 순서가 다르다 — " + "; ".join(bad[k] for k in sorted(bad)))
    return out, len(live), None


def bundle_url_of(doc, base):
    """라이브 문서가 싣는 티스토리 번들(`static/pc/dist/index.js`) URL. 없으면 None.

    `index-legacy.js`(nomodule)는 같은 디렉터리의 다른 파일이라 경로 끝까지 맞춘다.
    """
    for tag in re.findall(r"<script\b[^>]*>", doc or "", re.I):
        s = re.search(r'(?:^|\s)src\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if s and urllib.parse.urlparse(s.group(1)).path.endswith(NAMECARD_BUNDLE_PATH):
            return urllib.parse.urljoin(base + "/", htmllib.unescape(s.group(1)))
    return None


def verify_namecard_bundle(base, home_doc):
    """V019 — 프리뷰 Namecard 픽스처가 라이브 번들의 Namecard 컴포넌트와 같은 원소·클래스·자리인가(#131·#134).

    예외로 멈추면 미검증으로 남긴다 — 뒤의 검사와 리포트까지 잃지 않게(V018과 같다).
    """
    try:
        _verify_namecard_bundle(base, home_doc)
    except Exception as e:
        unverified("V019", "Namecard 번들 대조가 예외로 멈췄다 (%s: %s)." % (type(e).__name__, e), RENDER_PY)


def _verify_namecard_bundle(base, home_doc):
    url = bundle_url_of(home_doc, base)
    if not url:
        unverified("V019", "라이브 홈에서 티스토리 번들(%s) 링크를 찾지 못했다 — 경로가 바뀌었다면 "
                   "Namecard 컴포넌트를 어디서 받는지부터 다시 봐야 한다." % NAMECARD_BUNDLE_PATH, base + "/")
        return
    mod = load_renderer()
    if mod is None:
        unverified("V019", "프리뷰 렌더러(render.py)를 불러오지 못했다.", RENDER_PY)
        return
    if not hasattr(mod, "namecard_states"):
        unverified("V019", "render.py에 namecard_states가 없어 픽스처 상태를 모으지 못했다.", RENDER_PY)
        return
    fixtures = mod.namecard_states()
    status, js, _ = fetch(url)
    if status != 200 or not js:
        unverified("V019", "티스토리 번들을 받지 못했다 (HTTP %s)." % status, url)
        return
    problems, n, unshaped = namecard_drift(js, fixtures)
    if problems is None:
        unverified("V019", "번들에서 Namecard 컴포넌트를 찾지 못했다(앱 표 `{Comment:…,Namecard:…}`나 정의 모양이 "
                   "바뀌었다). 대조기(verify.py bundle_component)를 번들에 맞춰 고친 뒤 다시 돌린다 — 그동안 "
                   "픽스처·TIS005가 낡았는지 알 수 없다.", url)
        return
    if unshaped:
        unverified("V019", "Namecard 원소의 자리·형제 순서를 대조하지 못했다 — %s. 원소 집합 대조만 했다. "
                   "대조기(verify.py bundle_tree)를 번들에 맞춰 고친다." % unshaped, url)
    if problems:
        warn("V019", "프리뷰 Namecard 픽스처가 라이브 번들과 갈렸다 — %s. 티스토리가 카드 마크업을 바꿨다면 "
             "render.py namecard_box, data/tistory-hardcoded-colors.json namecardRules(TIS005), "
             "src/styles/tistory.css의 Namecard 덮어쓰기를 같이 고친다(결정 53, #89)." % " / ".join(problems), url)
    else:
        pinned = preview_sheet_url("TISTORY_NAMECARD_BUNDLE")
        tail = ("render.py TISTORY_NAMECARD_BUNDLE과 같은 번들이다" if pinned == url else
                "번들 해시는 render.py TISTORY_NAMECARD_BUNDLE(%s)과 다르지만 카드 마크업은 같다 — 상수를 %s 로 "
                "갱신해 두라" % (pinned, url))
        info("V019 — 프리뷰 Namecard 픽스처가 라이브 번들 컴포넌트와 같은 원소·클래스 %d종이다%s. %s." % (
            n, "" if unshaped else "(자리·형제 순서도 같다)", tail))


class _NamecardAncestry(HTMLParser):
    """Namecard 그릇마다 조상들의 (태그, class 목록). 닫는 태그를 빼먹은 HTML도 가장 가까운 같은 태그까지 닫는다.

    ⚠ 브라우저의 트리 구성 규칙(표 안의 엇나간 `</div>` 무시 등)은 흉내 내지 않는다 — 그런 마크업에서는
       안·밖 판정이 브라우저와 갈릴 수 있다. 의심되면 SKILL.md 「V020 손 절차」로 실물 DOM을 본다.
    """
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.hits = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("data-tistory-react-app") == "Namecard":
            self.hits.append(list(self.stack))
        if tag not in self.VOID:
            self.stack.append((tag, (a.get("class") or "").split()))

    def handle_startendtag(self, tag, attrs):
        if dict(attrs).get("data-tistory-react-app") == "Namecard":
            self.hits.append(list(self.stack))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def namecard_ancestry(doc):
    """문서의 Namecard 그릇마다 조상 (태그, class 목록)들의 목록. 그릇이 없으면 []."""
    p = _NamecardAncestry()
    p.feed(doc or "")
    p.close()
    return p.hits


def verify_namecard_protected(base, path):
    """V020 — 예외로 멈추면 미검증으로 남긴다(V018·V019와 같다). 본문은 `_verify_namecard_protected`."""
    try:
        _verify_namecard_protected(base, path)
    except Exception as e:
        unverified("V020", "보호글 Namecard 대조가 예외로 멈췄다 (%s: %s)." % (type(e).__name__, e), base + "/")


def protected_url(base, path):
    """`--protected-path` → URL. 절대 URL이면 그대로, 경로면 base에 붙인다. 한글 경로는 퍼센트 인코딩한다
    (urllib는 비ASCII URL에서 예외를 내고, fetch는 그것을 「못 받았다」로 삼켜 이유가 사라진다)."""
    u = urllib.parse.urlsplit(path)
    if not u.netloc:
        u = urllib.parse.urlsplit(base + (path if path.startswith("/") else "/" + path))
    return urllib.parse.urlunsplit(u._replace(path=urllib.parse.quote(u.path, safe="/%"),
                                              query=urllib.parse.quote(u.query, safe="=&%")))


def _verify_namecard_protected(base, path):
    """V020 — 보호글 페이지에 Namecard가 주입되는가, 되면 `.entry-main` 안인가(#130).

    우리 덮어쓰기는 전부 `.entry-main [data-tistory-react-app="Namecard"] .tt_box_namecard`로 시작한다
    (TIS005 접두). 그런데 보호글 영역(`<s_article_protected>` → `section.protected`)에는 `<s_rp>`도
    `.entry-main`도 없다. 티스토리가 거기에도 카드를 넣는데 `.entry-main` 밖이면 규칙이 하나도 매칭되지
    않아 다크에서 라이트 전용 #f7f7f7 판으로 뜬다(#59와 같은 모양). 보호글은 목록에서 찾을 수 없어
    (2026-10-10: 홈 1~25쪽·글 번호 1~299 어디에도 없었다) 경로를 `--protected-path`로 받는다.
    경로가 없으면 **미검증**이다 — 재지 않은 자리를 통과로 적지 않는다.

    로그아웃 화면만 본다. 비밀번호를 넣은 뒤의 화면은 이 스크립트가 못 연다 — SKILL.md 「V020」의
    손 절차로 본다.
    """
    if not path:
        unverified("V020", "보호글 경로(--protected-path)가 없어 보호글에 Namecard가 주입되는지 재지 못했다. "
                   "보호글이 생기면 그 경로로 다시 돌린다(#130).", base + "/")
        return
    url = protected_url(base, path)
    status, doc, _ = fetch(url)
    if status != 200 or not doc:
        unverified("V020", "보호글을 받지 못했다 (HTTP %s)." % status, url)
        return
    # class **토큰**으로 본다 — `\bprotected\b`는 하이픈을 경계로 읽어 `post-protected-note`에도 맞는다
    if not any("protected" in c.split() for c in
               re.findall(r'<section\b[^>]*?\sclass\s*=\s*["\']([^"\']*)["\']', doc, re.I)):
        unverified("V020", "이 페이지에 보호글 영역(section.protected)이 없다 — 보호가 풀렸거나 스킨이 다르다. "
                   "Namecard 위치를 보호글 조건에서 잰 것이 아니다.", url)
        return
    hits = namecard_ancestry(doc)
    if not hits:
        info("V020 — 보호글(로그아웃)에 Namecard 그릇이 없다 — 덮어쓰기가 닿을 상대가 없어 문제없다. "
             "비밀번호를 넣은 뒤 화면은 따로 본다(SKILL.md 「V020」).")
        return
    outside = [h for h in hits if not any("entry-main" in cls for _, cls in h)]
    if outside:
        trail = " > ".join(tag + "".join("." + c for c in cls) for tag, cls in outside[0]) or "(조상 없음)"
        warn("V020", "보호글에 Namecard가 `.entry-main` 밖에 주입된다(%d개 중 %d개, 조상: %s). TIS005 접두가 "
             "`.entry-main`으로 시작해 덮어쓰기가 하나도 매칭되지 않는다 — 다크에서 #f7f7f7 판으로 뜬다(#59)."
             % (len(hits), len(outside), trail), url)
    else:
        info("V020 — 보호글(로그아웃)의 Namecard %d개가 모두 `.entry-main` 안이다 — 덮어쓰기가 닿는다." % len(hits))


# ────────────────────────────── baseline ──────────────────────────────


def compare_baseline(stats, base):
    if not os.path.exists(BASELINE):
        # --compare를 요청했는데 비교할 것이 없으면 그건 요청 실패다.
        # 미검증 + exit 0으로 넘기면 이 스킬이 경고하는 "조용한 통과"가 된다.
        err("V012", "이전 baseline이 없어 회귀를 비교하지 못했다. 배포 전에 "
            "--save-baseline으로 기준선을 먼저 만들어야 한다.", BASELINE)
        return
    saved = load_json(BASELINE, "baseline")
    if not isinstance(saved, dict):
        # 파싱은 되지만 모양이 다를 수 있다. load_json은 깨진 JSON만 막는다.
        if saved is not None:
            unverified("V015", "baseline의 형식이 예상과 다르다(최상위가 객체가 아니다). "
                       "--save-baseline으로 다시 만들어라.", BASELINE)
        return
    prev_base = saved.get("base")
    if prev_base and prev_base.rstrip("/") != base.rstrip("/"):
        # DECISIONS.md 결정 22 — 두 블로그의 지표를 섞지 않는다. 맞대면 무관한
        # 차이가 전부 "회귀"로 나온다.
        # 미검증으로 넘기면 회귀 검사를 한 번도 안 하고 "오류 0"으로 끝난다.
        # --compare를 요청한 이상, 비교하지 못한 것은 요청 실패다.
        err("V012", "baseline은 %s 에서 찍혔는데 지금 검증 대상은 %s 다. "
            "다른 블로그끼리는 비교하지 않는다 — 회귀 검사를 하지 못했다. "
            "--save-baseline으로 이 블로그의 기준선을 새로 만들어라."
            % (prev_base, base), BASELINE)
        return
    old = saved.get("pages", {})
    for name in sorted(set(old) - set(stats)):
        if name not in ATTEMPTED:
            # 타깃 목록에 아예 없었다. data/posts.json이 없으면 page·category가
            # 만들어지지 않는다. 시도하지 않은 것을 죽었다고 적으면 안 된다.
            unverified("V012", "%s 는 이번 검증 대상에 없었다. data/posts.json이 없거나 "
                       "비어 URL을 만들지 못했을 수 있다." % name, name)
        elif name in UNREACHED:
            # 응답 자체가 없었다. 회귀가 아니라 검증을 못 한 것이다.
            unverified("V012", "%s 가 baseline에는 있는데 이번에는 응답이 없어 비교하지 "
                       "못했다." % name, name)
        else:
            err("V012", "%s 가 baseline에는 있는데 이번에는 정상 응답이 아니었다. "
                "페이지가 죽었다." % name, name)
    for name, cur in sorted(stats.items()):
        prev = old.get(name)
        if not prev:
            info("%s — 이전 baseline에 없던 페이지다." % name)
            continue
        if prev.get("url") and prev["url"] != cur.get("url"):
            # page 대상은 posts[0]이라 새 글을 쓰고 실측을 갱신하면 다른 글이 된다.
            # 다른 문서끼리 링크 수를 비교하면 없는 회귀가 나온다.
            info("%s — baseline과 다른 URL이라 비교를 건너뛴다 (%s → %s). "
                 "새 글이 올라와 표본이 바뀐 것이면 --save-baseline으로 기준선을 다시 찍어라."
                 % (name, prev["url"], cur.get("url")))
            continue
        if cur["h1"] != prev.get("h1"):
            warn("V012", "%s의 h1이 %s → %s로 바뀌었다."
                 % (name, prev.get("h1"), cur["h1"]), name)
        if cur["entryLinks"] < prev.get("entryLinks", 0):
            if name == "page":
                # 글 페이지의 링크 수는 관련글·이전/다음 치환자가 만든다 — 스킨 소관이다.
                err("V012", "%s의 내부링크가 %d → %d로 줄었다. 회귀다."
                    % (name, prev.get("entryLinks", 0), cur["entryLinks"]), name)
            else:
                # 목록 페이지의 링크 수는 글이 몇 편 실렸는가다 — 콘텐츠 소관이다.
                # 글을 지우거나 카테고리를 옮기면 줄어든다. 배포 회귀가 아니다.
                warn("V012", "%s의 내부링크가 %d → %d로 줄었다. 목록 페이지라 글 삭제·"
                     "카테고리 이동으로도 줄 수 있다 — 배포 때문인지 확인하라."
                     % (name, prev.get("entryLinks", 0), cur["entryLinks"]), name)
        lost = set(prev.get("jsonld", [])) - set(cur["jsonld"])
        if lost:
            err("V012", "%s의 구조화 데이터가 사라졌다: %s"
                % (name, ", ".join(sorted(lost))), name)


def save_baseline(base, stats, expected, allow_missing=False):
    """기준선을 남긴다. 단, 불완전한 기준선으로 좋은 기준선을 덮지 않는다.

    verify_page는 HTTP 200일 때만 stats에 쓴다. 네트워크가 한 번 흔들리면
    stats가 비거나 줄어드는데, 그걸 그대로 저장하면 배포 후 --compare가
    순회할 것이 없어 오류 없이 통과한다. 회귀 게이트가 필요한 순간에
    조용히 사라지는 것이라 실패보다 나쁘다."""
    missing = sorted(set(expected) - set(stats))
    if not stats:
        err("V014", "받은 페이지가 하나도 없어 baseline을 저장하지 않았다. "
            "기존 baseline은 그대로 두었다.", BASELINE)
        return
    if missing and not allow_missing:
        # 첫 실행이면 덮어쓸 기준선이 없어 아래 가드가 안 돈다. 그렇다고 경고로
        # 넘기면, 배포 문서의 "exit 1은 정상" 안내와 겹쳐 잘린 게이트가 통과한다.
        err("V014", "%s 를 받지 못해 baseline을 저장하지 않았다. 이대로 두면 이 "
            "페이지들이 배포 후 회귀 감시에서 빠진다 — 원인을 고쳐라. 그 페이지 타입이 "
            "원래 없는 것이면(방명록을 껐다든가) --allow-missing 으로 명시하고 진행하라."
            % ", ".join(missing), BASELINE)
        return

    if os.path.exists(BASELINE):
        saved = load_json(BASELINE, "기존 baseline") or {}
        prev_base = saved.get("base")
        if prev_base and prev_base.rstrip("/") != base.rstrip("/"):
            # DECISIONS.md 결정 22 — 두 블로그의 지표를 섞지 않는다. 다른 블로그 실행이
            # 본 블로그 기준선을 덮으면, 배포 후 --compare가 base 불일치로 미검증 처리되어
            # 오류 없이 통과한다. 회귀 게이트가 조용히 사라지는 경로다.
            err("V014", "기존 baseline은 %s 것인데 지금은 %s 를 찍으려 한다. 덮어쓰면 "
                "그 블로그의 기준선을 잃는다. 저장하지 않았다 — 의도한 것이면 %s 를 지워라."
                % (prev_base, base, os.path.relpath(BASELINE, ROOT)), BASELINE)
            return
        prev = saved.get("pages", {})
        lost = sorted(set(prev) - set(stats))
        if lost:
            # 네트워크 실패든 죽은 페이지든, 덮어쓰면 감시에서 빠지는 것은 같다.
            err("V014", "이번에 받지 못한 페이지가 기존 baseline에는 있다: %s. "
                "덮어쓰면 이 페이지들이 회귀 감시에서 조용히 빠진다. 저장하지 않았다 — "
                "원인을 고치고 다시 실행하거나, 의도한 것이면 %s 를 지워라."
                % (", ".join(lost), os.path.relpath(BASELINE, ROOT)), BASELINE)
            return

    os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
    with open(BASELINE, "w", encoding="utf-8") as f:
        # 어떤 글·카테고리를 봤는지 함께 남긴다. 이게 없으면 다음 실행이 **다른 글**을
        # 골라(글이 하나만 늘어도 바뀐다) 배포 전/후가 서로 다른 대상을 비교하고,
        # 그 차이가 전부 회귀로 보고된다.
        json.dump({"base": base, "pages": stats, "missing": missing,
                   "targets": {"post": _RESOLVED.get("post"),
                               "category": _RESOLVED.get("category")}},
                  f, ensure_ascii=False, indent=1)
    if missing:
        warn("V014", "--allow-missing 으로 %s 를 빼고 저장했다. 이 페이지 타입들은 "
             "배포 후 회귀 감시 대상이 아니다." % ", ".join(missing), BASELINE)
    info("baseline을 %s 에 저장했다 (페이지 %d종)."
         % (os.path.relpath(BASELINE, ROOT), len(stats)))


# ─────────────────────────────── main ───────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True,
                    help="검증할 블로그 루트 URL (예: https://sanggi-jayg.tistory.com)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save-baseline", action="store_true")
    ap.add_argument("--allow-missing", action="store_true",
                    help="일부 페이지 타입이 원래 없을 때(방명록 끔 등) 그것을 빼고 "
                         "baseline을 저장한다. 빠진 것은 회귀 감시에서 제외된다.")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--post-path", default=None,
                    help="검증에 쓸 글의 경로 (예: /entry/제목). 자동 선택이 엉뚱한 글을 "
                         "집거나 못 찾을 때만 쓴다.")
    ap.add_argument("--category", default=None,
                    help="검증에 쓸 상위 카테고리 이름 (예: 경제).")
    ap.add_argument("--protected-path", default=None,
                    help="보호글의 경로 (예: /300). V020이 보호글에 Namecard가 어디 주입되는지 잰다 — "
                         "보호글은 목록에서 찾을 수 없어 자동 선택이 없다. 없으면 V020은 미검증.")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    base_host = urllib.parse.urlparse(base).netloc
    if not base_host:
        sys.stderr.write("--base 가 URL이 아니다: %s\n" % args.base)
        sys.exit(2)

    # --json은 자동화용이다. 헤더 한 줄이 섞이면 파싱이 깨진다.
    if not args.json:
        print("검증 대상: %s\n" % base)

    # 타깃을 먼저 확정한다 — 이 안에서 대상 블로그를 한 번 두드릴 수 있고(다른 블로그일 때만),
    # V013 페이징 검사도 여기서 정해진 카테고리를 그대로 쓴다.
    resolve_targets(base, base_host, cli_post=args.post_path, cli_cat=args.category)
    targets = page_targets(base, base_host)
    stats, home_doc, post_url, post_doc = {}, "", "", ""

    for name, url in targets:
        ATTEMPTED.add(name)
        status, doc, final = fetch(url)
        verify_page(name, url, doc, status, base_host, stats, final=final)
        if name == "index":
            home_doc = doc
        if name == "page":
            post_url = url
            post_doc = doc
        time.sleep(0.4)   # 크롤링이 아니라 검증이다. 8회면 예의를 지키기에 충분하다

    if home_doc:
        pc_skin_css = verify_skin_applied(base, home_doc)
    else:
        # 행이 아예 없으면 통과로 읽힌다. 이 저장소의 규칙은 미검증을 미검증으로 적는 것이다.
        pc_skin_css = None
        unverified("V009", "홈을 받지 못해 스킨 반영 여부를 확인하지 못했다.", base + "/")
    verify_mobile(base, post_url, pc_skin_css=pc_skin_css)
    verify_category_tree(base, home_doc)
    verify_paging_canonical(base)
    if home_doc:
        verify_paging_fixture(base, home_doc)
    else:
        unverified("V018", "홈을 받지 못해 페이징 픽스처를 대조하지 못했다.", base + "/")
    verify_platform_assets(base)
    verify_tistory_sheets(base, home_doc, post_doc)
    if home_doc:
        verify_namecard_bundle(base, home_doc)
    else:
        unverified("V019", "홈을 받지 못해 Namecard 번들을 대조하지 못했다.", base + "/")
    verify_namecard_protected(base, args.protected_path)

    if args.compare:
        compare_baseline(stats, base)
    if args.save_baseline:
        save_baseline(base, stats, [n for n, _ in targets],
                      allow_missing=args.allow_missing)

    if args.json:
        print(json.dumps({"base": base, "pages": stats, "errors": ERRORS,
                          "warnings": WARNINGS, "unverified": UNVERIFIED, "info": INFO},
                         ensure_ascii=False, indent=1))
    else:
        for it in ERRORS:
            print("❌ [%s] %s\n     %s" % (it["code"], it["message"], it["where"]))
        for it in WARNINGS:
            print("⚠️  [%s] %s\n     %s" % (it["code"], it["message"], it["where"]))
        for it in UNVERIFIED:
            print("❔ [%s] %s\n     %s" % (it["code"], it["message"], it["where"]))
        for m in INFO:
            print("ℹ️  %s" % m)
        print("\n오류 %d · 경고 %d · 미검증 %d"
              % (len(ERRORS), len(WARNINGS), len(UNVERIFIED)))

    sys.exit(1 if ERRORS else 0)


if __name__ == "__main__":
    main()
