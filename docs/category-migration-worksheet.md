# 카테고리 이동 작업 체크리스트

티스토리 관리 화면을 열어 두고 이 파일을 보면서 진행한다.
설계 근거와 왜 이렇게 나눴는지는 [`category-taxonomy.md`](./category-taxonomy.md)에 있다 — **이 파일은 손으로 하는 작업만** 담는다.

**총 275편** · 통째 이동 121편 / 쪼개서 이동 154편

---

## 0단계 — 시작 전

- [ ] **블로그 백업을 받는다** — 관리 → 데이터 관리 → 백업. 카테고리 관리 화면은 되돌리기가 없다
- [ ] 관리 → 글 관리 화면을 연다 (카테고리 필터와 일괄 선택이 여기 있다)

> **기존 카테고리를 고치지 않는다.** 새로 만들고, 글을 옮기고, 빈 껍데기를 지우는 순서다.
> 중간에 멈춰도 글은 전부 어딘가에 남아 있다.

---

## 1단계 — 새 카테고리 만들기

관리 → 카테고리 관리에서 **위에서부터 순서대로** 만든다. 만드는 순서가 곧 노출 순서라 나중에 정렬할 일이 줄어든다.

```
 1. 인프라
      └ 쿠버네티스
      └ 모니터링
      └ 데이터 파이프라인
      └ 리눅스
      └ CI·CD
 2. Kotlin·Spring
 3. 아키텍처
 4. 데이터베이스
      └ MySQL
      └ NoSQL·검색
      └ DB 이론
 5. 네트워크
 6. 보안
 7. AI
 8. 코드 품질
      └ Clean Code
      └ 설계 원칙
      └ 리팩토링
      └ 테스트
 9. Python
      └ 성능과 동시성
      └ Django·Flask
      └ 기초
      └ 라이브러리
10. Go
11. 알고리즘
12. 개발 도구
      └ Git
      └ 개발 환경
13. 기록
```

- [ ] 상위 11종을 만들었다
- [ ] 하위 26종을 만들었다

> **이름 주의** — `CI·CD`의 가운뎃점은 `·`(U+00B7)다. `&`는 어디에도 쓰지 않는다.

---

## 2단계 — 통째로 옮기기

한 카테고리의 글이 전부 같은 곳으로 간다. **글 관리 → 카테고리 필터 → 전체 선택 → 카테고리 이동** 한 번이면 끝난다.

> ⚠️ **하위부터 비우고 상위 직속을 마지막에 한다.** 필터에서 상위를 고르면 하위 글까지 딸려 올 수 있다.
> 상위 직속 글이 있는 것은 `IT`(35) · `Go`(11) · `Kotlin & Java`(5) · `Infrastructure`(2) · `일상`(2) · `책책책 책을 읽읍시다`(2)다.
> 전체 선택 전에 **목록에 뜬 편수가 표의 편수와 같은지** 확인한다.

| ✓ | 기존 카테고리 | 편수 | 옮길 곳 |
|---|---|---:|---|
| [ ] | `IT/Clean Code` | 16 | **코드 품질/Clean Code** |
| [ ] | `IT/AI` | 12 | **AI** |
| [ ] | `Go` | 11 | **Go** |
| [ ] | `Infrastructure/Fluentd` | 11 | **인프라/모니터링** |
| [ ] | `IT/리팩토링` | 9 | **코드 품질/리팩토링** |
| [ ] | `IT/Langchain` | 8 | **AI** |
| [ ] | `Infrastructure/Micro Service Architecture` | 8 | **아키텍처** |
| [ ] | `Python/Django` | 6 | **Python/Django·Flask** |
| [ ] | `Kotlin & Java` | 5 | **Kotlin·Spring** |
| [ ] | `Infrastructure/Kafka` | 5 | **인프라/데이터 파이프라인** |
| [ ] | `Infrastructure/CDC` | 4 | **인프라/데이터 파이프라인** |
| [ ] | `Python/Flask` | 4 | **Python/Django·Flask** |
| [ ] | `Database/Redis` | 3 | **데이터베이스/NoSQL·검색** |
| [ ] | `일상` | 2 | **기록** |
| [ ] | `책책책 책을 읽읍시다` | 2 | **기록** |
| [ ] | `Infrastructure` | 2 | **아키텍처** |
| [ ] | `Infrastructure/VPN` | 2 | **네트워크** |
| [ ] | `Infrastructure/Airflow` | 2 | **인프라/데이터 파이프라인** |
| [ ] | `Infrastructure/Prometheus` | 2 | **인프라/모니터링** |
| [ ] | `IT/수학` | 1 | **알고리즘** |
| [ ] | `Infrastructure/Docker` | 1 | **인프라/쿠버네티스** |
| [ ] | `OS/Mac` | 1 | **개발 도구/개발 환경** |
| [ ] | `Search Engine/ElasticSearch` | 1 | **데이터베이스/NoSQL·검색** |
| [ ] | `PHP/Codeigniter` | 1 | **인프라/리눅스** |
| [ ] | `PHP/Laravel` | 1 | **인프라/리눅스** |
| [ ] | `Search Engine/Lucene Solr` | 1 | **데이터베이스/NoSQL·검색** |

여기까지 121편. 전체의 44%가 이 단계에서 끝난다.

---

## 3단계 — 쪼개서 옮기기

여러 곳으로 갈린다. 카테고리 필터로 거른 뒤 **아래 목록을 보며 골라서** 이동한다.
제목은 관리 화면에 보이는 그대로다. 목적지가 같은 것끼리 묶어 놨으니 한 목적지씩 처리하면 된다.

### `IT` — 35편 → 10곳

**→ 코드 품질/설계 원칙** (11편)

- [ ] 2024.12.19  의존성 주입에 대한 생각
- [ ] 2024.08.01  멱등성 (Idempotence)와 HTTP API 설계
- [ ] 2021.01.22  소프트웨어 개발원칙 YAGNI
- [ ] 2021.01.22  소프트웨어 개발원칙 KISS
- [ ] 2021.01.22  소프트웨어 개발 원칙 DRY
- [ ] 2021.01.22  객체지향 설계 5대 원리 SOLID - IRP
- [ ] 2021.01.21  객체지향 설계 5대 원리 SOLID - OCP
- [ ] 2021.01.21  객체지향 설계 5대 원리 SOLID  - SRP
- [ ] 2021.01.21  객체지향 설계 5대 원리 SOLID
- [ ] 2019.10.22  [토끼책] 객체지향의 사실과 오해 - 2장. 이상한 나라의 객체  ⚠️ 토끼책 2편 — 책 요약이라 기록으로 볼 수도 (내용은 객체지향 설계)
- [ ] 2019.10.22  [토끼책] 객체지향의 사실과 오해 1장 - 협력하는 객체들의 공동체

**→ 보안** (5편)

- [ ] 2026.08.12  타이밍 어택, 어디까지 막아야 할까? == 비교부터 프레임워크 CVE까지
- [ ] 2026.05.22  유출된 AWS AccessKey 무중단 교체하기: 출근길에마주한 IAM 유저 생성 시도 알림
- [ ] 2025.12.03  백엔드 관점에서 본 개인정보 보호법 및 안전성 확보조치 핵심 요약
- [ ] 2025.11.28  2025년 실서비스 보안 취약점 발견 후기
- [ ] 2021.09.27  JWT (JSON Web Token)

**→ 코드 품질/테스트** (4편)

- [ ] 2026.07.17  AI 코딩 에이전트 git worktree 병렬 개발의 테스트 인프라, Testcontainers로 전환하기 - 2편
- [ ] 2026.07.17  AI 코딩 에이전트 git worktree 병렬 개발의 테스트 인프라, Testcontainers로 전환하기 - 1편
- [ ] 2026.06.19  Chrome Local Overrides로 API 응답을 변경하고 UI를 테스트하는 방법
- [ ] 2022.12.24  API, 서비스, 도메인 테스트 및 TDD 에서의 기어비

**→ 개발 도구/개발 환경** (4편)

- [ ] 2026.02.11  터미널 오픈소스 도구 모음: btop, k9s, Mole, Sniffnet
- [ ] 2025.08.08  [Mac] 맥 환경, Jetbrains IDE 과거 버전 삭제
- [ ] 2024.02.26  [Jetbrains]  Intellij 인텔리제이 Live Template 사용 방법
- [ ] 2019.10.25  batch 프로그램으로 host 변경하기  ⚠️ 'batch 프로그램으로 host 변경' — hosts 파일이 주제면 네트워크로

**→ 인프라/CI·CD** (4편)

- [ ] 2025.05.02  Jira와 GitHub 연동을 통한 태스크 상태 전환 및 버전 릴리스 자동화
- [ ] 2021.09.27  Jenkins Nexus Docker 연동하기
- [ ] 2021.02.08  [Jenkins] 젠킨스 Dockerfile 설치
- [ ] 2021.02.05  [Jenkins] 젠킨스란 무엇인가

**→ 네트워크** (2편)

- [ ] 2026.04.02  통신사별 DNS IP 리스트 (구글, SKT, KT, LG, Cloudflare)
- [ ] 2021.09.27  WEB RTC

**→ 기록** (2편)

- [ ] 2025.05.26  좋은 엔지니어 되기: 핵심 원칙과 실천 방안
- [ ] 2019.10.23  개발에 있어서...

**→ 인프라/쿠버네티스** (1편)

- [ ] 2023.01.09  [Kubernetes] OpenLens 설치

**→ 아키텍처** (1편)

- [ ] 2022.10.08  알림 서비스 디자인

**→ 개발 도구/Git** (1편)

- [ ] 2019.10.23  GitLab - SVN 마이그레이션 및 Clone


### `Python/Python` — 28편 → 4곳

**→ Python/성능과 동시성** (14편)

- [ ] 2023.04.05  [Python] 파이썬 Thread and Pool Manager
- [ ] 2022.09.28  [Python] lru_cache
- [ ] 2022.09.28  [Python] Object class __slots__를 이용한 성능 개선
- [ ] 2022.08.14  [Python] Concurrency Thread Decorator - 3
- [ ] 2022.08.12  [Python] Concurrency PDF 파일 생성  - 2
- [ ] 2022.08.12  [Python] Concurrency 어떤 경우에 어떤 것을 사용하는게 좋을까 - 1
- [ ] 2022.07.09  [Python] Thread와 Async를 이용한 비동기 방법
- [ ] 2021.11.25  [Python] 파이썬 multiprocessing
- [ ] 2021.11.25  [Python] 파이썬 비동기 I/O
- [ ] 2021.11.15  [Python] 사전(dict) 와 셋(set) 의 성능
- [ ] 2021.11.12  [Python] 튜플(tuple) 성능
- [ ] 2021.11.12  [Python] 리스트(list) 성능
- [ ] 2021.11.12  [Python] 프로파일링 cProfile, memory_profiler
- [ ] 2021.11.09  [Python] 검색 방법 profile 해보기

**→ Python/기초** (9편)

- [ ] 2022.10.31  [Python] Linter 비교
- [ ] 2022.07.08  [Python] DTO, Dataclass Validate 방법
- [ ] 2022.01.03  [Python] __slots__ method
- [ ] 2021.12.23  [Python] __new__ method
- [ ] 2021.01.22  CentOS pyenv 설치
- [ ] 2021.01.15  [Python] builtin dir() 함수
- [ ] 2021.01.08  [Python] builtin all() 함수
- [ ] 2021.01.07  [Python] builtin abs() 함수
- [ ] 2019.10.22  PIP 꼬임

**→ Python/라이브러리** (4편)

- [ ] 2022.07.23  [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 3
- [ ] 2022.07.13  [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 2
- [ ] 2022.07.13  [Python] 음성인식(Speech Recognition) 과 TTS 구현 - 1
- [ ] 2022.02.05  Python 에서 go 함수 사용 하는 방법

**→ 알고리즘** (1편)

- [ ] 2022.05.12  [Python] 후위표기법(postifx) 계산 코드


### `IT/Web` — 18편 → 3곳

**→ 네트워크** (9편)

- [ ] 2025.04.01  HTTP (Hypertext Transfer Protocol) 개념알기, HTTP/3
- [ ] 2024.12.25  HTTP (Hypertext Transfer Protocol) 개념알기, HTTP/2
- [ ] 2024.12.24  HTTP (Hypertext Transfer Protocol) 개념알기
- [ ] 2021.01.19  캐시 (Cache)  ⚠️ '캐시 (Cache)' — HTTP 캐시인지 애플리케이션 캐시인지에 따라 데이터베이스/NoSQL·검색으로 갈 수도
- [ ] 2021.01.15  DNS(Domain Name System) 작동원리
- [ ] 2021.01.15  브라우저 동작 원리
- [ ] 2021.01.14  HTTP Response Status Code (HTTP 응답 상태 코드)
- [ ] 2021.01.13  HTTP Request Method (HTTP 요청 방법)
- [ ] 2021.01.13  HTTP (HyperText Transfer Protocol) 란?

**→ 보안** (8편)

- [ ] 2023.05.18  [Web Hacking] Challange 54 풀이
- [ ] 2023.05.05  [Web Hacking] Challange 24 풀이
- [ ] 2023.05.01  [Web Hacking] Challange 16 풀이
- [ ] 2023.05.01  [보안] Cookie bomb attack
- [ ] 2023.04.30  [Web Hacking] Challange 26 풀이
- [ ] 2023.04.30  [Web Hacking] Challange 15 풀이
- [ ] 2023.04.13  [보안] XSS HTML Image 태그 주의할 점 - 2
- [ ] 2023.04.08  [보안] XSS HTML Image 태그 주의할 점

**→ 기록** (1편)

- [ ] 2021.01.13  2020년 백엔드(Back-end) 개발자 로드맵


### `OS/Centos` — 10편 → 3곳

**→ 인프라/리눅스** (6편)

- [ ] 2021.02.04  Cent OS 6 버전 yum 에러
- [ ] 2019.10.23  설치 에러 발생시 대처
- [ ] 2019.10.22  fail2ban  ⚠️ fail2ban — 침입 차단 도구라 보안으로 볼 수도
- [ ] 2019.10.22  Centos 파일, 디렉토리 찾기
- [ ] 2019.10.22  파이선, 쉘스크립트 윈도우 -> 리눅스 되었을때 발생하는 문제
- [ ] 2019.10.22  쉘 접속 지연 문제 해결 방법

**→ 인프라/모니터링** (2편)

- [ ] 2021.04.09  [CentOS] CPU, Memory 사용량 로그
- [ ] 2021.04.08  [CentOS 7] Prometheus + Grafana 설치

**→ 네트워크** (2편)

- [ ] 2019.10.22  CentOS 7 / 고정 IP 설정하는 방법
- [ ] 2019.10.22  Centos 6, 7 포트 추가


### `Database/MySQL` — 21편 → 2곳

**→ 데이터베이스/MySQL** (17편)

- [ ] 2024.02.15  [MySQL] Table lock 조회 쿼리
- [ ] 2023.12.24  [MySQL] GROUP BY Optimization
- [ ] 2023.12.06  [MySQL] ORDER BY Optimization
- [ ] 2023.08.24  [MySQL] Show Index
- [ ] 2022.05.09  [MySQL] binlog to SQL(텍스트) 변환
- [ ] 2020.07.14  MariaDB sharding using docker
- [ ] 2019.10.22  MySQL Replication 연결
- [ ] 2019.10.22  MySQL DB 명세서 쿼리 작성
- [ ] 2019.10.22  MySQL innodb 버퍼 할당 에러
- [ ] 2019.10.22  MySQL 프로시저 디버그
- [ ] 2019.10.22  MySQL error 1364 Field doesn't have a default values
- [ ] 2019.10.22  MySQL Dump시 테이블 Lock 에러
- [ ] 2019.10.22  MySQL 접속 유저 추가
- [ ] 2019.10.22  MySQL 5.7 설정 튜닝
- [ ] 2019.10.22  MySQL's Storage Engines - InnoDB Engine
- [ ] 2019.10.22  프로시저 언제 사용해야 하나?
- [ ] 2019.10.22  MySQL's Storage Engies - MyISAM Engine

**→ 데이터베이스/DB 이론** (4편)

- [ ] 2019.10.22  Indexing for High Performance
- [ ] 2019.10.22  데이터 베이스 설계 프로세스
- [ ] 2019.10.22  Isolation level (트랜잭션 고립(격리) 수준)
- [ ] 2019.10.22  트랜잭션 너는 누구니?


### `IT/알고리즘` — 14편 → 2곳

**→ 알고리즘** (13편)

- [ ] 2022.01.08  [백준] 4963 파이썬(python)
- [ ] 2022.01.08  [백준] 2468 파이썬(python)
- [ ] 2022.01.08  [백준] 1697 파이썬(python)
- [ ] 2022.01.08  [백준] 11403 파이썬(python)
- [ ] 2022.01.08  [백준] 9372 파이썬(python)
- [ ] 2022.01.08  [백준] 7569 파이썬(python)
- [ ] 2021.11.07  [Python] 백준 11724 - 연결 요소의 개수
- [ ] 2021.11.06  [Python] 백준 7576 - 토마토
- [ ] 2021.11.06  [Python] 백준 1012 - 유기농 배추
- [ ] 2021.11.06  [Python] 백준 2667 - 단지번호붙이기
- [ ] 2021.01.23  프로그래머스 - 가장 큰 정사각형 찾기
- [ ] 2021.01.22  프로그래머스 - 나머지 한 점
- [ ] 2021.01.22  프로그래머스 - 순열 검사

**→ 아키텍처** (1편)

- [ ] 2025.03.29  Consistent hashing, 일관된 해싱


### `Kotlin & Java/Spring` — 10편 → 2곳

**→ 인프라/쿠버네티스** (6편)

- [ ] 2026.05.09  K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 3편: HikariCP 설정으로인한 Socket 메모리 누수  ⚠️ OOMKilled 3부작 — Spring Boot 앱 문제이지만 K8s 운영 트러블슈팅으로 판단
- [ ] 2026.04.21  K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 2편: K8s 팟 힙 덤프 추출과 논힙 메모리 추적
- [ ] 2026.04.06  K8s 환경에서 발생한 Spring Boot 컨테이너 OOMKilled 추적기 - 1편: OOM 레벨 구분과 QoS 확인
- [ ] 2026.03.27  K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 3편: Argo Workflows로 스케줄링하기  ⚠️ Argo 전환 3부작 — Spring Batch 설계가 절반이지만 K8s 스케줄링이 주제
- [ ] 2026.03.27  K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 2편: Spring Batch REST API 서버 설계
- [ ] 2026.03.27  K8s CronJob 기반 Spring Batch, Argo Workflows로 전환하기 - 1편: CronJob 문제와 스케줄러 선택

**→ Kotlin·Spring** (4편)

- [ ] 2025.12.01  다중 DataSource 환경에서 장애 격리하기: LazyConnectionDataSourceProxy 활용기
- [ ] 2024.07.28  Kotlin + Spring Boot 에서 data class 구현으로 Validation 로직 작성하기
- [ ] 2024.02.06  Pessimistic Locking in JPA
- [ ] 2023.03.22  [Code Execution API] 1. 프로그래밍 코드 실행 API 만들어보기


### `IT/Git` — 9편 → 2곳

**→ 개발 도구/Git** (8편)

- [ ] 2026.02.05  Git Worktree 주요 명령어 정리 (add / list / remove)
- [ ] 2023.12.12  [Git] .gitignore 적용이 안되는 경우
- [ ] 2023.09.13  Jetbrains IDE용 Git 팁
- [ ] 2022.07.21  Git Commit Message Convention 정리
- [ ] 2021.08.19  Git 프로젝트 별로 다른 계정 사용하기
- [ ] 2021.02.18  Git Branch 를 통한 Gitflow
- [ ] 2021.02.17  Git Branch 사용법
- [ ] 2021.02.17  Gitlab 에서 Github 로 저장소 log 유지하며 옮기기

**→ 인프라/CI·CD** (1편)

- [ ] 2022.02.05  Github Action


### `Python/Open Source` — 6편 → 2곳

**→ Python/라이브러리** (4편)

- [ ] 2023.04.04  [Python] 파이썬 출력 문자 색 변경하기
- [ ] 2023.03.14  ChatGPT를 이용한 간단한 Web App 만들기 (python, streamlit)  ⚠️ ChatGPT + streamlit 웹앱 — AI로 볼 수도
- [ ] 2021.08.12  [Python] Colorful print
- [ ] 2021.01.13  [Python 오픈소스] Diagrams

**→ 코드 품질/테스트** (2편)

- [ ] 2023.03.15  [Locust] 2. Locust를 통한 언어와 프레임워크 별 테스트
- [ ] 2023.03.15  [Locust] 1. Locust 부하 테스트 툴(load testing tool)


### `OS/Ubuntu` — 3편 → 2곳

**→ 데이터베이스/MySQL** (2편)

- [ ] 2021.06.17  [Ubuntu 20.04] MySQL 5.6.xx 설치
- [ ] 2021.01.15  [Ubuntu 18] docker 를 이용한 MariaDB Sharding (샤딩)

**→ 네트워크** (1편)

- [ ] 2022.05.16  Ubuntu 20.04 고정 IP 할당 방법


---

## 4단계 — 정렬 순서 잡기

카테고리 관리에서 드래그로 1단계 목록 순서와 같게 맞춘다. 1단계에서 순서대로 만들었으면 확인만 하면 된다.

**활성 주력 → 대형 아카이브 → 잡문** 순이다. 이걸 빠뜨리면 개편 효과의 절반이 날아간다 — 사이드바 맨 위가 3~5년 전 연재물로 채워진다.

- [ ] 상위 11종 순서 확인
- [ ] 각 상위 안의 하위 순서 확인

---

## 5단계 — 뒷정리

- [ ] **기존 카테고리를 전부 지운다** — 여기까지 왔으면 기존 트리 47줄이 모두 0편이다. `Design Pattern`처럼 처음부터 비어 있던 것도 함께 사라진다
- [ ] **비공개 글 3편**(`비공개용`)을 확인해 배치하거나 비공개인 채로 둔다 — 크롤링에 잡히지 않아 이 목록에 없다
- [ ] 블로그를 열어 사이드바 카테고리 트리를 눈으로 확인한다

---

## 6단계 — 저장소에 반영

```bash
/blog-census          # data/categories.json · posts.json 재생성
```

- [ ] `DECISIONS.md` §3 카테고리 절을 새 값으로 다시 쓴다 (⚠️ 개편 대기 표시 제거)
- [ ] `DECISIONS.md` 미결 8을 완료 처리한다
- [ ] `DESIGN.md` §6.2 `data-cat` 접두 선택자 값을 새 상위 11종으로 교체한다
- [ ] 미결 6(기본 이미지 11장 도안) 착수 — 이제 카테고리가 확정됐다

---

## 작업 중 판단이 필요한 글

제목만으로 분류해서 원문을 봐야 확정되는 것들이다. 위 목록에서 ⚠️ 로 표시해 뒀다.
**옮기기 전에 글을 한 번 열어 보고**, 다르게 판단되면 그쪽으로 옮긴다.

| 글 | 넣어 둔 곳 | 이럴 땐 이쪽으로 |
|---|---|---|
| 캐시 (Cache) | 웹·보안/HTTP | 애플리케이션 캐시 얘기면 → 데이터/NoSQL·검색 |
| OOMKilled 추적기 3부작 | 인프라/쿠버네티스 | Spring 설정 얘기가 중심이면 → 백엔드/Kotlin·Spring |
| Argo Workflows 전환 3부작 | 인프라/쿠버네티스 | Spring Batch 설계가 중심이면 → 백엔드/Kotlin·Spring |
| JVM GC 3부작 | 백엔드/Kotlin·Spring | 순수 런타임 얘기면 → `JVM` 상위를 따로 만들 수도 |
| ChatGPT를 이용한 간단한 Web App | Python/라이브러리 | AI 활용이 중심이면 → AI/LLM 활용 |
| 속도의 병목이 이동하고 있다 | AI/LLM 활용 | 에세이에 가까우면 → 기록 |
| 토끼책 2편 (객체지향의 사실과 오해) | 백엔드/설계 원칙 | 독서 기록으로 보고 싶으면 → 기록 |
| batch 프로그램으로 host 변경하기 | 개발 도구/개발 환경 | hosts 파일이 주제면 → 인프라/네트워크 |
| fail2ban | 인프라/리눅스 | 침입 차단이 주제면 → 웹·보안/보안 |

**바꾸기로 했다면** `scripts/remap-categories.py`의 해당 인덱스를 옮기고 다시 돌린다 — 매핑과 문서가 같이 갱신된다.

