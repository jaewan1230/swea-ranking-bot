import argparse
import sys
from collections import defaultdict
from pathlib import Path

from playwright.sync_api import sync_playwright

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

SUBMIT_STATUS_URL = "https://swexpertacademy.com/main/talk/solvingClub/problemBoxSubmitStatusList.do"
DEFAULT_AUTH_FILE = Path(__file__).parent / "swea_auth.json"
PAGE_SIZE = 30
MAX_PAGES = 50


def save_login_session(auth_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://swexpertacademy.com/main/main.do")
        input("SWEA에 로그인한 뒤 이 창에서 Enter를 누르세요...")
        context.storage_state(path=str(auth_path))
        browser.close()
    print(f"로그인 세션 저장됨: {auth_path}")


def collect_pass_counts(solveclub_id: str, prob_box_id: str, auth_path: Path) -> dict[str, set[str]]:
    passed = defaultdict(set)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(auth_path))
        page = context.new_page()
        page.set_default_timeout(15000)

        for left_page in range(1, MAX_PAGES + 1):
            url = f"{SUBMIT_STATUS_URL}?solveclubId={solveclub_id}&probBoxId={prob_box_id}&leftPage={left_page}"
            page.goto(url)
            page.select_option("select", str(PAGE_SIZE))
            page.wait_for_load_state("networkidle")

            rows = page.locator(".box-list-inner > .inner_list:has(.inner_list_left .name)")
            row_count = rows.count()
            if row_count == 0:
                break

            for i in range(row_count):
                row = rows.nth(i)
                nickname = row.locator(".inner_list_left .name").text_content().strip()
                row.locator(".btn_detial").click()
                detail = row.locator("xpath=following-sibling::div[contains(@class,'inner_list_detail')][1]")
                detail.wait_for(state="visible")

                submissions = detail.locator(".problem_smt_detail")
                for j in range(submissions.count()):
                    block = submissions.nth(j)
                    header = block.locator(".battle-infobox-title").text_content().strip()
                    problem_no = header.split()[0]
                    result_text = block.locator("li:has-text('결과')").text_content().strip()
                    if result_text.startswith("Pass"):
                        passed[nickname].add(problem_no)

            if row_count < PAGE_SIZE:
                break

        browser.close()

    return passed


def format_ranking_table(passed: dict[str, set[str]], top_n: int = 3) -> str:
    ranking = sorted(passed.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    medals = ["🥇 1위", "🥈 2위", "🥉 3위"]

    lines = [
        "| **순위** | **이름** | **푼 문제 수** |",
        "|:-----|:---------|---------:|",
    ]

    rank = 0
    prev_count = None
    for nickname, problems in ranking:
        if len(problems) != prev_count:
            rank += 1
        if rank > top_n:
            break
        prev_count = len(problems)
        label = medals[rank - 1] if rank <= len(medals) else f"{rank}위"
        lines.append(f"| **{label}** | {nickname} | {len(problems)} |")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SWEA Solving Club Problem Box 제출현황을 스크래핑해 주간 랭킹을 집계한다.")
    parser.add_argument("--login", action="store_true", help="SWEA 로그인 세션을 저장한다 (최초 1회, 이후 만료 시 재실행)")
    parser.add_argument("--solveclub-id", help="집계할 Solving Club ID")
    parser.add_argument("--prob-box-id", help="집계할 Problem Box ID")
    parser.add_argument("--nickname", help="특정 닉네임만 집계 (테스트용)")
    parser.add_argument("--auth-file", default=str(DEFAULT_AUTH_FILE))
    args = parser.parse_args()

    auth_path = Path(args.auth_file)

    if args.login:
        save_login_session(auth_path)
    else:
        if not args.solveclub_id or not args.prob_box_id:
            raise SystemExit("--solveclub-id 와 --prob-box-id 를 지정해야 합니다")
        if not auth_path.exists():
            raise SystemExit(f"{auth_path} 가 없습니다. 먼저 --login 으로 로그인 세션을 저장하세요.")
        passed = collect_pass_counts(args.solveclub_id, args.prob_box_id, auth_path)
        if args.nickname:
            count = len(passed.get(args.nickname, set()))
            print(f"{args.nickname}: Pass {count}개")
        else:
            print(format_ranking_table(passed))
