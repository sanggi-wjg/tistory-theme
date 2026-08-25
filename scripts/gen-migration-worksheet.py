#!/usr/bin/env python3
"""data/category-mapping.json에서 손으로 하는 이동 작업 체크리스트를 만든다.

티스토리 글 관리는 "기존 카테고리로 필터 → 선택 → 이동" 순서라
작업 단위를 신규가 아니라 **기존 카테고리 기준**으로 묶는다.
remap-categories.py로 매핑을 바꾼 뒤 이 스크립트를 다시 돌리면 체크리스트가 따라온다.
"""
import json, collections

m = json.load(open("data/category-mapping.json"))
posts = m["posts"]
tax = m["taxonomy"]

# 기존 카테고리 -> 목적지별 글
src = collections.defaultdict(lambda: collections.defaultdict(list))
for p in posts:
    src[p["from"]][p["to"]].append(p)

whole, split = [], []
for old, dests in src.items():
    total = sum(len(v) for v in dests.values())
    (whole if len(dests) == 1 else split).append((old, dests, total))

whole.sort(key=lambda x: -x[2])
split.sort(key=lambda x: (-len(x[1]), -x[2]))

review = {p["title"]: p["review"] for p in posts if p.get("review")}

L = []
w = L.append

w("# 카테고리 이동 작업 체크리스트")
w("")
w("티스토리 관리 화면을 열어 두고 이 파일을 보면서 진행한다.")
w("설계 근거와 왜 이렇게 나눴는지는 [`category-taxonomy.md`](./category-taxonomy.md)에 있다 — **이 파일은 손으로 하는 작업만** 담는다.")
w("")
w(f"**총 {len(posts)}편** · 통째 이동 {sum(x[2] for x in whole)}편 / 쪼개서 이동 {sum(x[2] for x in split)}편")
w("")
w("---")
w("")
w("## 0단계 — 시작 전")
w("")
w("- [ ] **블로그 백업을 받는다** — 관리 → 데이터 관리 → 백업. 카테고리 관리 화면은 되돌리기가 없다")
w("- [ ] 관리 → 글 관리 화면을 연다 (카테고리 필터와 일괄 선택이 여기 있다)")
w("")
w("> **기존 카테고리를 고치지 않는다.** 새로 만들고, 글을 옮기고, 빈 껍데기를 지우는 순서다.")
w("> 중간에 멈춰도 글은 전부 어딘가에 남아 있다.")
w("")
w("---")
w("")
w("## 1단계 — 새 카테고리 만들기")
w("")
w("관리 → 카테고리 관리에서 **위에서부터 순서대로** 만든다. 만드는 순서가 곧 노출 순서라 나중에 정렬할 일이 줄어든다.")
w("")
w("```")
for t in tax:
    subs = [s for s in t["subs"] if s["name"]]
    w(f'{t["order"]:>2}. {t["top"]}')
    for s in subs:
        w(f'      └ {s["name"]}')
w("```")
w("")
w("- [ ] 상위 11종을 만들었다")
w("- [ ] 하위 26종을 만들었다")
w("")
w("> **이름 주의** — `CI·CD`의 가운뎃점은 `·`(U+00B7)다. `&`는 어디에도 쓰지 않는다.")
w("")
w("---")
w("")
w("## 2단계 — 통째로 옮기기")
w("")
w("한 카테고리의 글이 전부 같은 곳으로 간다. **글 관리 → 카테고리 필터 → 전체 선택 → 카테고리 이동** 한 번이면 끝난다.")
w("")
w("> ⚠️ **하위부터 비우고 상위 직속을 마지막에 한다.** 필터에서 상위를 고르면 하위 글까지 딸려 올 수 있다.")
w("> 상위 직속 글이 있는 것은 `IT`(35) · `Go`(11) · `Kotlin & Java`(5) · `Infrastructure`(2) · `일상`(2) · `책책책 책을 읽읍시다`(2)다.")
w("> 전체 선택 전에 **목록에 뜬 편수가 표의 편수와 같은지** 확인한다.")
w("")
w("| ✓ | 기존 카테고리 | 편수 | 옮길 곳 |")
w("|---|---|---:|---|")
for old, dests, total in whole:
    dest = list(dests.keys())[0]
    w(f"| [ ] | `{old}` | {total} | **{dest}** |")
w("")
w(f"여기까지 {sum(x[2] for x in whole)}편. 전체의 {sum(x[2] for x in whole)*100//len(posts)}%가 이 단계에서 끝난다.")
w("")
w("---")
w("")
w("## 3단계 — 쪼개서 옮기기")
w("")
w("여러 곳으로 갈린다. 카테고리 필터로 거른 뒤 **아래 목록을 보며 골라서** 이동한다.")
w("제목은 관리 화면에 보이는 그대로다. 목적지가 같은 것끼리 묶어 놨으니 한 목적지씩 처리하면 된다.")
w("")

for old, dests, total in split:
    w(f"### `{old}` — {total}편 → {len(dests)}곳")
    w("")
    for dest, items in sorted(dests.items(), key=lambda kv: -len(kv[1])):
        w(f"**→ {dest}** ({len(items)}편)")
        w("")
        for p in sorted(items, key=lambda p: p["date"], reverse=True):
            note = f"  ⚠️ {p['review']}" if p.get("review") else ""
            w(f"- [ ] {p['date']}  {p['title']}{note}")
        w("")
    w("")

w("---")
w("")
w("## 4단계 — 정렬 순서 잡기")
w("")
w("카테고리 관리에서 드래그로 1단계 목록 순서와 같게 맞춘다. 1단계에서 순서대로 만들었으면 확인만 하면 된다.")
w("")
w("**활성 주력 → 대형 아카이브 → 잡문** 순이다. 이걸 빠뜨리면 개편 효과의 절반이 날아간다 — 사이드바 맨 위가 3~5년 전 연재물로 채워진다.")
w("")
w("- [ ] 상위 11종 순서 확인")
w("- [ ] 각 상위 안의 하위 순서 확인")
w("")
w("---")
w("")
w("## 5단계 — 뒷정리")
w("")
w("- [ ] **기존 카테고리를 전부 지운다** — 여기까지 왔으면 기존 트리 47줄이 모두 0편이다. `Design Pattern`처럼 처음부터 비어 있던 것도 함께 사라진다")
w("- [ ] **비공개 글 3편**(`비공개용`)을 확인해 배치하거나 비공개인 채로 둔다 — 크롤링에 잡히지 않아 이 목록에 없다")
w("- [ ] 블로그를 열어 사이드바 카테고리 트리를 눈으로 확인한다")
w("")
w("---")
w("")
w("## 6단계 — 저장소에 반영")
w("")
w("```bash")
w("/blog-census          # data/categories.json · posts.json 재생성")
w("```")
w("")
w("- [ ] `DECISIONS.md` §3 카테고리 절을 새 값으로 다시 쓴다 (⚠️ 개편 대기 표시 제거)")
w("- [ ] `DECISIONS.md` 미결 8을 완료 처리한다")
w("- [ ] `DESIGN.md` §6.2 `data-cat` 접두 선택자 값을 새 상위 11종으로 교체한다")
w("- [ ] 미결 6(기본 이미지 11장 도안) 착수 — 이제 카테고리가 확정됐다")
w("")
w("---")
w("")
w("## 작업 중 판단이 필요한 글")
w("")
w("제목만으로 분류해서 원문을 봐야 확정되는 것들이다. 위 목록에서 ⚠️ 로 표시해 뒀다.")
w("**옮기기 전에 글을 한 번 열어 보고**, 다르게 판단되면 그쪽으로 옮긴다.")
w("")
w("| 글 | 넣어 둔 곳 | 이럴 땐 이쪽으로 |")
w("|---|---|---|")
rows = [
    ("캐시 (Cache)", "웹·보안/HTTP", "애플리케이션 캐시 얘기면 → 데이터/NoSQL·검색"),
    ("OOMKilled 추적기 3부작", "인프라/쿠버네티스", "Spring 설정 얘기가 중심이면 → 백엔드/Kotlin·Spring"),
    ("Argo Workflows 전환 3부작", "인프라/쿠버네티스", "Spring Batch 설계가 중심이면 → 백엔드/Kotlin·Spring"),
    ("JVM GC 3부작", "백엔드/Kotlin·Spring", "순수 런타임 얘기면 → `JVM` 상위를 따로 만들 수도"),
    ("ChatGPT를 이용한 간단한 Web App", "Python/라이브러리", "AI 활용이 중심이면 → AI/LLM 활용"),
    ("속도의 병목이 이동하고 있다", "AI/LLM 활용", "에세이에 가까우면 → 기록"),
    ("토끼책 2편 (객체지향의 사실과 오해)", "백엔드/설계 원칙", "독서 기록으로 보고 싶으면 → 기록"),
    ("batch 프로그램으로 host 변경하기", "개발 도구/개발 환경", "hosts 파일이 주제면 → 인프라/네트워크"),
    ("fail2ban", "인프라/리눅스", "침입 차단이 주제면 → 웹·보안/보안"),
]
for a, b, c in rows:
    w(f"| {a} | {b} | {c} |")
w("")
w("**바꾸기로 했다면** `scripts/remap-categories.py`의 해당 인덱스를 옮기고 다시 돌린다 — 매핑과 문서가 같이 갱신된다.")
w("")

open("docs/category-migration-worksheet.md", "w", encoding="utf-8").write("\n".join(L) + "\n")

print(f"통째 이동 {len(whole)}건 / {sum(x[2] for x in whole)}편")
print(f"쪼개서 이동 {len(split)}건 / {sum(x[2] for x in split)}편")
print(f"합계 {sum(x[2] for x in whole)+sum(x[2] for x in split)}편")
