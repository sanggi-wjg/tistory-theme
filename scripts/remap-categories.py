#!/usr/bin/env python3
"""275편을 새 주제 축 분류로 매핑하고 검증한다."""
import json, collections, sys

TAXONOMY = [
    ("언어 & 런타임", [
        ("Python 기초 & 도구",      [94,120,133,134,201,211,219,220,272]),
        ("Python 성능 & 동시성",    [84,96,97,99,100,101,119,135,136,137,138,139,140,141]),
        ("Python 활용 & 오픈소스",  [85,89,106,117,118,124,175,218]),
        ("JVM (Java · Kotlin)",     [27,28,29,55,69]),
        ("Go",                      [102,103,104,105,107,111,112,113,115,116,126]),
    ]),
    ("백엔드 & 아키텍처", [
        ("Spring",                  [21,54,62,86]),
        ("웹 프레임워크",           [222,224,225,226,227,228,239,240,248,249,242,244]),
        ("분산 시스템 & MSA",       [31,32,33,95,151,152,153,154,155,156,157,158]),
        ("설계 원칙 & 패턴",        [37,53,202,203,204,205,206,207,208,260,261]),
    ]),
    ("데이터", [
        ("MySQL",                   [58,64,66,75,123,179,210,221,253,254,255,256,257,258,259,262,266,267,269]),
        ("데이터베이스 기초",       [263,264,265,268]),
        ("NoSQL & 검색 엔진",       [108,109,110,241,247]),
        ("데이터 파이프라인",       [56,59,60,61,70,71,72,73,90,146,147]),
    ]),
    ("인프라 & 운영", [
        ("쿠버네티스 & 컨테이너",   [7,8,9,11,12,13,68,92]),
        ("로그 & 모니터링",         [176,177,178,180,181,182,183,184,185,186,187,188,189,190,191]),
        ("리눅스 서버 운영",        [197,245,250,270,273,274]),
        ("네트워크",                [10,91,121,251,252,271]),
        ("CI/CD",                   [26,125,150,195,196]),
    ]),
    ("코드 품질", [
        ("Clean Code",              [159,160,161,162,163,164,165,166,167,168,169,170,172,173,174,223]),
        ("리팩토링",                [229,230,231,232,233,234,235,236,237]),
        ("테스트",                  [1,2,3,87,88,93]),
    ]),
    ("웹 & 보안", [
        ("HTTP & 브라우저",         [30,35,36,148,209,212,213,214,215,216]),
        ("보안",                    [0,6,20,22,76,77,78,79,80,81,82,83,149]),
    ]),
    ("AI", [
        ("LLM 활용 & 에이전트",     [14,17,39,49,50,52]),
        ("Langchain",               [38,40,41,42,43,45,46,47,48]),
        ("로컬 모델",               [19,34,44,51,63]),
    ]),
    ("알고리즘 & CS", [
        (None,                      [67,122,127,128,129,130,131,132,142,143,144,145,198,199,200]),
    ]),
    ("개발 도구", [
        ("Git",                     [18,65,74,114,171,192,193,194,246]),
        ("에디터 & 터미널",         [16,24,57,98,238]),
    ]),
    ("기록", [
        ("책",                      [15,23]),
        ("일상",                    [4,5]),
        ("개발자 생각",             [25,217,243]),
    ]),
]

# 배치 근거가 갈릴 수 있어 사용자 확인이 필요한 글
NEEDS_REVIEW = {
    209: "'캐시 (Cache)' — HTTP 캐시인지 애플리케이션 캐시인지에 따라 데이터/NoSQL & 검색 엔진으로 갈 수도",
    7: "OOMKilled 3부작 — Spring Boot 앱 문제이지만 K8s 운영 트러블슈팅으로 판단",
    11: "Argo 전환 3부작 — Spring Batch 설계가 절반이지만 K8s 스케줄링이 주제",
    89: "ChatGPT + streamlit 웹앱 — AI/LLM 활용으로 볼 수도",
    17: "'속도의 병목이 이동하고 있다' — 에세이라 기록/개발자 생각으로 볼 수도",
    260: "토끼책 2편 — 책 요약이라 기록/책으로 볼 수도 (내용은 객체지향 설계)",
    238: "'batch 프로그램으로 host 변경' — 윈도우 배치 스크립트라 인프라/네트워크로 볼 수도",
    250: "fail2ban — 침입 차단 도구라 웹 & 보안/보안으로 볼 수도",
}

posts = json.load(open("data/posts.json"))["posts"]

mapping = {}
dupes = []
for top, subs in TAXONOMY:
    for sub, idxs in subs:
        path = top if sub is None else f"{top}/{sub}"
        for i in idxs:
            if i in mapping:
                dupes.append((i, mapping[i], path))
            mapping[i] = path

missing = [i for i in range(len(posts)) if i not in mapping]
out_of_range = [i for i in mapping if i >= len(posts)]

if dupes or missing or out_of_range:
    print("!! 검증 실패")
    if dupes: print("  중복:", dupes)
    if missing: print("  누락:", [(i, posts[i]["title"]) for i in missing])
    if out_of_range: print("  범위 초과:", out_of_range)
    sys.exit(1)

print(f"검증 통과 — {len(posts)}편 전부 1:1 매핑, 중복 0")

# 신규 트리 편수
print("\n=== 새 카테고리 트리 ===")
grand = 0
for top, subs in TAXONOMY:
    tot = sum(len(idxs) for _, idxs in subs)
    grand += tot
    print(f"{top} ({tot})")
    for sub, idxs in subs:
        if sub: print(f"    {sub} ({len(idxs)})")
print(f"상위 {len(TAXONOMY)}종 · 하위 {sum(1 for _,s in TAXONOMY for sub,_ in s if sub)}종 · 총 {grand}편")

# 구→신 이동 행렬
print("\n=== 구 카테고리 → 신 카테고리 이동 ===")
matrix = collections.defaultdict(collections.Counter)
for i, p in enumerate(posts):
    matrix[p["category"]][mapping[i]] += 1
for old in sorted(matrix, key=lambda k: -sum(matrix[k].values())):
    tot = sum(matrix[old].values())
    dests = matrix[old]
    print(f"{old} ({tot})")
    for new, n in dests.most_common():
        print(f"    → {new} ({n})")

# 대표이미지 없는 글이 몰린 신규 카테고리 (스킨 기본 이미지 영향)
print("\n=== 신규 카테고리별 대표이미지 결손 ===")
thumb = collections.defaultdict(lambda: [0, 0])
for i, p in enumerate(posts):
    t = thumb[mapping[i]]
    t[0] += 1
    if p["hasThumbnail"]: t[1] += 1
for path in sorted(thumb, key=lambda k: -(thumb[k][0] - thumb[k][1])):
    tot, has = thumb[path]
    print(f"{path}: {tot - has}/{tot} 없음 ({has*100//tot}% 보유)")

json.dump(
    {"taxonomy": [{"top": t, "subs": [{"name": s, "count": len(i)} for s, i in ss]} for t, ss in TAXONOMY],
     "posts": [{"index": i, "title": p["title"], "date": p["date"],
                "from": p["category"], "to": mapping[i],
                "hasThumbnail": p["hasThumbnail"],
                "review": NEEDS_REVIEW.get(i)} for i, p in enumerate(posts)]},
    open("data/category-mapping.json", "w"), ensure_ascii=False, indent=2)
print("\ndata/category-mapping.json 기록 완료")
