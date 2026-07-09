import json
import os
import sys
import threading
from pathlib import Path


def configure_playwright_browsers() -> None:
    if not getattr(sys, "frozen", False):
        return

    bundled_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    bundled_browsers = bundled_root / "ms-playwright"
    if bundled_browsers.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(bundled_browsers))


def configure_tk_libraries() -> None:
    candidates = []
    if getattr(sys, "frozen", False):
        bundled_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        candidates.append((bundled_root / "_tcl_data", bundled_root / "_tk_data"))
    else:
        prefix = Path(sys.prefix)
        candidates.append((prefix / "Library" / "lib" / "tcl8.6", prefix / "Library" / "lib" / "tk8.6"))

    for tcl_dir, tk_dir in candidates:
        if (tcl_dir / "init.tcl").exists() and (tk_dir / "tk.tcl").exists():
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
            os.environ.setdefault("TK_LIBRARY", str(tk_dir))
            return


configure_tk_libraries()
configure_playwright_browsers()

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from playwright.sync_api import sync_playwright

from swea_ranking_bot import DEFAULT_ROSTER_FILE, collect_pass_counts, format_ranking_table, load_roster, parse_swea_ids

APP_NAME = "swea-ranking-bot"
APP_DIR = Path(os.environ.get("APPDATA") or Path.home()) / APP_NAME
AUTH_FILE = APP_DIR / "swea_auth.json"
CONFIG_FILE = APP_DIR / "config.json"
LOGIN_URL = "https://swexpertacademy.com/main/main.do"
DEFAULT_TITLE = "M월 D일 ~ M월 D일 알고리즘 랭킹"
DEFAULT_INTRO = "이번주의 15기 실습코치 알고리즘 풀이 주간 랭킹을 발표합니다!!! :thumbup:"
DEFAULT_OUTRO = "이번주도 화이팅해보아요 :wagom:"
OLD_DEFAULT_TITLE = "알고리즘 랭킹"
OLD_DEFAULT_INTRO = "이번주의 알고리즘 풀이 주간 랭킹을 발표합니다!!!"
OLD_DEFAULT_OUTRO = "이번주도 화이팅해보아요."
ROSTER_EXAMPLE = {
    "김싸피_1234567": "구미",
    "이싸피_2345678": "서울",
    "박싸피_3456789": "광주",
}


ROSTER_FILE = DEFAULT_ROSTER_FILE


class SweaRankingApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SWEA Ranking Bot")
        self.geometry("860x760")
        self.minsize(760, 640)

        config = self._load_config()
        self.url_var = tk.StringVar(value=config.get("url", ""))
        self.solveclub_id_var = tk.StringVar(value=config.get("solveclub_id", ""))
        self.prob_box_id_var = tk.StringVar(value=config.get("prob_box_id", ""))
        self.top_n_var = tk.StringVar(value=str(config.get("top_n", 3)))
        self.title_var = tk.StringVar(value=self._config_value(config, "title", DEFAULT_TITLE, OLD_DEFAULT_TITLE))
        self.intro_var = tk.StringVar(value=self._config_value(config, "intro", DEFAULT_INTRO, OLD_DEFAULT_INTRO))
        self.outro_var = tk.StringVar(value=self._config_value(config, "outro", DEFAULT_OUTRO, OLD_DEFAULT_OUTRO))
        self.status_var = tk.StringVar(value=self._initial_status())

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(7, weight=1)

        title = ttk.Label(main, text="SWEA Ranking Bot", font=("", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        description = ttk.Label(
            main,
            text="SWEA Solving Club 랭킹을 집계해 Mattermost에 붙여넣기 좋은 Markdown으로 만듭니다.",
        )
        description.grid(row=1, column=0, sticky="w", pady=(4, 14))

        login_frame = ttk.Frame(main)
        login_frame.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        login_frame.columnconfigure(0, weight=1)
        ttk.Label(login_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        self.login_button = ttk.Button(login_frame, text="SWEA 로그인 / 세션 갱신", command=self.login)
        self.login_button.grid(row=0, column=1, sticky="e", padx=(12, 0))

        url_frame = ttk.LabelFrame(main, text="SWEA Problem Box URL")
        url_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        url_frame.columnconfigure(0, weight=1)
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.parse_button = ttk.Button(url_frame, text="URL에서 ID 가져오기", command=self.parse_url)
        self.parse_button.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=10)

        ids_frame = ttk.LabelFrame(main, text="집계 대상")
        ids_frame.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ids_frame.columnconfigure(1, weight=1)
        ids_frame.columnconfigure(3, weight=1)
        ttk.Label(ids_frame, text="Solving Club ID").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=10)
        ttk.Entry(ids_frame, textvariable=self.solveclub_id_var).grid(row=0, column=1, sticky="ew", pady=10)
        ttk.Label(ids_frame, text="Problem Box ID").grid(row=0, column=2, sticky="w", padx=(16, 8), pady=10)
        ttk.Entry(ids_frame, textvariable=self.prob_box_id_var).grid(row=0, column=3, sticky="ew", pady=10)
        ttk.Label(ids_frame, text="랭킹 범위").grid(row=0, column=4, sticky="w", padx=(16, 8), pady=10)
        self.top_n_spinbox = ttk.Spinbox(ids_frame, from_=1, to=20, width=5, textvariable=self.top_n_var)
        self.top_n_spinbox.grid(row=0, column=5, sticky="w", padx=(0, 10), pady=10)

        message_frame = ttk.LabelFrame(main, text="Mattermost 메시지")
        message_frame.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        message_frame.columnconfigure(1, weight=1)
        ttk.Label(message_frame, text="제목").grid(row=0, column=0, sticky="w", padx=(10, 8), pady=(10, 4))
        ttk.Entry(message_frame, textvariable=self.title_var).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 4))
        ttk.Label(message_frame, text="안내 문구").grid(row=1, column=0, sticky="w", padx=(10, 8), pady=4)
        ttk.Entry(message_frame, textvariable=self.intro_var).grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)
        ttk.Label(message_frame, text="마무리 문구").grid(row=2, column=0, sticky="w", padx=(10, 8), pady=(4, 10))
        ttk.Entry(message_frame, textvariable=self.outro_var).grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=(4, 10))

        actions_frame = ttk.Frame(main)
        actions_frame.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        self.collect_button = ttk.Button(actions_frame, text="랭킹 집계하기", command=self.collect_ranking)
        self.collect_button.grid(row=0, column=0, padx=(0, 8))
        self.copy_button = ttk.Button(actions_frame, text="결과 복사", command=self.copy_result)
        self.copy_button.grid(row=0, column=1, padx=(0, 8))
        self.clear_button = ttk.Button(actions_frame, text="결과 초기화", command=self.clear_result)
        self.clear_button.grid(row=0, column=2)
        self.roster_button = ttk.Button(actions_frame, text="명단/지역 파일 열기", command=self.open_roster_file)
        self.roster_button.grid(row=0, column=3, padx=(8, 0))

        result_frame = ttk.LabelFrame(main, text="Mattermost에 붙여넣을 Markdown")
        result_frame.grid(row=7, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap="word", height=18, font=("Consolas", 10))
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def parse_url(self) -> None:
        raw_url = self.url_var.get().strip()
        if not raw_url:
            messagebox.showwarning("URL 필요", "SWEA Problem Box URL을 붙여넣어주세요.")
            return

        try:
            solveclub_id, prob_box_id = parse_swea_ids(raw_url)
        except ValueError as exc:
            messagebox.showerror("URL 파싱 실패", str(exc))
            self.status_var.set("URL에서 ID를 찾지 못했습니다.")
            return

        self.solveclub_id_var.set(solveclub_id)
        self.prob_box_id_var.set(prob_box_id)
        self.status_var.set("URL에서 Solving Club ID와 Problem Box ID를 가져왔습니다.")
        self._save_config()

    def login(self) -> None:
        self._set_busy(True)
        thread = threading.Thread(target=self._login_worker, daemon=True)
        thread.start()

    def _login_worker(self) -> None:
        browser = None
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            self._set_status_threadsafe("브라우저를 여는 중...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto(LOGIN_URL)

                self._set_status_threadsafe("브라우저로 돌아가 SWEA 로그인을 완료한 뒤 이 창의 [확인]을 눌러주세요.")
                if not self._ask_login_done():
                    self._set_status_threadsafe("로그인 세션 저장을 취소했습니다.")
                    return

                context.storage_state(path=str(AUTH_FILE))
                self._set_status_threadsafe("로그인 세션을 저장했습니다.")
        except Exception as exc:
            self._show_error_threadsafe("로그인 실패", self._friendly_error(exc))
            self._set_status_threadsafe("로그인에 실패했습니다.")
        finally:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            self._set_busy_threadsafe(False)

    def _ask_login_done(self) -> bool:
        event = threading.Event()
        result = {"ok": False}

        def ask() -> None:
            result["ok"] = messagebox.askokcancel(
                "SWEA 로그인",
                "1. 이 창을 닫지 말고, 열린 브라우저로 돌아가\n"
                "   SWEA 로그인을 먼저 완료해주세요.\n"
                "2. SWEA 로그인이 완료되면 이 창으로 돌아와\n"
                "   [확인]을 눌러주세요.\n\n"
                "[확인]을 누르는 순간 현재 브라우저 로그인 세션을 저장합니다.",
            )
            event.set()

        self.after(0, ask)
        event.wait()
        return result["ok"]

    def collect_ranking(self) -> None:
        solveclub_id = self.solveclub_id_var.get().strip()
        prob_box_id = self.prob_box_id_var.get().strip()
        if not solveclub_id or not prob_box_id:
            messagebox.showwarning("ID 필요", "Solving Club ID와 Problem Box ID를 입력해주세요.")
            return
        if not AUTH_FILE.exists():
            messagebox.showwarning("로그인 필요", "먼저 [SWEA 로그인 / 세션 갱신]을 눌러 로그인 세션을 저장해주세요.")
            return

        try:
            top_n = int(self.top_n_var.get())
        except ValueError:
            messagebox.showwarning("랭킹 범위 확인", "랭킹 범위는 숫자로 입력해주세요.")
            return
        if top_n < 1:
            messagebox.showwarning("랭킹 범위 확인", "랭킹 범위는 1 이상이어야 합니다.")
            return

        self._save_config()
        self._set_busy(True)
        thread = threading.Thread(
            target=self._collect_worker,
            args=(
                solveclub_id,
                prob_box_id,
                top_n,
                self.title_var.get(),
                self.intro_var.get(),
                self.outro_var.get(),
            ),
            daemon=True,
        )
        thread.start()

    def _collect_worker(
        self,
        solveclub_id: str,
        prob_box_id: str,
        top_n: int,
        title: str,
        intro: str,
        outro: str,
    ) -> None:
        try:
            self._set_status_threadsafe("집계를 시작합니다...")
            passed = collect_pass_counts(
                solveclub_id,
                prob_box_id,
                AUTH_FILE,
                progress_callback=self._set_status_threadsafe,
            )
            roster = self._load_roster()
            table = format_ranking_table(passed, roster, top_n=top_n)
            markdown = self._build_mattermost_message(title, intro, table, outro)
            self._set_result_threadsafe(markdown)

            if passed:
                self._set_status_threadsafe(f"완료: {len(passed)}명의 Pass 기록을 집계했습니다.")
            else:
                self._set_status_threadsafe("집계 결과가 없습니다. ID, 권한, 제출 여부를 확인해주세요.")
        except Exception as exc:
            self._show_error_threadsafe("집계 실패", self._friendly_error(exc))
            self._set_status_threadsafe("집계에 실패했습니다.")
        finally:
            self._set_busy_threadsafe(False)

    def copy_result(self) -> None:
        markdown = self.result_text.get("1.0", "end-1c")
        if not markdown.strip():
            self.status_var.set("복사할 결과가 없습니다.")
            return

        self.clipboard_clear()
        self.clipboard_append(markdown)
        self.status_var.set("클립보드에 복사했습니다. Mattermost에 붙여넣으면 됩니다.")

    def clear_result(self) -> None:
        self.result_text.delete("1.0", "end")
        self.status_var.set("결과를 초기화했습니다.")

    def open_roster_file(self) -> None:
        try:
            roster_path = self._ensure_roster_file()
            if hasattr(os, "startfile"):
                os.startfile(str(roster_path))
                self.status_var.set("명단/지역 파일을 열었습니다.")
            else:
                messagebox.showinfo("명단/지역 파일", f"이 파일을 편집해주세요:\n{roster_path}")
        except Exception as exc:
            messagebox.showerror("명단/지역 파일 열기 실패", self._friendly_error(exc))

    def _build_mattermost_message(self, title: str, intro: str, table: str, outro: str) -> str:
        header_lines = []
        body_parts = []

        if title.strip():
            header_lines.append(self._format_title(title))
        if intro.strip():
            header_lines.append(self._format_intro(intro))
        if header_lines:
            body_parts.append("\n".join(header_lines))

        body_parts.append(table)
        if outro.strip():
            body_parts.append(outro.strip())
        body_parts.append("---")
        return "\n\n".join(body_parts)

    def _format_title(self, title: str) -> str:
        title = title.strip()
        if title.startswith("#"):
            return title
        return f"### :white_heart: {title} :white_heart:"

    def _format_intro(self, intro: str) -> str:
        intro = intro.strip()
        if intro.startswith("#"):
            return intro
        return f"##### {intro}"

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for button in (self.login_button, self.parse_button, self.collect_button, self.roster_button):
            button.configure(state=state)

    def _set_busy_threadsafe(self, busy: bool) -> None:
        self.after(0, self._set_busy, busy)

    def _set_status_threadsafe(self, message: str) -> None:
        self.after(0, self.status_var.set, message)

    def _set_result_threadsafe(self, markdown: str) -> None:
        def update() -> None:
            self.result_text.delete("1.0", "end")
            self.result_text.insert("1.0", markdown)

        self.after(0, update)

    def _show_error_threadsafe(self, title: str, message: str) -> None:
        self.after(0, messagebox.showerror, title, message)

    def _friendly_error(self, exc: Exception) -> str:
        message = str(exc).strip()
        if "Timeout" in message:
            return (
                "SWEA 페이지 응답이 늦거나 화면 구조가 달라졌습니다.\n"
                "로그인 세션, Problem Box ID, Solving Club 권한을 확인해주세요."
            )
        if "storage state" in message.lower() or "auth" in message.lower():
            return "로그인 세션을 읽지 못했습니다. 다시 로그인해주세요."
        return message or exc.__class__.__name__

    def _initial_status(self) -> str:
        if AUTH_FILE.exists():
            return "로그인 세션 파일이 있습니다. 필요하면 세션을 갱신할 수 있습니다."
        return "로그인 세션이 없습니다. 먼저 SWEA 로그인을 진행해주세요."

    def _load_config(self) -> dict:
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _config_value(self, config: dict, key: str, default: str, old_default: str) -> str:
        value = config.get(key, default)
        if value == old_default:
            return default
        return value

    def _load_roster(self) -> dict[str, str]:
        try:
            return load_roster(ROSTER_FILE)
        except json.JSONDecodeError as exc:
            raise ValueError(f"명단/지역 파일 JSON 문법을 확인해주세요:\n{ROSTER_FILE}\n\n{exc}") from exc

    def _ensure_roster_file(self) -> Path:
        ROSTER_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not ROSTER_FILE.exists():
            ROSTER_FILE.write_text(
                json.dumps(ROSTER_EXAMPLE, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            messagebox.showinfo(
                "명단/지역 파일 생성",
                "예시 roster.json을 만들었습니다.\n닉네임과 지역을 수정한 뒤 저장해주세요.",
            )
        return ROSTER_FILE

    def _save_config(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "url": self.url_var.get().strip(),
            "solveclub_id": self.solveclub_id_var.get().strip(),
            "prob_box_id": self.prob_box_id_var.get().strip(),
            "top_n": self.top_n_var.get().strip(),
            "title": self.title_var.get(),
            "intro": self.intro_var.get(),
            "outro": self.outro_var.get(),
        }
        CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _on_close(self) -> None:
        self._save_config()
        self.destroy()


def main() -> None:
    app = SweaRankingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
