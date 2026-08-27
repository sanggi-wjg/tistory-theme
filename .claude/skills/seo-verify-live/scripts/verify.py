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

    skin-preview는 10개를 렌더하지만 그중 page_toc·tag_cloud는 **같은 URL 타입의 다른 상태**다
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

    atom-one-light(결정 32의 두 번째 전제)은 2026-08-27 실측에서 글 페이지 소스 HTML에
    **없었다.** 있든 없든 info로 남긴다 — 프리뷰가 그 시트를 우리 뒤에 싣는 것은 더 엄격한
    조건이라 해롭지 않지만, 전제가 흔들린 것은 적어 둬야 다음 사람이 안다.
    """
    want = preview_sheet_url("TISTORY_CONTENT_CSS")
    if not want:
        unverified("V017", "render.py에서 TISTORY_CONTENT_CSS를 읽지 못했다 — 상수 모양이 바뀌었나.", RENDER_PY)
        return
    live = None
    for tag in re.findall(r"<link\b[^>]*>", head_of(home_doc or ""), re.I):
        h = href_of(tag)
        if h and "/static/style/content.css" in h:
            live = urllib.parse.urljoin(base + "/", h)
            break
    if not live:
        unverified("V017", "라이브 홈 head에서 티스토리 content.css 링크를 찾지 못했다. "
                   "티스토리가 시트 경로를 바꿨다면 render.py 상수도 같이 봐야 한다.", base + "/")
    elif live == want:
        info("V017 — 프리뷰가 싣는 티스토리 content.css가 라이브와 같은 URL이다.")
    else:
        s1, b1, _ = fetch(live)
        s2, b2, _ = fetch(want)
        if s1 == 200 and s2 == 200 and b1 == b2:
            info("V017 — 티스토리 content.css 해시가 바뀌었지만 내용은 같다(%d bytes). render.py "
                 "TISTORY_CONTENT_CSS를 %s 로 갱신해 두라." % (len(b1.encode("utf-8")), live))
        else:
            warn("V017", "프리뷰가 싣는 티스토리 content.css가 라이브와 다르다 — render.py: %s (HTTP %s) / "
                 "라이브: %s (HTTP %s). 프리뷰의 특이도 싸움이 낡은 상대와 벌어진다. 상수를 갱신하고 "
                 "data/tistory-hardcoded-colors.json을 새 시트와 다시 대조하라(TIS001~004)."
                 % (want, s2, live, s1), RENDER_PY)
    if post_doc:
        if re.search(r"highlight\.js/[\d.]+/styles/atom-one-light", post_doc):
            info("V017 — 글 페이지 소스 HTML에 티스토리의 atom-one-light 링크가 있다(결정 32의 전제 유효).")
        else:
            info("V017 — 글 페이지 소스 HTML에 atom-one-light 링크가 **없다**(2026-08-27 실측과 같다). "
                 "결정 32·HLJS001의 전제(티스토리가 우리 뒤에 싣는다)는 런타임 주입이거나 사라진 것일 수 "
                 "있다. 프리뷰가 그 시트를 우리 뒤에 싣는 것은 더 엄격한 조건이라 해롭지 않다.")


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
    verify_platform_assets(base)
    verify_tistory_sheets(base, home_doc, post_doc)

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
