import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────
#  ЦВЕТА И СТИЛИ
# ──────────────────────────────────────────────
BG        = "#0d1117"
SURFACE   = "#161b22"
BORDER    = "#30363d"
ACCENT    = "#58a6ff"
ACCENT2   = "#3fb950"
DANGER    = "#f85149"
WARN      = "#d29922"
FG        = "#e6edf3"
FG_DIM    = "#8b949e"
FONT_MAIN = ("Consolas", 10)
FONT_HEAD = ("Consolas", 13, "bold")
FONT_TINY = ("Consolas", 9)

# ──────────────────────────────────────────────
#  ГЛАВНОЕ ОКНО
# ──────────────────────────────────────────────
class WebAutomatorPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WebAutomator Pro v1.0")
        self.geometry("900x680")
        self.minsize(780, 580)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.driver = None
        self.running = False
        self.commands = []

        self._build_ui()
        self._load_task_file()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── ИНТЕРФЕЙС ────────────────────────────
    def _build_ui(self):
        # ── Заголовок ──
        header = tk.Frame(self, bg=SURFACE, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="⚡ WebAutomator Pro",
                 font=("Consolas", 15, "bold"),
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=20, pady=12)
        tk.Label(header, text="v1.0  |  by PhantomBot",
                 font=FONT_TINY, bg=SURFACE, fg=FG_DIM).pack(side="left", padx=0, pady=14)

        self.status_dot = tk.Label(header, text="● ГОТОВ",
                                   font=FONT_TINY, bg=SURFACE, fg=ACCENT2)
        self.status_dot.pack(side="right", padx=20)

        # ── Разделитель ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Основная область ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        # ── Левая колонка: редактор команд ──
        lbl_cmd = tk.Label(body, text="КОМАНДЫ СЦЕНАРИЯ",
                           font=FONT_TINY, bg=BG, fg=FG_DIM)
        lbl_cmd.grid(row=0, column=0, sticky="w", pady=(0, 4))

        editor_frame = tk.Frame(body, bg=BORDER, bd=0)
        editor_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.editor = scrolledtext.ScrolledText(
            editor_frame,
            font=FONT_MAIN, bg=SURFACE, fg=FG,
            insertbackground=ACCENT,
            selectbackground=ACCENT,
            relief="flat", bd=8,
            wrap="none",
            undo=True
        )
        self.editor.pack(fill="both", expand=True)
        self._insert_placeholder()

        # ── Правая колонка ──
        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, rowspan=2, sticky="nsew")
        right.rowconfigure(3, weight=1)

        # Быстрые команды
        tk.Label(right, text="ВСТАВИТЬ КОМАНДУ",
                 font=FONT_TINY, bg=BG, fg=FG_DIM).grid(row=0, column=0, sticky="w", pady=(0, 6))

        btn_frame = tk.Frame(right, bg=BG)
        btn_frame.grid(row=1, column=0, sticky="ew")

        snippets = [
            ("🌐  Открыть URL",    "open|https://example.com"),
            ("🖱  Клик по элем.",  "click|#button-id"),
            ("⌨  Ввести текст",   "type|#input-id|текст"),
            ("⏱  Пауза (сек)",    "wait|3"),
            ("📸  Скриншот",       "screenshot|screen.png"),
            ("🔄  Обновить стр.",  "refresh|"),
            ("📜  Прокрутить вниз","scroll|bottom"),
        ]
        for label, snippet in snippets:
            b = tk.Button(btn_frame, text=label,
                          font=FONT_TINY, bg=SURFACE, fg=FG,
                          activebackground=BORDER, activeforeground=ACCENT,
                          relief="flat", cursor="hand2", anchor="w",
                          padx=10, pady=5,
                          command=lambda s=snippet: self._insert_snippet(s))
            b.pack(fill="x", pady=2)
            self._hover(b)

        # Разделитель
        tk.Frame(right, bg=BORDER, height=1).grid(row=2, column=0, sticky="ew", pady=10)

        # Лог
        tk.Label(right, text="ЛОГ ВЫПОЛНЕНИЯ",
                 font=FONT_TINY, bg=BG, fg=FG_DIM).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.log = scrolledtext.ScrolledText(
            right, font=FONT_TINY, bg=SURFACE, fg=FG_DIM,
            relief="flat", bd=8, state="disabled", height=14
        )
        self.log.grid(row=3, column=0, sticky="nsew")
        self.log.tag_config("ok",   foreground=ACCENT2)
        self.log.tag_config("err",  foreground=DANGER)
        self.log.tag_config("info", foreground=ACCENT)
        self.log.tag_config("warn", foreground=WARN)

        # ── Панель управления ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        ctrl = tk.Frame(self, bg=SURFACE, height=52)
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)

        self.btn_run = self._ctrl_btn(ctrl, "▶  ЗАПУСТИТЬ", ACCENT2, self._start)
        self.btn_run.pack(side="left", padx=12, pady=10)

        self.btn_stop = self._ctrl_btn(ctrl, "■  СТОП", DANGER, self._stop)
        self.btn_stop.pack(side="left", padx=4, pady=10)
        self.btn_stop.config(state="disabled")

        self._ctrl_btn(ctrl, "💾  Сохранить", WARN, self._save).pack(side="left", padx=4, pady=10)
        self._ctrl_btn(ctrl, "🗑  Очистить лог", FG_DIM, self._clear_log).pack(side="left", padx=4, pady=10)

        tk.Label(ctrl, text="© 2026 WebAutomator Pro  |  Справка: F1",
                 font=FONT_TINY, bg=SURFACE, fg=FG_DIM).pack(side="right", padx=16)

        self.bind("<F1>", self._show_help)

    def _ctrl_btn(self, parent, text, color, cmd):
        b = tk.Button(parent, text=text, font=FONT_TINY,
                      bg=SURFACE, fg=color,
                      activebackground=BORDER, activeforeground=color,
                      relief="flat", cursor="hand2",
                      padx=14, pady=6, command=cmd,
                      highlightbackground=color, highlightthickness=1)
        return b

    def _hover(self, widget):
        widget.bind("<Enter>", lambda e: widget.config(bg=BORDER))
        widget.bind("<Leave>", lambda e: widget.config(bg=SURFACE))

    # ── ЗАГЛУШКА В РЕДАКТОРЕ ────────────────
    def _insert_placeholder(self):
        placeholder = (
            "# WebAutomator Pro — Сценарий\n"
            "# Формат: команда|параметр1|параметр2\n"
            "#\n"
            "# Команды:\n"
            "#   open|URL           — открыть страницу\n"
            "#   click|CSS          — кликнуть элемент\n"
            "#   type|CSS|текст     — ввести текст\n"
            "#   wait|секунды       — пауза\n"
            "#   screenshot|файл   — скриншот\n"
            "#   refresh|           — обновить\n"
            "#   scroll|bottom/top  — прокрутить\n"
            "#\n"
            "# ── Пример ──────────────────────────────\n"
            "open|https://google.com\n"
            "wait|2\n"
            "type|input[name='q']|WebAutomator Pro\n"
            "click|input[value='Google Search']\n"
            "wait|3\n"
            "screenshot|result.png\n"
        )
        self.editor.insert("1.0", placeholder)

    def _insert_snippet(self, text):
        self.editor.insert("insert", text + "\n")
        self.editor.focus()

    # ── ЗАГРУЗКА / СОХРАНЕНИЕ ───────────────
    def _load_task_file(self):
        if os.path.exists("task.txt"):
            with open("task.txt", "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self._log("Загружен task.txt", "info")

    def _save(self):
        content = self.editor.get("1.0", "end-1c")
        with open("task.txt", "w", encoding="utf-8") as f:
            f.write(content)
        self._log("Сценарий сохранён в task.txt", "ok")

    # ── ЛОГ ─────────────────────────────────
    def _log(self, msg, tag="info"):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", f"[{ts}] {msg}\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    # ── СТАТУС ───────────────────────────────
    def _set_status(self, text, color):
        self.status_dot.config(text=f"● {text}", fg=color)

    # ── ЗАПУСК ───────────────────────────────
    def _start(self):
        if self.running:
            return
        self._save()
        self.running = True
        self.btn_run.config(state="disabled")
        self.btn_stop.config(state="normal")
        self._set_status("РАБОТАЕТ", WARN)
        threading.Thread(target=self._run_automation, daemon=True).start()

    def _stop(self):
        self.running = False
        self._log("Остановка по запросу пользователя", "warn")
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        self._set_status("ОСТАНОВЛЕН", DANGER)
        self.btn_run.config(state="normal")
        self.btn_stop.config(state="disabled")

    def _run_automation(self):
        try:
            options = Options()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--start-maximized")

            self._log("Запуск браузера...", "info")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })

            with open("task.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()

            total = sum(1 for l in lines if l.strip() and not l.startswith("#"))
            done = 0

            for line in lines:
                if not self.running:
                    break
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("|")
                cmd = parts[0].lower()

                try:
                    if cmd == "open":
                        url = parts[1]
                        self._log(f"Открываю: {url}", "info")
                        self.driver.get(url)

                    elif cmd == "click":
                        sel = parts[1]
                        self._log(f"Клик: {sel}", "info")
                        el = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                        el.click()

                    elif cmd == "type":
                        sel, text = parts[1], parts[2]
                        self._log(f"Ввод в {sel}: {text}", "info")
                        el = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                        el.clear()
                        el.send_keys(text)

                    elif cmd == "wait":
                        secs = int(parts[1])
                        self._log(f"Пауза {secs} сек...", "info")
                        for _ in range(secs):
                            if not self.running:
                                break
                            time.sleep(1)

                    elif cmd == "screenshot":
                        fname = parts[1] if len(parts) > 1 else "screenshot.png"
                        self.driver.save_screenshot(fname)
                        self._log(f"Скриншот сохранён: {fname}", "ok")

                    elif cmd == "refresh":
                        self._log("Обновление страницы", "info")
                        self.driver.refresh()

                    elif cmd == "scroll":
                        direction = parts[1].lower() if len(parts) > 1 else "bottom"
                        js = "window.scrollTo(0, document.body.scrollHeight);" \
                            if direction == "bottom" else "window.scrollTo(0, 0);"
                        self.driver.execute_script(js)
                        self._log(f"Прокрутка: {direction}", "info")

                    else:
                        self._log(f"Неизвестная команда: {cmd}", "warn")

                    done += 1
                    self._log(f"✓ [{done}/{total}]", "ok")

                except Exception as e:
                    self._log(f"Ошибка в строке «{line}»: {e}", "err")

            if self.running:
                self._log("══ Сценарий завершён успешно ══", "ok")
                self._set_status("ГОТОВ", ACCENT2)

        except Exception as e:
            self._log(f"Критическая ошибка: {e}", "err")
            self._set_status("ОШИБКА", DANGER)

        finally:
            self.running = False
            self.btn_run.config(state="normal")
            self.btn_stop.config(state="disabled")
            if self.driver:
                time.sleep(3)
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

    # ── СПРАВКА ─────────────────────────────
    def _show_help(self, event=None):
        win = tk.Toplevel(self)
        win.title("Справка — WebAutomator Pro")
        win.geometry("540x420")
        win.configure(bg=BG)
        win.resizable(False, False)

        tk.Label(win, text="📖  Справка по командам",
                 font=FONT_HEAD, bg=BG, fg=ACCENT).pack(pady=(16, 8))

        help_text = (
            "ФОРМАТ КОМАНД:\n"
            "  команда|параметр1|параметр2\n\n"
            "СПИСОК КОМАНД:\n"
            "  open|URL              — открыть страницу\n"
            "  click|CSS-селектор    — кликнуть элемент\n"
            "  type|CSS|текст        — ввести текст в поле\n"
            "  wait|секунды          — ждать N секунд\n"
            "  screenshot|файл.png  — сохранить скриншот\n"
            "  refresh|              — обновить страницу\n"
            "  scroll|bottom/top     — прокрутить страницу\n\n"
            "ПРИМЕРЫ CSS-СЕЛЕКТОРОВ:\n"
            "  #id-элемента\n"
            "  .class-элемента\n"
            "  input[name='q']\n"
            "  button[type='submit']\n\n"
            "ГОРЯЧИЕ КЛАВИШИ:\n"
            "  F1 — эта справка\n"
            "  Ctrl+Z — отменить в редакторе\n\n"
            "ТРЕБОВАНИЯ:\n"
            "  Google Chrome установлен на ПК\n"
            "  Интернет для первого запуска (ChromeDriver)\n"
        )

        txt = scrolledtext.ScrolledText(win, font=FONT_MAIN, bg=SURFACE, fg=FG,
                                        relief="flat", bd=10, state="normal")
        txt.pack(fill="both", expand=True, padx=16, pady=8)
        txt.insert("1.0", help_text)
        txt.config(state="disabled")

        tk.Button(win, text="Закрыть", font=FONT_TINY, bg=SURFACE, fg=ACCENT,
                  relief="flat", cursor="hand2", padx=20, pady=6,
                  command=win.destroy).pack(pady=10)

    # ── ЗАКРЫТИЕ ─────────────────────────────
    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Выход",
                    "Сценарий выполняется. Выйти и остановить?"):
                return
        self._stop()
        self.destroy()


if __name__ == "__main__":
    app = WebAutomatorPro()
    app.mainloop()
