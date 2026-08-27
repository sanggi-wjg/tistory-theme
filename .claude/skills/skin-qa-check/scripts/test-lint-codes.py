#!/usr/bin/env python3
"""린트가 내는 코드가 전부 SKILL.md의 규칙 표에 있는가.

왜 필요한가 — 2026-08-27 셀프 리뷰에서 `SUB008`·`SUB009`·`TIS003`·`TIS004`가
표에 없는 것을 찾았다. **하필 네 번의 배포 사고에서 태어난 네 규칙이다**
(결정 29·34·35·36-b). 표가 범위 표기(`SUB001~007`)를 쓰는 탓에 뒤에 붙인 코드가
조용히 범위 밖으로 빠져나간 것이다.

이건 화면에도 린트에도 안 나타난다. 에이전트는 그 표를 보고 "무엇이 이미
덮여 있나"를 판단하므로, **안 적힌 축은 안 덮인 축으로 읽힌다** — 이미 있는
검사를 다시 만들거나, 뚫려 있다고 믿고 배포한다.

폐기한 코드는 표에만 남는다(`AREA003`). 그건 오류가 아니라 정상이다 —
번호를 재사용하지 않으므로 «왜 비어 있는지»가 표에 남아 있어야 한다.

  python3 .claude/skills/skin-qa-check/scripts/test-lint-codes.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "lint.py")
SKILL = os.path.abspath(os.path.join(HERE, "..", "SKILL.md"))

PREFIX = r"(?:SUB|AREA|BND|TOK|INL|TIS|HLJS|ROB|A11Y|SEO|CAT)"


def codes_in_lint(src):
    """err()/warn()의 첫 인자로 실제로 넘어가는 코드만 센다.

    주석이나 설명문에 적힌 코드 이름은 «내는» 것이 아니다. 그것까지 세면
    폐기한 코드를 주석으로 설명하는 순간 이 테스트가 깨진다.
    """
    return set(re.findall(r"""\b(?:err|warn)\(\s*["'](%s\d{3})["']""" % PREFIX, src))


def codes_in_doc(doc):
    """**규칙 표의 첫 칸**이 적은 코드. 범위 표기(`SUB001~007`)를 펼친다.

    ⚠ 문서 전체에서 찾으면 안 된다. 산문에 이름이 스치기만 해도 «적혀 있다»로
      세어져, 표에서 줄이 빠져도 통과한다. 첫 판이 정확히 그랬고 —
      이 테스트를 소개하는 문단에 `TIS004`를 적은 탓에 그 줄을 지워도 초록불이었다.
      «규칙이 있는가»가 아니라 «그 규칙이 조건을 재현하는가»를 물어야 한다는
      이 저장소의 규범이 테스트 자신에게도 적용된다.
    """
    found = set()
    for line in doc.split("\n"):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        if len(cells) < 3:
            continue
        head = cells[1]
        found |= set(re.findall(r"\b(%s\d{3})\b" % PREFIX, head))
        for m in re.finditer(r"`(%s)(\d{3})~(\d{3})`" % PREFIX, head):
            prefix, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
            for n in range(lo, hi + 1):
                found.add("%s%03d" % (prefix, n))
    return found


def main():
    for p in (LINT, SKILL):
        if not os.path.exists(p):
            print("❌ 파일이 없다: %s" % p)
            sys.exit(1)

    emitted = codes_in_lint(open(LINT, encoding="utf-8").read())
    documented = codes_in_doc(open(SKILL, encoding="utf-8").read())

    if not emitted:
        # 파서가 조용히 빈 집합을 읽으면 «전부 문서화됨»으로 통과해 버린다.
        # 검사가 꺼지는 것과 통과하는 것은 다른 일이다 (결정 40).
        print("❌ lint.py에서 코드를 하나도 읽지 못했다. err()/warn() 호출 모양이 바뀌었나.")
        sys.exit(1)

    missing = sorted(emitted - documented)
    doc_only = sorted(documented - emitted)

    print("린트가 err/warn으로 내는 코드 %d종 · SKILL.md가 적은 코드 %d종"
          % (len(emitted), len(documented)))
    if doc_only:
        # 두 가지가 섞인다 — 폐기한 코드(AREA003)와 info로만 내는 코드(SEO005).
        # 둘 다 표에 남아 있는 것이 정상이라 실패로 세지 않는다.
        print("  표에만 있음(폐기 또는 info 전용): %s" % ", ".join(doc_only))

    if missing:
        print("\n❌ SKILL.md 규칙 표에 없는 코드 %d종: %s" % (len(missing), ", ".join(missing)))
        print("   에이전트는 이 표로 «무엇이 이미 덮여 있나»를 판단한다.")
        print("   안 적힌 축은 안 덮인 축으로 읽힌다.")
        sys.exit(1)

    print("\n실패 0건")


if __name__ == "__main__":
    main()
