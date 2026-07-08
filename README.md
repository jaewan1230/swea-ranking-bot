# SWEA Ranking Bot

[SW Expert Academy](https://swexpertacademy.com) Solving Club의 Problem Box 제출현황을 스크래핑해서, 클럽 멤버별 주간 Pass 문제 수 랭킹을 자동으로 집계하는 CLI 도구.

스터디나 사내/교육 코호트에서 SWEA Solving Club을 돌리고 있는데, "누가 이번 주에 몇 문제 풀었는지"를 매번 수동으로 확인하기 번거로운 경우에 쓰기 위해 만들었다. Problem Box 하나(예: 그 주에 등록한 문제들)를 지정하면, 멤버별 제출 결과를 펼쳐서 Pass한 문제 수를 집계하고 Markdown 랭킹 표로 출력한다.

## 설치

```
pip install -r requirements.txt
python -m playwright install chromium
```

## 사용법

```
python swea_ranking_bot.py --login
python swea_ranking_bot.py --solveclub-id <Solving Club ID> --prob-box-id <Problem Box ID> --nickname <닉네임>   # 개별 테스트
python swea_ranking_bot.py --solveclub-id <Solving Club ID> --prob-box-id <Problem Box ID>                        # 전체 집계
```

`--login`은 최초 1회(또는 세션 만료 시) 실행 — 브라우저가 뜨면 SWEA에 로그인 후 터미널에서 Enter.
로그인 세션은 `swea_auth.json`에 저장되며 `.gitignore`로 제외되어 커밋되지 않는다. SWEA 비밀번호는 어디에도 저장하지 않는다.

`--solveclub-id`, `--prob-box-id`는 해당 Solving Club/Problem Box 페이지 URL의 쿼리 파라미터에서 확인할 수 있다
(`.../problemBoxSubmitStatusList.do?solveclubId=...&probBoxId=...`).

## 출력 예시

```
| **순위** | **이름** | **푼 문제 수** |
|:-----|:---------|---------:|
| **🥇 1위** | user_a | 5 |
| **🥈 2위** | user_b | 4 |
| **🥉 3위** | user_c | 1 |
```

## 동작 원리

로그인 세션을 재사용하는 헤드리스 Chromium(Playwright)으로 제출현황 페이지를 열고, 멤버별 행의 "상세보기"를 클릭해 펼쳐지는 제출 상세(문제번호, 결과)를 읽어 집계한다. 별도의 비공개 API를 호출하지 않고 실제 사용자가 클릭하는 흐름을 그대로 재현한다.

## License

MIT
