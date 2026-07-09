# SWEA Ranking Bot

[SW Expert Academy](https://swexpertacademy.com) Solving Club의 Problem Box 제출현황을 스크래핑해서, 클럽 멤버별 주간 Pass 문제 수 랭킹을 Mattermost에 공유하기 좋은 Markdown 표로 출력하는 CLI 도구.

스터디나 사내/교육 코호트에서 SWEA Solving Club을 돌리고 있는데, "누가 이번 주에 몇 문제 풀었는지"를 매번 수동으로 확인하기 번거로운 경우에 쓰기 위해 만들었다. Problem Box 하나(예: 그 주에 등록한 문제들)를 지정하면, 멤버별 제출 결과를 펼쳐서 Pass한 문제 수를 집계하고 Mattermost 공지에 붙여넣기 좋은 Markdown 랭킹 표로 출력한다.

## 사용 시나리오

예를 들어 매주 SWEA Solving Club에 알고리즘 Problem Box를 만들고, 주간 풀이 결과를 Mattermost 채널에 공유하는 흐름에서 사용할 수 있다.

1. SWEA Solving Club에 이번 주 Problem Box를 만든다.
2. 주간 풀이가 끝나면 이 도구로 멤버별 Pass 문제 수를 집계한다.
3. 출력된 Markdown 표를 Mattermost 공지 메시지에 붙여넣어 랭킹을 공유한다.

이 도구는 Mattermost에 직접 메시지를 전송하지 않는다. 현재는 Mattermost에서 표로 렌더링되기 좋은 Markdown을 생성하는 데 집중한다.

## 설치

Python 3.10 이상을 권장한다.

```
pip install -r requirements.txt
python -m playwright install chromium
```

## GUI 사용법

터미널이 익숙하지 않은 코치는 GUI를 실행하면 된다.

```
python swea_ranking_gui.py
```

1. [SWEA 로그인 / 세션 갱신]을 눌러 SWEA에 로그인한다.
2. SWEA Problem Box URL을 붙여넣고 [URL에서 ID 가져오기]를 누른다.
3. [랭킹 집계하기]를 눌러 결과를 만든다.
4. 필요한 문구를 편집한 뒤 [결과 복사]를 눌러 Mattermost에 붙여넣는다.

Problem Box 상세 페이지나 제출현황 페이지 URL을 그대로 붙여넣으면 `solveclubId`, `probBoxId`를 자동으로 채운다.

```
https://swexpertacademy.com/main/talk/solvingClub/problemBoxDetail.do?solveclubId=...&probBoxId=...
https://swexpertacademy.com/main/talk/solvingClub/problemBoxSubmitStatusList.do?solveclubId=...&probBoxId=...
```

GUI의 로그인 세션과 최근 입력값은 저장소 폴더가 아니라 `%APPDATA%\swea-ranking-bot`에 저장된다.

선택으로 `%APPDATA%\swea-ranking-bot\roster.json`에 닉네임별 지역을 적어두면 표의 이름 열을 `이름 (지역)`으로 표시한다.

```json
{
  "user_a": "광주",
  "user_b": "서울"
}
```

## CLI 사용법

```
python swea_ranking_bot.py --login
python swea_ranking_bot.py --solveclub-id <Solving Club ID> --prob-box-id <Problem Box ID> --nickname <닉네임>   # 개별 테스트
python swea_ranking_bot.py --solveclub-id <Solving Club ID> --prob-box-id <Problem Box ID>                        # 전체 집계
```

`--login`은 최초 1회(또는 세션 만료 시) 실행 — 브라우저가 뜨면 SWEA에 로그인 후 터미널에서 Enter.
로그인 세션은 `swea_auth.json`에 저장되며 `.gitignore`로 제외되어 커밋되지 않는다. SWEA 비밀번호는 어디에도 저장하지 않는다.

`--solveclub-id`, `--prob-box-id`는 해당 Solving Club/Problem Box 페이지 URL의 쿼리 파라미터에서 확인할 수 있다
(`.../problemBoxSubmitStatusList.do?solveclubId=...&probBoxId=...`).

### 표시 이름 / 지역 표기

SWEA 닉네임은 보통 `이름_학번`(예: `박재완_1328704`) 형식이라, 랭킹 표에는 `_학번` 부분을 자동으로 잘라내고 이름만 표시한다.

지역까지 함께 표시하고 싶다면(`이름 (지역)` 형식) `roster.json` 파일을 만들어 닉네임→지역 매핑을 넣으면 된다. `roster.example.json`을 복사해서 시작하면 된다:

```
cp roster.example.json roster.json
```

```json
{
  "박재완_1328704": "대전",
  "유승준_1430673": "대전"
}
```

`roster.json`은 실제 인원 정보(개인정보)가 들어가므로 `.gitignore`에 포함되어 있어 커밋되지 않는다. 파일이 없으면 지역 없이 이름만 표시된다. `--roster-file`로 다른 경로를 지정할 수도 있다(기수가 바뀌면 새 roster 파일로 교체).

## Windows exe 빌드

릴리즈용 exe는 PyInstaller로 만들 수 있다. Playwright 브라우저 의존성이 있어 단일 exe보다 기본 폴더 배포를 권장한다.

```
pip install pyinstaller
python -m PyInstaller --noconfirm --clean --windowed --name "SWEA Ranking Bot" swea_ranking_gui.py
```

빌드가 끝나면 `dist/SWEA Ranking Bot/` 폴더를 zip으로 묶어 GitHub Releases에 첨부한다.

## 출력 예시

Mattermost 메시지에 제목과 안내 문구를 적고, 아래 표를 붙여넣으면 된다.

```
| **순위** | **이름** | **푼 문제 수** |
|:-----|:---------|---------:|
| **🥇 1위** | user_a | 5 |
| **🥈 2위** | user_b | 4 |
| **🥈 2위** | user_c | 4 |
| **🥉 3위** | user_d | 1 |
```

## 동작 원리

로그인 세션을 재사용하는 헤드리스 Chromium(Playwright)으로 제출현황 페이지를 열고, 멤버별 행의 "상세보기"를 클릭해 펼쳐지는 제출 상세(문제번호, 결과)를 읽어 집계한다. 별도의 비공개 API를 호출하지 않고 실제 사용자가 클릭하는 흐름을 그대로 재현한다.

## 트러블슈팅

개발·운영 중 겪은 문제와 해결 방법을 기록한다. 새로운 이슈를 만나면 여기에 계속 추가할 것.

- **일반 SWEA 문제 링크로 풀면 집계에 안 잡힘**: Problem Box에 등록된 문제여야 그 박스의 "제출현황"에 잡힌다. 공지에는 반드시 Problem Box 등록 후 생성되는 클럽 전용 링크(`talk/solvingClub/problemView.do?...probBoxId=...`)를 써야 한다. 일반 문제 링크(`code/problem/problemDetail.do`)로 풀면 Solving Club 제출현황에 반영되지 않는다.
- **로그인 세션이 만료되면 무한 대기**: 세션이 만료되면 페이지가 익명 로그인 페이지(`identity/anonymous/loginPage.do`)로 리다이렉트되는데, 이를 감지하는 로직이 없어 이후 셀렉터 대기가 타임아웃까지 계속 걸린다. `--login`을 다시 실행해 세션을 갱신하면 해결된다. (세션 만료 자동 감지는 아직 구현 안 됨 — TODO)
- **페이지네이션이 무한 루프에 빠질 뻔함**: 처음엔 "Next" 버튼의 visibility/class를 보고 마지막 페이지를 판단했는데 이 방식이 불안정했다. 지금은 `row_count < PAGE_SIZE`(한 페이지에 표시되는 행 수가 페이지 크기보다 적으면 마지막 페이지)로 판단하고, 추가로 `MAX_PAGES` 상한과 `page.set_default_timeout(15000)`을 둬서 어떤 경우든 무한정 멈춰있지 않도록 안전장치를 걸었다.
- **랭킹 표에 메달 이모지가 들어가면 Windows 콘솔에서 크래시**: cp949 코드페이지를 쓰는 한글 Windows 콘솔은 🥇 같은 이모지를 출력하지 못해 `UnicodeEncodeError`가 난다. 스크립트 시작 시 `sys.stdout.reconfigure(encoding="utf-8")`로 강제 UTF-8 출력하도록 해서 해결했다.
- **DOM 구조 파악 중 Problem Box 이름이 실수로 바뀜**: 브라우저 자동화로 클래스명을 조사하던 중 실수로 Problem Box 이름이 변경된 적이 있다. Problem Box 관리 화면에서 클릭/입력 자동화를 할 때는 결과를 스크린샷으로 매번 확인할 것.
- **닉네임이 `이름_학번` 형식이라 그대로 쓰면 지저분함**: 정규식(`_[A-Za-z]*\d+$`)으로 학번 suffix를 잘라 이름만 표시한다. 지역까지 표시하려면 [표시 이름 / 지역 표기](#표시-이름--지역-표기) 참고.

## License

MIT
