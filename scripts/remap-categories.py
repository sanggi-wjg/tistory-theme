#!/usr/bin/env python3
"""275편을 새 카테고리 트리에 매핑하고 검증한다.

TAXONOMY의 순서가 곧 티스토리 카테고리 관리 화면의 정렬 순서다.
활성 주력 → 대형 아카이브 → 잡문 순으로 놓았다. 근거는 아래 활성도 집계.

이름에 `&`를 쓰지 않는다 — URL에서 %26이 되고 RSS·OG에서 이스케이프가 필요하다.
하위 이름에 `/`를 쓰지 않는다 — 상위/하위 경로 표기와 충돌한다 (CI/CD → CI·CD).
"""
import json, collections, sys

# (상위, [(하위 or None, [글 인덱스])])  — 목록 순서 = 사이드바 노출 순서
TAXONOMY = [
    ("인프라", [
        ("쿠버네티스",       [7,8,9,11,12,13,68,92]),
        ("모니터링",         [176,177,178,180,181,182,183,184,185,186,187,188,189,190,191]),
        ("리눅스",           [197,245,250,270,273,274]),
        ("네트워크",         [10,91,121,251,252,271]),
        ("CI·CD",            [26,125,150,195,196]),
    ]),
    ("백엔드", [
        ("Kotlin·Spring",    [21,54,62,86,27,28,29,55,69]),
        ("웹 프레임워크",    [222,224,225,226,227,228,239,240,248,249,242,244]),
        ("분산 시스템",      [31,32,33,95,151,152,153,154,155,156,157,158]),
        ("설계 원칙",        [37,53,202,203,204,205,206,207,208,260,261]),
    ]),
    ("데이터", [
        ("MySQL",            [58,64,66,75,123,179,210,221,253,254,255,256,257,258,259,262,266,267,269]),
        ("DB 이론",          [263,264,265,268]),
        ("NoSQL·검색",       [108,109,110,241,247]),
        ("데이터 파이프라인",[56,59,60,61,70,71,72,73,90,146,147]),
    ]),
    ("웹·보안", [
        ("HTTP",             [30,35,36,148,209,212,213,214,215,216]),
        ("보안",             [0,6,20,22,76,77,78,79,80,81,82,83,149]),
    ]),
    ("AI", [
        ("LLM 활용",         [14,17,39,49,50,52]),
        ("Langchain",        [38,40,41,42,43,45,46,47,48]),
        ("로컬 모델",        [19,34,44,51,63]),
    ]),
    ("Python", [
        ("기초",             [94,120,133,134,201,211,219,220,272]),
        ("성능과 동시성",    [84,96,97,99,100,101,119,135,136,137,138,139,140,141]),
        ("라이브러리",       [85,89,106,117,118,124,175,218]),
    ]),
    ("코드 품질", [
        ("Clean Code",       [159,160,161,162,163,164,165,166,167,168,169,170,172,173,174,223]),
        ("리팩토링",         [229,230,231,232,233,234,235,236,237]),
        ("테스트",           [1,2,3,87,88,93]),
    ]),
    ("개발 도구", [
        ("Git",              [18,65,74,114,171,192,193,194,246]),
        ("개발 환경",        [16,24,57,98,238]),
    ]),
    ("알고리즘", [
        (None,               [67,122,127,128,129,130,131,132,142,143,144,145,198,199,200]),
    ]),
    ("Go", [
        (None,               [102,103,104,105,107,111,112,113,115,116,126]),
    ]),
    ("기록", [
        (None,               [4,5,15,23,25,217,243]),
    ]),
]

# 배치 근거가 갈릴 수 있어 원문 확인이 필요한 글
NEEDS_REVIEW = {
    209: "'캐시 (Cache)' — HTTP 캐시인지 애플리케이션 캐시인지에 따라 데이터/NoSQL·검색으로 갈 수도",
    7:   "OOMKilled 3부작 — Spring Boot 앱 문제이지만 K8s 운영 트러블슈팅으로 판단",
    11:  "Argo 전환 3부작 — Spring Batch 설계가 절반이지만 K8s 스케줄링이 주제",
    27:  "JVM GC 3부작 — 언어 런타임이지만 Spring Boot 부하 테스트가 붙어 백엔드로 판단",
    89:  "ChatGPT + streamlit 웹앱 — AI/LLM 활용으로 볼 수도",
    17:  "'속도의 병목이 이동하고 있다' — 에세이라 기록으로 볼 수도",
    260: "토끼책 2편 — 책 요약이라 기록으로 볼 수도 (내용은 객체지향 설계)",
    238: "'batch 프로그램으로 host 변경' — hosts 파일이 주제면 인프라/네트워크로",
    250: "fail2ban — 침입 차단 도구라 웹·보안/보안으로 볼 수도",
}

posts = json.load(open("data/posts.json"))["posts"]

# ── 검증 ──────────────────────────────────────────────────────────
mapping, order, dupes = {}, [], []
for top, subs in TAXONOMY:
    for sub, idxs in subs:
        path = top if sub is None else f"{top}/{sub}"
        order.append(path)
        for i in idxs:
            if i in mapping:
                dupes.append((i, mapping[i], path))
            mapping[i] = path

bad_name = [p for p in order if "&" in p or p.count("/") > 1]
missing = [i for i in range(len(posts)) if i not in mapping]
oob = [i for i in mapping if i >= len(posts)]

if dupes or missing or oob or bad_name:
    print("!! 검증 실패")
    if dupes:    print("  중복:", dupes)
    if missing:  print("  누락:", [(i, posts[i]["title"]) for i in missing])
    if oob:      print("  범위 초과:", oob)
    if bad_name: print("  이름 규칙 위반(& 또는 / 포함):", bad_name)
    sys.exit(1)

print(f"검증 통과 — {len(posts)}편 전부 1:1 매핑, 중복 0, 이름 규칙 위반 0")

# ── 새 트리 ───────────────────────────────────────────────────────
print("\n=== 새 카테고리 트리 (표시 순서대로) ===")
for n, (top, subs) in enumerate(TAXONOMY, 1):
    tot = sum(len(i) for _, i in subs)
    print(f"{n:>2}. {top} ({tot})")
    for sub, idxs in subs:
        if sub: print(f"      {sub} ({len(idxs)})")
print(f"\n상위 {len(TAXONOMY)}종 · 하위 {sum(1 for _,s in TAXONOMY for sub,_ in s if sub)}종 · 총 {len(posts)}편")

# ── 활성도: 정렬 순서의 근거 ──────────────────────────────────────
print("\n=== 카테고리 활성도 (정렬 순서의 근거) ===")
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
    {"note": "TAXONOMY 순서 = 티스토리 카테고리 정렬 순서",
     "taxonomy": [{"order": n, "top": t,
                   "subs": [{"name": s, "count": len(i)} for s, i in ss]}
                  for n, (t, ss) in enumerate(TAXONOMY, 1)],
     "posts": [{"index": i, "title": p["title"], "date": p["date"],
                "from": p["category"], "to": mapping[i],
                "hasThumbnail": p["hasThumbnail"],
                "review": NEEDS_REVIEW.get(i)} for i, p in enumerate(posts)]},
    open("data/category-mapping.json", "w"), ensure_ascii=False, indent=2)
print("\ndata/category-mapping.json 기록 완료")
