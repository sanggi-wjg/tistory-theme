# 카테고리 재분류 계획

**대상** `sanggi-jayg.tistory.com` 공개 글 275편 (2026-08-24 크롤링 기준)
**상태** 제안 — 티스토리 적용 전
**전체 매핑** [`data/category-mapping.json`](../data/category-mapping.json) — 275편 1:1, 중복·누락 0으로 검증됨
**재현** `python3 scripts/remap-categories.py` — 매핑 정의이자 검증기다. 배치를 바꾸려면 이 파일을 고친다
**실제 작업** [`category-migration-worksheet.md`](./category-migration-worksheet.md) — 티스토리 화면에서 체크하며 진행하는 목록. `python3 scripts/gen-migration-worksheet.py`로 다시 만든다

---

## 1. 무엇을 위한 분류인가

블로그 카테고리는 아카이브 정리가 아니다. 세 가지를 해야 한다.

1. 처음 온 사람이 **3초 안에 여기가 뭐 하는 곳인지** 안다
2. 글 하나를 검색으로 읽고 온 사람이 **"비슷한 걸 더"** 를 누를 수 있다
3. 글쓴이가 새 글을 쓸 때 **넣을 곳이 바로 떠오른다**

275편을 고르게 나누는 것은 목적이 아니다. 실제로 고르게 나누면 ②만 잘하고 ①③을 놓친다 — 아래 §2가 그 증거다.

---

## 2. 지금 구조의 문제

현재 상위 11종 / 하위 36종.

### 2.1 `IT`가 미분류 통이다

122편(45%)이 `IT` 아래 있고, 그 직속 35편은 서로 관계가 없다 — 보안 사고 대응, Jenkins 설치, SOLID 원칙, IntelliJ 팁, 객체지향 책 정리가 한 목록에 섞인다. 목록 페이지가 정보를 주지 못한다.

### 2.2 분류 축이 세 개 섞여 있다

같은 레벨에 언어(`Python` `Go` `Kotlin & Java` `PHP`), 기술 영역(`Infrastructure` `Database` `Search Engine`), 주제(`Clean Code` `리팩토링` `알고리즘`)가 공존한다. "JPA 락"은 언어(Kotlin)인가 영역(Database)인가 — 답이 없다.

### 2.3 최신 글이 갈 곳이 없다

2025~2026년 글은 운영 트러블슈팅과 전환 회고(OOMKilled 추적기, AccessKey 유출 대응, Argo Workflows 전환, AI 에이전트 테스트 인프라)인데, 축이 "언어별 문법 정리"에 맞춰져 있어 `IT` 직속으로 밀려났다.

### 2.4 큰 카테고리일수록 죽어 있다

이게 가장 중요하다. 카테고리 크기는 **과거**가 정하는데, 블로그가 보여줘야 하는 것은 **현재**다.

| 카테고리 | 총 편수 | 2025~26 | 최신 글 | 한날 몰림 |
|---|---:|---:|---|---|
| 리팩토링 | 9 | 0 | 2019.10.25 | **9편이 2019.10.25 하루** |
| Clean Code | 16 | 0 | 2021.09.06 | **12편이 2021.09.06 하루** |
| Fluentd | 11 | 0 | 2021.08.12 | **9편이 2021.05.11 하루** |
| MySQL | 21 | 0 | 2024.02.15 | 11편이 2019.10.22 하루 |

하루 만에 몰아 쓴 **연재 시리즈**가 사이드바에서 영구히 큰 자리를 차지한다. 전체로 보면 **하위 32개 중 16개가 최근 2년 0편**이다.

**결론: 죽은 카테고리는 구조가 아니라 순서로 다룬다.** 분류를 뒤틀어 활성도를 반영하려 하면 분류가 망가진다. 티스토리는 카테고리 정렬 순서를 지정할 수 있으므로 §4를 그렇게 쓴다.

### 2.5 잔가지가 많다

1편짜리 하위 7개(`Docker` `Mac` `수학` `ElasticSearch` `Lucene Solr` `Laravel` `Codeigniter`)와 **0편짜리 `Design Pattern`**. 사이드바 트리가 47줄인데 그중 상당수가 클릭할 이유가 없다.

> 크롤링은 글이 있는 하위 30종만 잡는다. DECISIONS.md §3의 하위 36종과 차이 나는 만큼(`Design Pattern` 포함 6종 안팎)은 **글이 0편인 카테고리**다. 관리 화면에서 직접 확인해 함께 정리한다.

---

## 3. 새 카테고리 트리

**상위 11종 · 하위 26종 · 사이드바 37줄** (현재 47줄). 번호가 곧 정렬 순서다 — 근거는 §4.

| # | 상위 | 편수 | 하위 |
|---:|---|---:|---|
| 1 | **인프라** | 40 | 쿠버네티스 (8) · 모니터링 (15) · 리눅스 (6) · 네트워크 (6) · CI·CD (5) |
| 2 | **백엔드** | 44 | Kotlin·Spring (9) · 웹 프레임워크 (12) · 분산 시스템 (12) · 설계 원칙 (11) |
| 3 | **데이터** | 39 | MySQL (19) · DB 이론 (4) · NoSQL·검색 (5) · 데이터 파이프라인 (11) |
| 4 | **웹·보안** | 23 | HTTP (10) · 보안 (13) |
| 5 | **AI** | 20 | LLM 활용 (6) · Langchain (9) · 로컬 모델 (5) |
| 6 | **Python** | 31 | 기초 (9) · 성능과 동시성 (14) · 라이브러리 (8) |
| 7 | **코드 품질** | 31 | Clean Code (16) · 리팩토링 (9) · 테스트 (6) |
| 8 | **개발 도구** | 14 | Git (9) · 개발 환경 (5) |
| 9 | **알고리즘** | 15 | — |
| 10 | **Go** | 11 | — |
| 11 | **기록** | 7 | — |

최대 카테고리가 전체의 16%다 (현재는 `IT` 45%).

### 3.1 축은 주제로 통일하되, 언어는 예외로 남긴다

**이 예외를 숨기지 않는다.** `Python`과 `Go`는 언어 축이고 나머지는 주제 축이다. §2.2에서 지적한 "축 혼재"의 일부를 의도적으로 남긴 것이다.

이유는 블로그이기 때문이다. **언어 이름은 검색과 인지에서 가장 강력한 라벨이다.** `[Python] …` 제목을 단 31편을 주제별로 흩으면, 검색으로 들어온 독자에게 보여줄 옆 글이 무너진다. 축의 순수성은 도서관 분류학의 미덕이지 블로그의 미덕이 아니다.

다만 예외를 **두 개로 묶어 두고 아래쪽에 놓는다**(6번, 10번). 언어가 트리의 얼굴이 되지 않게 한다 — 이 블로그의 최신 글은 Kotlin/Spring/K8s이지 Python이 아니다.

### 3.2 배치를 가른 판단들

- **JVM 5편은 `백엔드/Kotlin·Spring`으로.** GC 3편은 2025년 글이고 "Spring Boot GC 부하 테스트"라 Spring과 붙는 게 맞다. 언어 상위에 두면 죽은 서랍에 활성 글이 묻힌다.
- **K8s 위에서 Spring 앱을 운영한 6편은 인프라로.** OOMKilled 3부작과 Argo 전환 3부작은 Spring 코드보다 K8s 운영이 주제이고, 유입 검색어도 "OOMKilled" "Argo Workflows"일 가능성이 높다.
- **`Web` 18편은 성격이 둘이었다.** HTTP·브라우저 개념 10편과 웹해킹·XSS 8편. 후자를 `보안`으로 모으니 최신 보안 글(타이밍 어택, AccessKey 유출, 개인정보보호법)과 합쳐져 13편이 됐다. **`보안`은 최근 2년 4편으로 성장 중이라** 나중에 상위로 독립시킬 여지를 남겼다.
- **`Search Engine` 2편은 단독으로 두지 않았다.** Redis와 묶어 `NoSQL·검색` 5편으로. 비-RDB 저장소라는 공통점이 있다.
- **토끼책(객체지향의 사실과 오해) 2편은 `기록`이 아니라 `백엔드/설계 원칙`에.** SOLID·DRY와 같은 내용이라 함께 있어야 유용하다.
- **`알고리즘` `Go` `기록`은 하위를 두지 않았다.** 각각 15·11·7편이고 더 쪼갤 실익이 없다. 특히 `기록` 7편에 하위 3개는 과분할이고, `개발자 생각` 같은 이름은 방치되기 쉽다.

### 3.3 이름 규칙

| 규칙 | 이유 |
|---|---|
| **`&`를 쓰지 않는다** | URL에서 `%26`, RSS·OG에서 `&amp;` 이스케이프. 사이드바에서 `A & B` 패턴이 반복되면 읽기 피곤하다. `·`로 대체 — 쿼리 구분자로 오해될 여지가 없다 |
| **하위에 `/`를 쓰지 않는다** | `상위/하위` 경로 표기와 충돌한다. `CI/CD` → `CI·CD` |
| **하위에서 상위 이름을 반복하지 않는다** | `Python 성능 & 동시성` → `Python/성능과 동시성` |
| **한두 단어로 끝낸다** | 사이드바·글 머리 라벨·브레드크럼에 모두 들어간다 |

`scripts/remap-categories.py`가 `&`와 `/`를 검사해 위반 시 실패한다.

---

## 4. 정렬 순서와 그 근거

티스토리 카테고리 관리 화면에서 드래그로 순서를 정한다. **활성 주력 → 대형 아카이브 → 잡문** 순이다.

| # | 상위 | 편수 | 2025~26 | 최신 글 | 놓은 이유 |
|---:|---|---:|---:|---|---|
| 1 | 인프라 | 40 | **8** | 2026.05 | 최근 2년 글이 가장 많다. 블로그의 현재 |
| 2 | 백엔드 | 44 | 7 | 2025.12 | 최대 카테고리이자 활성 |
| 3 | 데이터 | 39 | 0 | 2024.03 | 정체지만 대형 — 크기도 방문자에게는 정보다 |
| 4 | 웹·보안 | 23 | 5 | **2026.08** | 가장 최근 글. 성장 중 |
| 5 | AI | 20 | 4 | 2026.03 | 성장 중 |
| 6 | Python | 31 | 0 | 2023.04 | 대형 아카이브. 검색 유입은 살아 있다 |
| 7 | 코드 품질 | 31 | 3 | 2026.07 | 25편이 2019·2021년 책 정리. 테스트만 활성 |
| 8 | 개발 도구 | 14 | 3 | 2026.02 | 소형 활성 |
| 9 | 알고리즘 | 15 | 0 | 2023.12 | 아카이브 |
| 10 | Go | 11 | 0 | 2022.08 | 아카이브 |
| 11 | 기록 | 7 | 5 | 2026.05 | 활성이지만 성격상 맨 아래 |

하위 단위 활성도는 `python3 scripts/remap-categories.py`가 매번 출력한다.

---

## 5. 구 → 신 이동 요약

가장 크게 흩어지는 것부터.

| 현재 | 편수 | 이동 |
|---|---:|---|
| `IT` (직속) | 35 | **11곳으로 분해** — 설계 원칙 11 · 보안 5 · 테스트 4 · 개발 환경 4 · CI·CD 4 · 기록 2 · 나머지 5 |
| `Python/Python` | 28 | 성능과 동시성 14 · 기초 9 · 라이브러리 4 · 알고리즘 1 |
| `Database/MySQL` | 21 | MySQL 17 · DB 이론 4 |
| `IT/Web` | 18 | HTTP 9 · 보안 8 · 기록 1 |
| `IT/알고리즘` | 14 | 알고리즘 13 · 분산 시스템 1 |
| `IT/AI` | 12 | LLM 활용 6 · 로컬 모델 5 · Langchain 1 |
| `Kotlin & Java/Spring` | 10 | **쿠버네티스 6** · Kotlin·Spring 4 |
| `OS/Centos` | 10 | 리눅스 6 · 모니터링 2 · 네트워크 2 |
| `IT/Git` | 9 | Git 8 · CI·CD 1 |

**통째로 옮겨가는 것** — `IT/Clean Code`→코드 품질/Clean Code, `IT/리팩토링`→코드 품질/리팩토링, `Infrastructure/MSA`→백엔드/분산 시스템, `Infrastructure/Fluentd`→인프라/모니터링, `Go`→Go, `Kotlin & Java`(직속)→백엔드/Kotlin·Spring, `Python/Django`+`Python/Flask`+`PHP/*`→백엔드/웹 프레임워크, `Infrastructure/Kafka`+`CDC`+`Airflow`→데이터/데이터 파이프라인.

전체 275편의 개별 이동은 §9 부록과 `data/category-mapping.json`에 있다.

---

## 6. 확인이 필요한 9건

배치 근거가 갈릴 수 있는 글들이다. 원문을 봐야 확정된다.

| 글 | 배치 | 다른 선택지 |
|---|---|---|
| 캐시 (Cache) | 웹·보안/HTTP | HTTP 캐시가 아니라 애플리케이션 캐시면 → 데이터/NoSQL·검색 |
| OOMKilled 추적기 3부작 | 인프라/쿠버네티스 | Spring Boot 앱 문제로 보면 → 백엔드/Kotlin·Spring |
| Argo Workflows 전환 3부작 | 인프라/쿠버네티스 | 2편이 Spring Batch REST API 설계라 → 백엔드/Kotlin·Spring |
| JVM GC 3부작 | 백엔드/Kotlin·Spring | 언어 런타임으로 보면 → Python처럼 `JVM` 상위 신설 |
| ChatGPT + streamlit 웹앱 | Python/라이브러리 | → AI/LLM 활용 |
| 속도의 병목이 이동하고 있다 | AI/LLM 활용 | 에세이라 → 기록 |
| 토끼책 2편 | 백엔드/설계 원칙 | 책 정리라 → 기록 |
| batch 프로그램으로 host 변경 | 개발 도구/개발 환경 | hosts 파일이 주제라 → 인프라/네트워크 |
| fail2ban | 인프라/리눅스 | 침입 차단이라 → 웹·보안/보안 |

**크롤링이 닿지 않은 것** — 티스토리 관리 화면의 `비공개용 (3)`은 비공개 글이라 실측에 잡히지 않았다. 이 3편은 직접 확인해서 배치하거나 비공개인 채로 남긴다.

---

## 7. 스킨 프로젝트에 미치는 영향

| 항목 | 영향 |
|---|---|
| **DECISIONS.md 결정 5** (상위 카테고리별 기본 이미지 11장) | **변경 없음.** 상위가 11종 그대로다 |
| **DECISIONS.md 결정 7** (카테고리 목록 상단 배너) | **유지, 그리고 더 필요해졌다.** 대표이미지 0% 카테고리가 여전히 있다 — `코드 품질/리팩토링` 9편 전부 없음, `코드 품질/Clean Code` 15/16 없음, `데이터/MySQL` 14/19 없음 |
| **DESIGN.md §6.2** (`data-cat` 접두 선택자) | **선택자 값 전면 교체.** 새 상위 11종 사이에 접두 충돌은 없다. `&`가 사라져 이스케이프 걱정이 줄었지만, 공백이 있으므로 여전히 따옴표로 감싼다 — `[data-cat^="개발 도구"]` |
| **DECISIONS.md §3 실측 카테고리 절** | 적용 후 `/blog-census`로 `data/categories.json` 재생성 필요 |
| **DECISIONS.md 미결 6** (기본 이미지 도안) | 이 개편이 그 선행 작업이다. 확정 후 11장 도안 착수 |
| **URL** | 티스토리 글 주소는 `/entry/{제목}` 또는 `/{번호}`라 **카테고리를 바꿔도 글 URL은 변하지 않는다.** 바뀌는 것은 `/category/...` 목록 주소뿐 |

---

## 8. 티스토리에서 실행하는 순서

카테고리 관리 화면은 되돌리기가 없다. 순서를 지킨다.

> **실제로 작업할 때는 [`category-migration-worksheet.md`](./category-migration-worksheet.md)를 연다.** 아래는 개요이고, 그쪽에 체크박스와 글 제목까지 있다 — 통째 이동 25건(109편) / 쪼개서 이동 11건(166편).

1. **백업** — 관리 → 데이터 관리에서 블로그 백업을 먼저 받는다
2. **새 상위 11종을 만든다** — 기존 것을 고치지 말고 새로 만든다. 기존 트리는 이동이 끝날 때까지 남겨 둔다
3. **하위 26종을 만든다**
4. **글을 옮긴다** — 관리 → 글 관리에서 카테고리로 필터 → 전체 선택 → 카테고리 이동. §9 부록의 카테고리별 목록 순서대로 진행하면 한 번에 한 덩어리씩 끝난다
5. **빈 기존 카테고리를 지운다** — 글을 다 옮기면 기존 트리 47줄이 전부 0편이 된다. `Design Pattern`처럼 처음부터 0편이던 것들도 이때 함께 사라진다
6. **정렬 순서를 잡는다** — §4의 번호대로 드래그. 이걸 빠뜨리면 개편 효과의 절반이 날아간다
7. **비공개 3편을 배치한다**
8. **재실측** — `/blog-census` 실행 → `data/categories.json`·`DECISIONS.md` §3 갱신
9. **스킨 반영** — 기본 이미지 11장 도안 → `DESIGN.md` §6.2 `data-cat` 선택자 교체

> 4번이 가장 오래 걸린다. `IT` 직속 35편은 11곳으로 흩어지므로 개별 확인이 필요하다. 나머지는 대부분 카테고리 단위로 통째 이동이라 빠르다.

---

## 9. 부록 — 신규 카테고리별 전체 글 목록

이동 작업 시 체크리스트로 쓴다. 카테고리 순서는 §4의 정렬 순서와 같다.

### 인프라/쿠버네티스 (8)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.05.09 | K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 3편: HikariCP 설정으로인한 Socket 메모리 누수 | Kotlin & Java/Spring |
| 2026.04.21 | K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 2편: K8s 팟 힙 덤프 추출과 논힙 메모리 추적 | Kotlin & Java/Spring |
| 2026.04.06 | K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 1편: OOM 레벨 구분과 QoS 확인 | Kotlin & Java/Spring |
| 2026.03.27 | K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 3편: Argo Workflows로 스케줄링하기 | Kotlin & Java/Spring |
| 2026.03.27 | K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 2편: Spring Batch REST API 서버 설계 | Kotlin & Java/Spring |
| 2026.03.27 | K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 1편: CronJob 문제와 스케줄러 선택 | Kotlin & Java/Spring |
| 2023.12.02 | [Docker] 도커 사용하지 않는 볼륨, 이미지 삭제하는 방법 | Infrastructure/Docker |
| 2023.01.09 | [Kubernetes] OpenLens 설치 | IT |

### 인프라/모니터링 (15)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2021.08.12 | [Fluentd] MySQL slow log 연동 | Infrastructure/Fluentd |
| 2021.06.29 | Promtheus + MySQL Exporter 연동 | Infrastructure/Prometheus |
| 2021.06.29 | Prometheus + Node Exporter + Grafana 연동 | Infrastructure/Prometheus |
| 2021.05.11 | [Fluentd] Php 연동 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] Python 연동 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 8. Prometheus 연동 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 7. Nginx 연동 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 6. 서버간 연동 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 5. Output plugin | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 4. Input plugin | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 3. 설정 파라미터 | Infrastructure/Fluentd |
| 2021.05.11 | [Fluentd] 2. 설정 개요 | Infrastructure/Fluentd |
| 2021.05.06 | [Fluentd] 1. 설치 | Infrastructure/Fluentd |
| 2021.04.09 | [CentOS] CPU, Memory 사용량 로그 | OS/Centos |
| 2021.04.08 | [CentOS 7] Prometheus + Grafana 설치 | OS/Centos |

### 인프라/리눅스 (6)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2021.02.04 | Cent OS 6 버전 yum 에러 | OS/Centos |
| 2019.10.23 | 설치 에러 발생시 대처 | OS/Centos |
| 2019.10.22 | fail2ban | OS/Centos |
| 2019.10.22 | Centos 파일, 디렉토리 찾기 | OS/Centos |
| 2019.10.22 | 파이선, 쉘스크립트 윈도우 -> 리눅스 되었을때 발생하는 문제 | OS/Centos |
| 2019.10.22 | 쉘 접속 지연 문제 해결 방법 | OS/Centos |

### 인프라/네트워크 (6)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.04.02 | 통신사별 DNS IP 리스트 (구글, SKT, KT, LG, Cloudflare) | IT |
| 2023.01.29 | [Ubuntu 20.04] OpenVPN Server Docker 설치 및 Client | Infrastructure/VPN |
| 2022.05.16 | Ubuntu 20.04 고정 IP 할당 방법 | OS/Ubuntu |
| 2019.10.22 | CentOS 7 / 고정 IP 설정하는 방법 | OS/Centos |
| 2019.10.22 | 넷기어 VPN - L2TP 설정 | Infrastructure/VPN |
| 2019.10.22 | Centos 6, 7 포트 추가 | OS/Centos |

### 인프라/CI·CD (5)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2025.05.02 | Jira와 GitHub 연동을 통한 태스크 상태 전환 및 버전 릴리스 자동화 | IT |
| 2022.02.05 | Github Action | IT/Git |
| 2021.09.27 | Jenkins Nexus Docker 연동하기 | IT |
| 2021.02.08 | [Jenkins] 젠킨스 Dockerfile 설치 | IT |
| 2021.02.05 | [Jenkins] 젠킨스란 무엇인가 | IT |

### 백엔드/Kotlin·Spring (9)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2025.12.01 | 다중 DataSource 환경에서 장애 격리하기: LazyConnectionDataSourceProxy 활용기 | Kotlin & Java/Spring |
| 2025.04.10 | JVM Garbage Collection Tuning - Spring Boot GC 부하 테스트 | Kotlin & Java |
| 2025.04.10 | JVM Garbage Collection Algorithm | Kotlin & Java |
| 2025.04.06 | JVM Garbage Collection | Kotlin & Java |
| 2024.07.28 | Kotlin + Spring Boot 에서 data class 구현으로 Validation 로직 작성하기 | Kotlin & Java/Spring |
| 2024.03.10 | [Gradle] Gradle dependency (그래들 종속성 선언) | Kotlin & Java |
| 2024.02.06 | Pessimistic Locking in JPA | Kotlin & Java/Spring |
| 2023.10.29 | Intellij에서 Kotlin을 Java로 변환 확인 하는 방법 | Kotlin & Java |
| 2023.03.22 | [Code Execution API] 1. 프로그래밍 코드 실행 API 만들어보기 | Kotlin & Java/Spring |

### 백엔드/웹 프레임워크 (12)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2020.07.14 | Django demo project (chatting, monggo db, sample) | Python/Django |
| 2019.11.11 | 5. Django - Nginx 연동 | Python/Django |
| 2019.11.07 | 4. Django 모델 및 관리자 | Python/Django |
| 2019.10.28 | 3. Django 뷰 작성 및 라우팅 | Python/Django |
| 2019.10.25 | 2.  Django 프로젝트 생성 | Python/Django |
| 2019.10.25 | 1. Django 및 기타 설치 | Python/Django |
| 2019.10.25 | Flask Flask-SQLAlchemy | Python/Flask |
| 2019.10.23 | Flask  Request Handler, Error Handler | Python/Flask |
| 2019.10.23 | Centos7 Nginx, PHP, MySQL  Codeigniter 프로젝트 세팅 | PHP/Codeigniter |
| 2019.10.23 | Centos  Laravel 설치 | PHP/Laravel |
| 2019.10.23 | Flask 관련... | Python/Flask |
| 2019.10.23 | Centos 7 Flask 설치 | Python/Flask |

### 백엔드/분산 시스템 (12)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2025.03.29 | Consistent hashing, 일관된 해싱 | IT/알고리즘 |
| 2025.03.27 | [분산 시스템] Raft Consensus Algorithm, 뗏목 합의 알고리즘 | Infrastructure |
| 2025.03.26 | [분산 시스템] CAP Theorem: Consistency, Availability, Partition tolerance | Infrastructure |
| 2022.10.08 | 알림 서비스 디자인 | IT |
| 2021.09.27 | Micro Service Architecture - 6. IPC 3 | Infrastructure/Micro Service Architecture |
| 2021.09.27 | Micro Service Architecture - 6. IPC 2 | Infrastructure/Micro Service Architecture |
| 2021.09.27 | Micro Service Architecture - 6. IPC | Infrastructure/Micro Service Architecture |
| 2021.09.27 | Micro Service Architecture - 5.분해전략 2 | Infrastructure/Micro Service Architecture |
| 2021.09.27 | Micro Service Architecture - 4.분해전략 | Infrastructure/Micro Service Architecture |
| 2021.09.07 | Micro Service Architecture - 3.패턴 | Infrastructure/Micro Service Architecture |
| 2021.09.06 | Micro Service Architecture - 2.FTGO 예시 | Infrastructure/Micro Service Architecture |
| 2021.09.06 | Micro Service Architecture - 1. MSA | Infrastructure/Micro Service Architecture |

### 백엔드/설계 원칙 (11)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2024.12.19 | 의존성 주입에 대한 생각 | IT |
| 2024.08.01 | 멱등성 (Idempotence)와 HTTP API 설계 | IT |
| 2021.01.22 | 소프트웨어 개발원칙 YAGNI | IT |
| 2021.01.22 | 소프트웨어 개발원칙 KISS | IT |
| 2021.01.22 | 소프트웨어 개발 원칙 DRY | IT |
| 2021.01.22 | 객체지향 설계 5대 원리 SOLID - IRP | IT |
| 2021.01.21 | 객체지향 설계 5대 원리 SOLID - OCP | IT |
| 2021.01.21 | 객체지향 설계 5대 원리 SOLID  - SRP | IT |
| 2021.01.21 | 객체지향 설계 5대 원리 SOLID | IT |
| 2019.10.22 | [토끼책] 객체지향의 사실과 오해 - 2장. 이상한 나라의 객체 | IT |
| 2019.10.22 | [토끼책] 객체지향의 사실과 오해 1장 - 협력하는 객체들의 공동체 | IT |

### 데이터/MySQL (19)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2024.02.15 | [MySQL] Table lock 조회 쿼리 | Database/MySQL |
| 2023.12.24 | [MySQL] GROUP BY Optimization | Database/MySQL |
| 2023.12.06 | [MySQL] ORDER BY Optimization | Database/MySQL |
| 2023.08.24 | [MySQL] Show Index | Database/MySQL |
| 2022.05.09 | [MySQL] binlog to SQL(텍스트) 변환 | Database/MySQL |
| 2021.06.17 | [Ubuntu 20.04] MySQL 5.6.xx 설치 | OS/Ubuntu |
| 2021.01.15 | [Ubuntu 18] docker 를 이용한 MariaDB Sharding (샤딩) | OS/Ubuntu |
| 2020.07.14 | MariaDB sharding using docker | Database/MySQL |
| 2019.10.22 | MySQL Replication 연결 | Database/MySQL |
| 2019.10.22 | MySQL DB 명세서 쿼리 작성 | Database/MySQL |
| 2019.10.22 | MySQL innodb 버퍼 할당 에러 | Database/MySQL |
| 2019.10.22 | MySQL 프로시저 디버그 | Database/MySQL |
| 2019.10.22 | MySQL error 1364 Field doesn't have a default values | Database/MySQL |
| 2019.10.22 | MySQL Dump시 테이블 Lock 에러 | Database/MySQL |
| 2019.10.22 | MySQL 접속 유저 추가 | Database/MySQL |
| 2019.10.22 | MySQL 5.7 설정 튜닝 | Database/MySQL |
| 2019.10.22 | MySQL's Storage Engines - InnoDB Engine | Database/MySQL |
| 2019.10.22 | 프로시저 언제 사용해야 하나? | Database/MySQL |
| 2019.10.22 | MySQL's Storage Engies - MyISAM Engine | Database/MySQL |

### 데이터/DB 이론 (4)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2019.10.22 | Indexing for High Performance | Database/MySQL |
| 2019.10.22 | 데이터 베이스 설계 프로세스 | Database/MySQL |
| 2019.10.22 | Isolation level (트랜잭션 고립(격리) 수준) | Database/MySQL |
| 2019.10.22 | 트랜잭션 너는 누구니? | Database/MySQL |

### 데이터/NoSQL·검색 (5)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2022.07.23 | [Redis] 활용 방법 | Database/Redis |
| 2022.07.23 | [Redis] Command | Database/Redis |
| 2022.07.23 | [Redis] 간단 개요 | Database/Redis |
| 2019.10.23 | Centos7 ElasticSearch 설치 | Search Engine/ElasticSearch |
| 2019.10.23 | Centos7 + Lucene Solr 8.2 설치 및 실행 | Search Engine/Lucene Solr |

### 데이터/데이터 파이프라인 (11)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2024.03.08 | [CDC] MySQL Debezium Change Data Capture 따라해보기 - 3 | Infrastructure/CDC |
| 2024.02.10 | [CDC] MySQL Debezium Change Data Capture 따라해보기 - 2 | Infrastructure/CDC |
| 2024.02.10 | [CDC] MySQL Debezium Change Data Capture 따라해보기 - 1 | Infrastructure/CDC |
| 2024.02.10 | [CDC] Change Data Capture 개념 | Infrastructure/CDC |
| 2023.10.29 | [Kafka] 카프카 컨슈머 | Infrastructure/Kafka |
| 2023.09.17 | [Kafka] 카프카 프로듀서 | Infrastructure/Kafka |
| 2023.09.17 | [Kafka] 카프카 메시지 브로커 | Infrastructure/Kafka |
| 2023.09.15 | [Kafka] 카프카 에러 핸들링 패턴 | Infrastructure/Kafka |
| 2023.02.07 | [Kafka] Python confluent Kafka 설치 및 테스트 | Infrastructure/Kafka |
| 2021.11.04 | [Airflow] DAGs 생성하기 | Infrastructure/Airflow |
| 2021.10.26 | [Airflow] Ubuntu 20.04 docker-compose 설치 | Infrastructure/Airflow |

### 웹·보안/HTTP (10)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2025.04.01 | HTTP (Hypertext Transfer Protocol) 개념알기, HTTP/3 | IT/Web |
| 2024.12.25 | HTTP (Hypertext Transfer Protocol) 개념알기, HTTP/2 | IT/Web |
| 2024.12.24 | HTTP (Hypertext Transfer Protocol) 개념알기 | IT/Web |
| 2021.09.27 | WEB RTC | IT |
| 2021.01.19 | 캐시 (Cache) | IT/Web |
| 2021.01.15 | DNS(Domain Name System) 작동원리 | IT/Web |
| 2021.01.15 | 브라우저 동작 원리 | IT/Web |
| 2021.01.14 | HTTP Response Status Code (HTTP 응답 상태 코드) | IT/Web |
| 2021.01.13 | HTTP Request Method (HTTP 요청 방법) | IT/Web |
| 2021.01.13 | HTTP (HyperText Transfer Protocol) 란? | IT/Web |

### 웹·보안/보안 (13)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.08.12 | 타이밍 어택, 어디까지 막아야 할까? == 비교부터 프레임워크 CVE까지 | IT |
| 2026.05.22 | 유출된 AWS AccessKey 무중단 교체하기: 출근길에마주한 IAM 유저 생성 시도 알림 | IT |
| 2025.12.03 | 백엔드 관점에서 본 개인정보 보호법 및 안전성 확보조치 핵심 요약 | IT |
| 2025.11.28 | 2025년 실서비스 보안 취약점 발견 후기 | IT |
| 2023.05.18 | [Web Hacking] Challange 54 풀이 | IT/Web |
| 2023.05.05 | [Web Hacking] Challange 24 풀이 | IT/Web |
| 2023.05.01 | [Web Hacking] Challange 16 풀이 | IT/Web |
| 2023.05.01 | [보안] Cookie bomb attack | IT/Web |
| 2023.04.30 | [Web Hacking] Challange 26 풀이 | IT/Web |
| 2023.04.30 | [Web Hacking] Challange 15 풀이 | IT/Web |
| 2023.04.13 | [보안] XSS HTML Image 태그 주의할 점 - 2 | IT/Web |
| 2023.04.08 | [보안] XSS HTML Image 태그 주의할 점 | IT/Web |
| 2021.09.27 | JWT (JSON Web Token) | IT |

### AI/LLM 활용 (6)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.03.26 | 구글 제미나이(Gemini), 데스크탑 앱처럼 쓰는 방법 - PWA 설치 가이드 | IT/AI |
| 2026.02.10 | 속도의 병목이 이동하고 있다 | IT/AI |
| 2024.12.12 | ORM 사용에 관한 에이전트 토론 들어보기 | IT/AI |
| 2024.11.24 | Prompt Engineering Guide: Prompting Techniques | IT/AI |
| 2024.11.22 | Prompt Engineering Guide: LLM Arguments | IT/AI |
| 2024.08.06 | [AI] Markdown 을 사용한 Prompts 작성 방법 | IT/AI |

### AI/Langchain (9)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2024.12.14 | [AI] 오디오 녹음 요약하기 (OpenAI Whisper, Langchain, Exaone) | IT/AI |
| 2024.12.09 | [Langchain] Chatbot 챗봇 구현 | IT/Langchain |
| 2024.12.07 | [Langchain] 이미지 분석 | IT/Langchain |
| 2024.12.05 | [Langchain] 계엄령 기념, 집밥 같은 랭체인 코드로 계엄령 뉴스 보기 | IT/Langchain |
| 2024.12.02 | [Langchain] AI vs AI 토론을 가장한 말싸움 하기 | IT/Langchain |
| 2024.11.26 | [Langchain] 웹 요약 Agent | IT/Langchain |
| 2024.11.25 | [Langchain] PDF 요약 Agent | IT/Langchain |
| 2024.11.25 | [Langchain] Math Agent | IT/Langchain |
| 2024.11.24 | [Langchain] 네이버 뉴스 요약 | IT/Langchain |

### AI/로컬 모델 (5)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.02.05 | Run Claude Code with Ollama Local & Cloud Models | IT/AI |
| 2025.01.15 | Ollama Model Update 모델 일괄 업데이트 방법 | IT/AI |
| 2024.11.28 | [Stable Diffusion] Stable Diffusion 3.5 Text to Image 이미지 생성 | IT/AI |
| 2024.08.07 | Ollama로 Github PR AI 코드 리뷰 하기 | IT/AI |
| 2024.01.26 | [AI] stable-code-3b 기본적인 사용 가이드 (AI coding) | IT/AI |

### Python/기초 (9)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2022.10.31 | [Python] Linter 비교 | Python/Python |
| 2022.07.08 | [Python] DTO, Dataclass Validate 방법 | Python/Python |
| 2022.01.03 | [Python] __slots__ method | Python/Python |
| 2021.12.23 | [Python] __new__ method | Python/Python |
| 2021.01.22 | CentOS pyenv 설치 | Python/Python |
| 2021.01.15 | [Python] builtin dir() 함수 | Python/Python |
| 2021.01.08 | [Python] builtin all() 함수 | Python/Python |
| 2021.01.07 | [Python] builtin abs() 함수 | Python/Python |
| 2019.10.22 | PIP 꼬임 | Python/Python |

### Python/성능과 동시성 (14)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2023.04.05 | [Python] 파이썬 Thread and Pool Manager | Python/Python |
| 2022.09.28 | [Python] lru_cache | Python/Python |
| 2022.09.28 | [Python] Object class __slots__를 이용한 성능 개선 | Python/Python |
| 2022.08.14 | [Python] Concurrency Thread Decorator - 3 | Python/Python |
| 2022.08.12 | [Python] Concurrency PDF 파일 생성  - 2 | Python/Python |
| 2022.08.12 | [Python] Concurrency 어떤 경우에 어떤 것을 사용하는게 좋을까 - 1 | Python/Python |
| 2022.07.09 | [Python] Thread와 Async를 이용한 비동기 방법 | Python/Python |
| 2021.11.25 | [Python] 파이썬 multiprocessing | Python/Python |
| 2021.11.25 | [Python] 파이썬 비동기 I/O | Python/Python |
| 2021.11.15 | [Python] 사전(dict) 와 셋(set) 의 성능 | Python/Python |
| 2021.11.12 | [Python] 튜플(tuple) 성능 | Python/Python |
| 2021.11.12 | [Python] 리스트(list) 성능 | Python/Python |
| 2021.11.12 | [Python] 프로파일링 cProfile, memory_profiler | Python/Python |
| 2021.11.09 | [Python] 검색 방법 profile 해보기 | Python/Python |

### Python/라이브러리 (8)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2023.04.04 | [Python] 파이썬 출력 문자 색 변경하기 | Python/Open Source |
| 2023.03.14 | ChatGPT를 이용한 간단한 Web App 만들기 (python, streamlit) | Python/Open Source |
| 2022.07.23 | [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 3 | Python/Python |
| 2022.07.13 | [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 2 | Python/Python |
| 2022.07.13 | [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 1 | Python/Python |
| 2022.02.05 | Python 에서 go 함수 사용 하는 방법 | Python/Python |
| 2021.08.12 | [Python] Colorful print | Python/Open Source |
| 2021.01.13 | [Python 오픈소스] Diagrams | Python/Open Source |

### 코드 품질/Clean Code (16)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2021.09.06 | [Clean Code] 11-1 Concern | IT/Clean Code |
| 2021.09.06 | [Clean Code] 10-2 응집도 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 10-1 클래스 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 9-3 깨끗한 테스트 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 9-2 도메인 특화 테스트 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 9-1 TDD | IT/Clean Code |
| 2021.09.06 | [Clean Code] 7-1 예외처리 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 6-2 객체지향 절차지향 2 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 6-1 객체지향 절차지향 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 5-1 형식 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 4-1 주석 | IT/Clean Code |
| 2021.09.06 | [Clean Code] 3-2 Functions | IT/Clean Code |
| 2021.08.18 | [Clean Code] 3-1 Parameter | IT/Clean Code |
| 2021.08.18 | [Clean Code] 2-2 Method | IT/Clean Code |
| 2021.08.18 | [Clean Code] 2-1 Class 와 Method 이름 | IT/Clean Code |
| 2019.11.13 | [Clean Code] 0. 앞 부분... | IT/Clean Code |

### 코드 품질/리팩토링 (9)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2019.10.25 | [리팩토링] 임수변수 내용 직접 삽입 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 메소드 삽입 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 메소드 추출 | IT/리팩토링 |
| 2019.10.25 | 리팩토링 - 코드 개선 방법 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 클래스 멤버변수 이동 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 객체간 메소드 이동 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 메소드를 메소드 객체로 전환 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 매개변수로의 값 대입 제거 | IT/리팩토링 |
| 2019.10.25 | [리팩토링] 직관적 임시변수 사용 | IT/리팩토링 |

### 코드 품질/테스트 (6)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.07.17 | AI 코딩 에이전트 git worktree 병렬 개발의 테스트 인프라, Testcontainers로 전환하기 - 2편 | IT |
| 2026.07.17 | AI 코딩 에이전트 git worktree 병렬 개발의 테스트 인프라, Testcontainers로 전환하기 - 1편 | IT |
| 2026.06.19 | Chrome Local Overrides로 API 응답을 변경하고 UI를 테스트하는 방법 | IT |
| 2023.03.15 | [Locust] 2. Locust를 통한 언어와 프레임워크 별 테스트 | Python/Open Source |
| 2023.03.15 | [Locust] 1. Locust 부하 테스트 툴(load testing tool) | Python/Open Source |
| 2022.12.24 | API, 서비스, 도메인 테스트 및 TDD 에서의 기어비 | IT |

### 개발 도구/Git (9)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.02.05 | Git Worktree 주요 명령어 정리 (add / list / remove) | IT/Git |
| 2023.12.12 | [Git] .gitignore 적용이 안되는 경우 | IT/Git |
| 2023.09.13 | Jetbrains IDE용 Git 팁 | IT/Git |
| 2022.07.21 | Git Commit Message Convention 정리 | IT/Git |
| 2021.08.19 | Git 프로젝트 별로 다른 계정 사용하기 | IT/Git |
| 2021.02.18 | Git Branch 를 통한 Gitflow | IT/Git |
| 2021.02.17 | Git Branch 사용법 | IT/Git |
| 2021.02.17 | Gitlab 에서 Github 로 저장소 log 유지하며 옮기기 | IT/Git |
| 2019.10.23 | GitLab - SVN 마이그레이션 및 Clone | IT |

### 개발 도구/개발 환경 (5)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.02.11 | 터미널 오픈소스 도구 모음: btop, k9s, Mole, Sniffnet | IT |
| 2025.08.08 | [Mac] 맥 환경, Jetbrains IDE 과거 버전 삭제 | IT |
| 2024.02.26 | [Jetbrains]  Intellij 인텔리제이 Live Template 사용 방법 | IT |
| 2022.09.19 | [Mac] 사용 중인 Port 찾기, Kill 하기 | OS/Mac |
| 2019.10.25 | batch 프로그램으로 host 변경하기 | IT |

### 알고리즘 (15)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2023.12.04 | [통계] 정규화(Normalization)와 표준화(Standardization) | IT/수학 |
| 2022.05.12 | [Python] 후위표기법(postifx) 계산 코드 | Python/Python |
| 2022.01.08 | [백준] 4963 파이썬(python) | IT/알고리즘 |
| 2022.01.08 | [백준] 2468 파이썬(python) | IT/알고리즘 |
| 2022.01.08 | [백준] 1697 파이썬(python) | IT/알고리즘 |
| 2022.01.08 | [백준] 11403 파이썬(python) | IT/알고리즘 |
| 2022.01.08 | [백준] 9372 파이썬(python) | IT/알고리즘 |
| 2022.01.08 | [백준] 7569 파이썬(python) | IT/알고리즘 |
| 2021.11.07 | [Python] 백준 11724 - 연결 요소의 개수 | IT/알고리즘 |
| 2021.11.06 | [Python] 백준 7576 - 토마토 | IT/알고리즘 |
| 2021.11.06 | [Python] 백준 1012 - 유기농 배추 | IT/알고리즘 |
| 2021.11.06 | [Python] 백준 2667 - 단지번호붙이기 | IT/알고리즘 |
| 2021.01.23 | 프로그래머스 - 가장 큰 정사각형 찾기 | IT/알고리즘 |
| 2021.01.22 | 프로그래머스 - 나머지 한 점 | IT/알고리즘 |
| 2021.01.22 | 프로그래머스 - 순열 검사 | IT/알고리즘 |

### Go (11)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2022.08.02 | [Go] Time | Go |
| 2022.07.25 | [Go] Factory Pattern(팩토리 패턴) 구현 | Go |
| 2022.07.24 | [Go] Channel 이용한 Queue | Go |
| 2022.07.23 | [Go] Int, String, Struct 정렬 | Go |
| 2022.07.23 | [Go] Linked List 구현 | Go |
| 2022.07.23 | [Go] Panic recover 하기 | Go |
| 2022.07.22 | [Go] File 정보 확인 | Go |
| 2022.07.22 | [Go lang] Excel 읽기, 쓰기 | Go |
| 2022.07.21 | [Go] variable type별 printf format | Go |
| 2022.07.21 | [Go]  대용량 파일 chunk 단위로 나누기 | Go |
| 2022.02.05 | Golang | Go |

### 기록 (7)

| 날짜 | 제목 | 현재 위치 |
|---|---|---|
| 2026.05.29 | 맛있는 치킨스톡 | 일상 |
| 2026.05.27 | 출근길, 직우차로 한대의 경찰차 | 일상 |
| 2026.03.18 | 쿠버네티스 패턴 (빌긴 이브리암 , 롤란트 후스 저자), 후기 | 책책책 책을 읽읍시다 |
| 2025.10.22 | 프로그래머의 뇌, 후기 | 책책책 책을 읽읍시다 |
| 2025.05.26 | 좋은 엔지니어 되기: 핵심 원칙과 실천 방안 | IT |
| 2021.01.13 | 2020년 백엔드(Back-end) 개발자 로드맵 | IT/Web |
| 2019.10.23 | 개발에 있어서... | IT |
