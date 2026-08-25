#!/usr/bin/env python3
"""275편을 새 카테고리 트리에 매핑하고 검증한다.

TAXONOMY의 순서가 곧 티스토리 카테고리 관리 화면의 정렬 순서다.
규칙은 docs/category-taxonomy.md §4 — **블로그 주력 순**이고, 1군 안의 순서는
편집 판단이라 기계적으로 재현되지 않는다. 새 카테고리는 먼저 몇 군인지 정한다.

    1군  블로그의 얼굴   인프라 · Kotlin·Java · 아키텍처 · 데이터베이스 · 네트워크 · 보안
    2군  횡단 관심사     AI · 코드 품질
    3군  언어 아카이브   Python · Go
    4군  주변            알고리즘 · 개발 도구
    5군  잡문            기록

이름 규칙 (docs/category-taxonomy.md §3.3) — 아래 검증이 셋 다 검사한다.
  · `&`를 쓰지 않는다          URL에서 %26, RSS·OG에서 이스케이프
  · 하위에 `/`를 쓰지 않는다   상위/하위 경로 표기와 충돌 (CI/CD → CI·CD)
  · 하위에서 상위 이름을 반복하지 않는다   `데이터베이스/DB 이론` 같은 축약형 포함
"""
import json, collections, sys

# (상위, [(하위 or None, [글 인덱스])])  — 목록 순서 = 사이드바 노출 순서
TAXONOMY = [
    # ── 1군: 블로그의 얼굴 ───────────────────────────────────────
    ("인프라", [
        ("쿠버네티스",        [11,12,13,68,92]),
        ("모니터링",          [176,177,178,180,181,182,183,184,185,186,187,188,189,190,191]),
        ("데이터 파이프라인", [56,59,60,61,70,71,72,73,90,146,147]),
        ("리눅스",            [197,245,250,270,273,274,242,244]),
        ("CI·CD",             [26,125,150,195,196]),
    ]),
    ("Kotlin·Java", [
        (None,                [7,8,9, 21,54,62,86, 27,28,29,55,69]),
    ]),
    ("아키텍처", [
        ("분산 시스템",       [31,32,33,95,151,152,153,154,155,156,157,158, 209]),
        ("원칙",              [37,53,202,203,204,205,206,207,208,260,261]),
    ]),
    ("데이터베이스", [
        ("MySQL",             [58,64,66,75,123,179,210,221,253,254,255,256,257,258,259,262,266,267,269]),
        ("NoSQL·검색",        [108,109,110,241,247]),
        ("이론",              [263,264,265,268]),
    ]),
    ("네트워크", [
        (None,                [30,35,36,148,212,213,214,215,216, 10,91,121,251,252,271]),
    ]),
    ("보안", [
        (None,                [0,6,20,22,76,77,78,79,80,81,82,83,149]),
    ]),
    # ── 2군: 횡단 관심사 ─────────────────────────────────────────
    ("AI", [
        (None,                [14,39,49,50,52, 38,40,41,42,43,45,46,47,48, 19,34,44,51,63]),
    ]),
    ("코드 품질", [
        ("Clean Code",        [159,160,161,162,163,164,165,166,167,168,169,170,172,173,174,223]),
        ("리팩토링",          [229,230,231,232,233,234,235,236,237]),
        ("테스트",            [1,2,3,87,88,93]),
    ]),
    # ── 3군: 언어 아카이브 ───────────────────────────────────────
    ("Python", [
        ("성능과 동시성",     [84,96,97,99,100,101,119,135,136,137,138,139,140,141]),
        ("Django·Flask",      [222,224,225,226,227,228,239,240,248,249]),
        ("기초",              [94,120,133,134,201,211,219,220,272]),
        ("라이브러리",        [85,89,106,117,118,124,175,218]),
    ]),
    ("Go", [
        (None,                [102,103,104,105,107,111,112,113,115,116,126]),
    ]),
    # ── 4군: 주변 ────────────────────────────────────────────────
    ("알고리즘", [
        (None,                [67,122,127,128,129,130,131,132,142,143,144,145,198,199,200]),
    ]),
    ("개발 도구", [
        ("Git",               [18,65,74,114,171,192,193,194,246]),
        ("에디터·터미널",     [16,24,57,98,238]),
    ]),
    # ── 5군: 잡문 ────────────────────────────────────────────────
    ("기록", [
        (None,                [4,5,15,17,23,25,217,243]),
    ]),
]

# 상위 이름의 축약형 — 하위 이름 반복 검사에 쓴다 (자동으로는 못 잡는다)
ALIASES = {
    "데이터베이스": ["DB"],
    "쿠버네티스":   ["K8s", "k8s"],
    "인프라":       ["Infra"],
}

# 원문을 읽어 확정한 것 (2026-08-25). 제목만으로는 갈렸던 글들이다.
VERIFIED = {
    7:   "원문 확인 — 3편이 90% HikariCP 설정이고 해결도 Spring 쪽이라 쿠버네티스에서 옮겨왔다",
    11:  "원문 확인 — 85%가 Argo/K8s YAML이고 Spring 코드는 없다. 쿠버네티스가 맞다",
    56:  "원문 확인 — 90%가 Spring Kafka 클라이언트 구성이고 MySQL 설정은 없다. MySQL이 아니라 파이프라인이 맞다",
    89:  "원문 확인 — streamlit UI 사용법이 중심이고 ChatGPT는 토큰 입력만. AI가 아니라 라이브러리가 맞다",
    209: "원문 확인 — HTTP 캐시도 Redis도 아닌 일반 컴퓨팅 개념(RAM·스토리지 계층)이라 네트워크에서 옮겨왔다",
    17:  "원문 확인 — 코드 없는 1인칭 에세이라 AI에서 옮겨왔다",
    238: "원문 확인 — 윈도우 .bat으로 hosts를 바꿔 로컬 환경을 전환한다. 네트워크가 아니다",
    242: "원문 확인 — 90%가 yum·systemctl 설치 명령이고 Codeigniter 내용은 없다. 리눅스가 맞다",
    250: "원문 확인 — 설치·설정 가이드이고 보안 개념 설명은 없다. 리눅스가 맞다",
    260: "원문 확인 — 감상이 아니라 상태·행동·식별자를 정리한 개념 노트다. 원칙이 맞다",
}

# 원문을 읽어도 남은 것
NEEDS_REVIEW = {
    213: "원문은 렌더링 엔진 내부(파싱·DOM·렌더트리)가 중심이고 네트워크는 항목 하나다. "
         "이 블로그에 프론트엔드 카테고리가 없어 갈 곳이 없다. 1편을 위해 카테고리를 만들 수는 없어 네트워크에 둔다",
}

posts = json.load(open("data/posts.json"))["posts"]

# ── 검증 ──────────────────────────────────────────────────────────
mapping, order, dupes, name_err = {}, [], [], []
for top, subs in TAXONOMY:
    tokens = [top] + top.split() + ALIASES.get(top, [])
    for sub, idxs in subs:
        path = top if sub is None else f"{top}/{sub}"
        order.append(path)
        if "&" in path:
            name_err.append(f"{path} — `&` 금지")
        if sub and "/" in sub:
            name_err.append(f"{path} — 하위에 `/` 금지")
        if sub:
            hit = [t for t in tokens if t in sub]
            if hit:
                name_err.append(f"{path} — 하위가 상위 이름을 반복한다 ({', '.join(hit)})")
        for i in idxs:
            if i in mapping:
                dupes.append((i, mapping[i], path))
            mapping[i] = path

missing = [i for i in range(len(posts)) if i not in mapping]
oob = [i for i in mapping if i >= len(posts)]

if dupes or missing or oob or name_err:
    print("!! 검증 실패")
    if dupes:    print("  중복:", dupes)
    if missing:  print("  누락:", [(i, posts[i]["title"]) for i in missing])
    if oob:      print("  범위 초과:", oob)
    for e in name_err: print("  이름 규칙:", e)
    sys.exit(1)

print(f"검증 통과 — {len(posts)}편 전부 1:1 매핑, 중복 0, 이름 규칙 위반 0")

# ── 새 트리 ───────────────────────────────────────────────────────
print("\n=== 새 카테고리 트리 (표시 순서대로) ===")
for n, (top, subs) in enumerate(TAXONOMY, 1):
    tot = sum(len(i) for _, i in subs)
    print(f"{n:>2}. {top} ({tot})")
    for sub, idxs in subs:
        if sub: print(f"      {sub} ({len(idxs)})")
n_sub = sum(1 for _, s in TAXONOMY for sub, _ in s if sub)
print(f"\n상위 {len(TAXONOMY)}종 · 하위 {n_sub}종 · 사이드바 {len(TAXONOMY) + n_sub}줄 · 총 {len(posts)}편")

# ── 활성도 (정렬 규칙의 근거는 아니지만 도안 우선순위·분할 판단에 쓴다) ──
print("\n=== 카테고리 활성도 ===")
print(f"{'카테고리':28} {'총':>4} {'2025~26':>8} {'최신 글':>11}  {'한날 몰림':>12}")
print("-" * 72)
for path in order:
    items = [posts[i] for i in range(len(posts)) if mapping[i] == path]
    recent = sum(1 for p in items if int(p["date"][:4]) >= 2025)
    last = max(p["date"] for p in items)
    burst = collections.Counter(p["date"] for p in items).most_common(1)[0]
    state = "활성" if recent else ("정체" if last >= "2024" else "아카이브")
    print(f"{path:28} {len(items):>4} {recent:>8} {last:>11}  {burst[1]:>3}편/{burst[0]}  {state}")

# ── 구 → 신 이동 ──────────────────────────────────────────────────
print("\n=== 구 카테고리 → 신 카테고리 이동 ===")
matrix = collections.defaultdict(collections.Counter)
for i, p in enumerate(posts):
    matrix[p["category"]][mapping[i]] += 1
for old in sorted(matrix, key=lambda k: -sum(matrix[k].values())):
    print(f"{old} ({sum(matrix[old].values())})")
    for new, n in matrix[old].most_common():
        print(f"    → {new} ({n})")

# ── 대표이미지 결손 (스킨 기본 이미지 설계용) ─────────────────────
print("\n=== 신규 카테고리별 대표이미지 결손 ===")
thumb = collections.defaultdict(lambda: [0, 0])
for i, p in enumerate(posts):
    t = thumb[mapping[i]]
    t[0] += 1
    if p["hasThumbnail"]: t[1] += 1
for path in sorted(thumb, key=lambda k: -(thumb[k][0] - thumb[k][1])):
    tot, has = thumb[path]
    print(f"{path}: {tot - has}/{tot} 없음 ({has * 100 // tot}% 보유)")

json.dump(
    {"note": "TAXONOMY 순서 = 티스토리 카테고리 정렬 순서 (블로그 주력 순, docs/category-taxonomy.md §4)",
     "taxonomy": [{"order": n, "top": t,
                   "subs": [{"name": s, "count": len(i)} for s, i in ss]}
                  for n, (t, ss) in enumerate(TAXONOMY, 1)],
     "posts": [{"index": i, "title": p["title"], "date": p["date"],
                "from": p["category"], "to": mapping[i],
                "hasThumbnail": p["hasThumbnail"],
                "review": NEEDS_REVIEW.get(i),
                "verified": VERIFIED.get(i)} for i, p in enumerate(posts)]},
    open("data/category-mapping.json", "w"), ensure_ascii=False, indent=2)
print("\ndata/category-mapping.json 기록 완료")
