# -*- coding: utf-8 -*-
import uno
import threading
import sys
import os
import json
import csv
import re
import difflib
import locale
import logging
import traceback
import time
from datetime import datetime

# ==========================================
# 0. GÜVENLİK VE LİMİT AYARLARI
# ==========================================
MAX_RESULTS = 10000  # Tkinter TreeView performansını korumak için ideal üst limit
LARGE_SHEET_ROWS = 100000  # Bu satır sayısından fazlası için uyarı ver
LARGE_SHEET_CELLS = 5000000  # (Satır x Sütun) Toplam hücre limiti (getDataArray koruması)

# ==========================================
# 1. AYARLAR, LOGLAMA VE ÇEVİRİLER
# ==========================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".multi_search_config.json")
LOG_FILE = os.path.join(os.path.expanduser("~"), ".multi_search.log")
HISTORY_LIMIT = 15

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a')]
)
logger = logging.getLogger(__name__)

LANG_CODE = "en"
try:
    loc = locale.getlocale()
    if loc and loc[0] and loc[0].lower().startswith("tr"):
        LANG_CODE = "tr"
except Exception as e:
    logger.debug(f"Locale detection failed: {e}")

TEXTS = {
    "tr": {
        "app_title": "Libre Çoklu Belgede Arama 🛡️",
        "frame_criteria": "Arama Kriterleri",
        "lbl_search": "Ara:",
        "chk_fuzzy": "Bulanık (Fuzzy)",
        "chk_regex": "Regex",
        "chk_case": "Büyük/Küçük Harf",
        "chk_whole": "Tam Kelime",
        "btn_find": "🔍 Ara",
        "btn_stop": "🛑 Durdur",
        "btn_export": "💾 CSV İndir",
        "col_score": "Puan",
        "col_doc": "Dosya",
        "col_sheet": "Sayfa",
        "col_cell": "Hücre",
        "col_val": "Değer",
        "status_ready": "Hazır",
        "status_reading": "Okunuyor: {}...",
        "status_searching": "İşleniyor: {} | Satır: {}/{} (%{:.1f})",
        "status_found": "Bitti: {} kayıt bulundu.",
        "status_stopped": "Durduruldu. Bulunan: {}",
        "status_csv_saved": "CSV dosyası kaydedildi.",
        "status_limit": "⚠️ Limit ulaşıldı (Maks: {})",
        "err_regex": "Geçersiz Regex Hatası!",
        "ctx_copy": "Kopyala",
        "header_msg": "Bilgi",
        "err_header": "Hata",
        "lbl_scope": "Kapsam:",
        "scope_all": "Tüm Açık Dosyalar",
        "scope_active": "Sadece Aktif Sayfa",
        "warn_large_sheet": "DİKKAT: '{}' sayfası çok büyük ({} satır, {} hücre).\nBu işlem LibreOffice'in belleğini (RAM) zorlayabilir.\n\nYine de okunsun mu?",
        "warn_overwrite": "Dosya zaten var. Üzerine yazılsın mı?"
    },
    "en": {
        "app_title": "Libre Multi Search 🛡️",
        "frame_criteria": "Search Criteria",
        "lbl_search": "Find:",
        "chk_fuzzy": "Fuzzy Search",
        "chk_regex": "Regex",
        "chk_case": "Case Sensitive",
        "chk_whole": "Whole Word",
        "btn_find": "🔍 Find",
        "btn_stop": "🛑 Stop",
        "btn_export": "💾 Export CSV",
        "col_score": "Score",
        "col_doc": "File",
        "col_sheet": "Sheet",
        "col_cell": "Cell",
        "col_val": "Value",
        "status_ready": "Ready",
        "status_reading": "Reading: {}...",
        "status_searching": "Processing: {} | Row: {}/{} ({:.1f}%)",
        "status_found": "Done: {} records found.",
        "status_stopped": "Stopped. Found: {}",
        "status_csv_saved": "CSV saved.",
        "status_limit": "⚠️ Limit reached (Max: {})",
        "err_regex": "Invalid Regex Pattern!",
        "ctx_copy": "Copy",
        "header_msg": "Info",
        "err_header": "Error",
        "lbl_scope": "Scope:",
        "scope_all": "All Open Docs",
        "scope_active": "Active Sheet Only",
        "warn_large_sheet": "WARNING: Sheet '{}' is very large ({} rows, {} cells).\nThis may consume a lot of LibreOffice memory (RAM).\n\nDo you want to force read?",
        "warn_overwrite": "File already exists. Overwrite?"
    }
}[LANG_CODE]


# ==========================================
# 2. YARDIMCI FONKSİYONLAR (HELPERS)
# ==========================================
def tr_lower(text):
    """Türkçe I/ı ve İ/i karakterlerini kusursuz küçültür."""
    if not isinstance(text, str):
        text = str(text)
    return text.replace("I", "ı").replace("İ", "i").lower()


# ==========================================
# 3. UNO DISPATCHER (LibreOffice İletişimi)
# ==========================================
class UnoService:
    def __init__(self, desktop):
        self.desktop = desktop

    def get_sheets_to_scan(self, scope_active_only=False):
        sheets_info = []
        try:
            components = self.desktop.getComponents()
            enum = components.createEnumeration()
            current_doc = self.desktop.getCurrentComponent()

            active_sheet_name = ""
            if hasattr(current_doc, "CurrentController"):
                try:
                    active_sheet_name = current_doc.CurrentController.ActiveSheet.Name
                except Exception:
                    pass

            while enum.hasMoreElements():
                try:
                    doc = enum.nextElement()
                    if not doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                        continue

                    is_active_doc = (doc == current_doc)
                    if scope_active_only and not is_active_doc:
                        continue

                    doc_id = id(doc)
                    doc_title = getattr(doc, "Title", "Untitled")

                    for sheet in doc.Sheets:
                        if scope_active_only and (not is_active_doc or sheet.Name != active_sheet_name):
                            continue

                        sheets_info.append({
                            "doc": doc, "sheet": sheet, "doc_id": doc_id,
                            "doc_title": doc_title, "sheet_name": sheet.Name
                        })
                except Exception as doc_err:
                    logger.warning(f"Skipping document due to state change: {doc_err}")

        except Exception as e:
            logger.error(f"UNO Error (get_sheets): {e}", exc_info=True)
        return sheets_info

    def fetch_sheet_data(self, sheet, force=False):
        try:
            cursor = sheet.createCursor()
            cursor.gotoEndOfUsedArea(True)
            addr = cursor.RangeAddress

            if addr.EndColumn < 0 or addr.EndRow < 0:
                return None, None, [], 0, 0

            start_col, start_row = addr.StartColumn, addr.StartRow
            total_rows = addr.EndRow - start_row + 1
            total_cols = addr.EndColumn - start_col + 1
            total_cells = total_rows * total_cols

            if not force and (total_rows > LARGE_SHEET_ROWS or total_cells > LARGE_SHEET_CELLS):
                return start_col, start_row, None, total_rows, total_cells

            data = sheet.getCellRangeByPosition(start_col, start_row, addr.EndColumn, addr.EndRow).getDataArray()
            return start_col, start_row, data, total_rows, total_cells

        except Exception as e:
            logger.error(f"UNO Error (fetch_data): {e}", exc_info=True)
            return None, None, [], 0, 0

    def focus_cell(self, doc, sheet, col, row):
        try:
            ctrl = doc.CurrentController
            frame = ctrl.Frame
            self.desktop.setActiveFrame(frame)
            frame.ContainerWindow.setVisible(True)
            frame.ContainerWindow.toFront()
            ctrl.setActiveSheet(sheet)
            cell = sheet.getCellByPosition(col, row)
            ctrl.select(cell)
        except Exception as e:
            logger.error(f"UNO Error (focus_cell): {e}")


# ==========================================
# 4. SEARCH ENGINE (Saf Python - Thread Safe)
# ==========================================
class SearchCore:
    @staticmethod
    def compile_query_info(query, use_regex, use_case, use_whole, use_fuzzy):
        q_comp = query if use_case else tr_lower(query)
        info = {
            "query": query,
            "query_comp": q_comp,
            "query_len": len(query),
            "query_char_set": set(q_comp) if use_fuzzy else set(),
            "use_fuzzy": use_fuzzy, "use_regex": use_regex,
            "use_whole": use_whole, "use_case": use_case,
            "regex_pattern": None, "error": None
        }
        info["query_set_len"] = len(info["query_char_set"])

        try:
            if use_whole and not use_regex:
                flags = 0 if use_case else re.IGNORECASE
                info["regex_pattern"] = re.compile(rf"\b{re.escape(query)}\b", flags)
                info["use_regex"] = True
            elif use_regex:
                flags = 0 if use_case else re.IGNORECASE
                info["regex_pattern"] = re.compile(query, flags)
        except Exception as e:
            info["error"] = str(e)
            logger.warning(f"Regex Compile Error: {e}")

        return info

    @staticmethod
    def scan_data(data, start_col, start_row, q_info, max_allowed, check_cancel_cb, progress_cb):
        results = []
        q_comp, q_len = q_info["query_comp"], q_info["query_len"]
        q_set, q_set_len = q_info["query_char_set"], q_info["query_set_len"]
        use_regex, regex_pat = q_info["use_regex"], q_info["regex_pattern"]
        use_whole, use_fuzzy, use_case = q_info["use_whole"], q_info["use_fuzzy"], q_info["use_case"]

        total_rows = len(data)
        added_count = 0
        last_ui_update = time.time()

        for r, row in enumerate(data):
            if check_cancel_cb():
                break

            if time.time() - last_ui_update > 0.1:
                progress_cb(r, total_rows)
                last_ui_update = time.time()

            for c, val in enumerate(row):
                if val == "" or val is None:
                    continue

                val_str = str(val)
                val_comp = val_str if use_case or use_regex else tr_lower(val_str)
                score, matched = 0, False

                if use_regex and regex_pat:
                    try:
                        if regex_pat.search(val_str):
                            score, matched = 100, True
                    except Exception:
                        pass

                if not matched and not use_whole:
                    if q_comp in val_comp:
                        score, matched = 100, True

                if not matched and use_fuzzy:
                    val_len = len(val_comp)
                    if val_len <= 1500:
                        if q_set_len > 2 and len(q_set & set(val_comp)) < (q_set_len * 0.4):
                            continue

                        try:
                            ratio_full = difflib.SequenceMatcher(None, q_comp, val_comp).ratio()
                            limit_len = min(val_len, q_len * 3)
                            ratio_partial = difflib.SequenceMatcher(None, q_comp, val_comp[
                                                                                  :limit_len]).ratio() if limit_len > q_len else 0

                            final_ratio = max(ratio_full, ratio_partial)
                            if final_ratio > 0.50:
                                score, matched = int(final_ratio * 100), True
                        except Exception:
                            pass

                if matched:
                    results.append({"score": score, "val": val_str, "col": start_col + c, "row": start_row + r})
                    added_count += 1

                    if added_count >= max_allowed:
                        progress_cb(total_rows, total_rows)
                        return results

        progress_cb(total_rows, total_rows)
        return results

    @staticmethod
    def get_cell_name(col, row):
        res = ""
        while col >= 0:
            res = chr(col % 26 + 65) + res
            col = col // 26 - 1
        return f"{res}{row + 1}"


# ==========================================
# 5. GUI & KONTROLCÜ (SearchApp)
# ==========================================
class SearchApp:
    def __init__(self, root, desktop):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.ttk = ttk

        self.root = root
        self.uno = UnoService(desktop)

        self.results = {}
        self.limit_reached = False

        self.config = self.load_config()
        self.search_history = self.config.get("history", [])

        self.is_searching = False
        self.sheets_queue = []
        self.current_query_info = None

        self.root.title(TEXTS["app_title"])
        self.root.geometry("1000x600")

        try:
            style = self.ttk.Style()
            if 'clam' in style.theme_names():
                style.theme_use('clam')
        except Exception:
            pass

        self._init_ui()
        logger.info("Application Started Successfully")

    def _init_ui(self):
        main_frame = self.ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)

        controls = self.ttk.LabelFrame(main_frame, text=TEXTS["frame_criteria"], padding=10)
        controls.pack(fill="x", pady=5)
        grid_frame = self.ttk.Frame(controls)
        grid_frame.pack(fill="x")

        self.ttk.Label(grid_frame, text=TEXTS["lbl_search"]).grid(row=0, column=0, padx=5, sticky="w")
        self.cmb_search = self.ttk.Combobox(grid_frame, width=40, values=self.search_history)
        self.cmb_search.grid(row=0, column=1, padx=5, pady=2)
        self.cmb_search.bind("<Return>", lambda e: self.toggle_search())

        self.ttk.Label(grid_frame, text=TEXTS["lbl_scope"]).grid(row=0, column=2, padx=15, sticky="w")
        self.var_scope = self.tk.StringVar(value=TEXTS["scope_all"])
        self.ttk.Combobox(grid_frame, textvariable=self.var_scope, state="readonly",
                          values=[TEXTS["scope_all"], TEXTS["scope_active"]]).grid(row=0, column=3, padx=5)

        opts_frame = self.ttk.Frame(controls)
        opts_frame.pack(fill="x", pady=10)

        self.var_fuzzy = self.tk.BooleanVar(value=self.config.get("fuzzy", False))
        self.var_regex = self.tk.BooleanVar(value=self.config.get("regex", False))
        self.var_case = self.tk.BooleanVar(value=self.config.get("case", False))
        self.var_whole = self.tk.BooleanVar(value=self.config.get("whole", False))

        self.ttk.Checkbutton(opts_frame, text=TEXTS["chk_fuzzy"], variable=self.var_fuzzy).pack(side="left", padx=5)
        self.ttk.Checkbutton(opts_frame, text=TEXTS["chk_regex"], variable=self.var_regex).pack(side="left", padx=5)
        self.ttk.Checkbutton(opts_frame, text=TEXTS["chk_case"], variable=self.var_case).pack(side="left", padx=5)
        self.ttk.Checkbutton(opts_frame, text=TEXTS["chk_whole"], variable=self.var_whole).pack(side="left", padx=5)

        btn_frame = self.ttk.Frame(controls)
        btn_frame.pack(fill="x", pady=5)

        self.btn_find = self.ttk.Button(btn_frame, text=TEXTS["btn_find"], command=self.toggle_search)
        self.btn_find.pack(side="left", padx=5)
        self.ttk.Button(btn_frame, text=TEXTS["btn_export"], command=self.export_csv).pack(side="right", padx=5)

        self.progress_var = self.tk.DoubleVar()
        self.progress = self.ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress.pack(side="bottom", fill="x")
        self.status = self.ttk.Label(self.root, text=TEXTS["status_ready"], relief="sunken", anchor="w")
        self.status.pack(side="bottom", fill="x")

        tree_frame = self.ttk.Frame(main_frame)
        tree_frame.pack(fill="both", expand=True, pady=5)

        cols = ("score", "doc", "sheet", "pos", "value")
        self.tree = self.ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")

        self.tree.column("score", width=60, anchor="center")
        self.tree.column("doc", width=150)
        self.tree.column("sheet", width=120)
        self.tree.column("pos", width=80, anchor="center")
        self.tree.column("value", width=400)

        # Sütun isimleri hatası giderildi
        headers = {
            "score": TEXTS["col_score"],
            "doc": TEXTS["col_doc"],
            "sheet": TEXTS["col_sheet"],
            "pos": TEXTS["col_cell"],
            "value": TEXTS["col_val"]
        }
        for col in cols:
            self.tree.heading(col, text=headers[col])

        sb = self.ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<Double-1>", self.on_click)
        self.context_menu = self.tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label=TEXTS["ctx_copy"], command=self.copy_value)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.is_searching = False
        try:
            self.root.destroy()
        except Exception:
            pass

    def toggle_search(self):
        from tkinter import messagebox

        if self.is_searching:
            self.is_searching = False
            self.btn_find.config(text=TEXTS["btn_find"])
            logger.info("Search manually stopped by user.")
            return

        query = self.cmb_search.get()
        if not query: return

        self._update_history(query)
        self.save_config()

        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self.limit_reached = False

        q_info = SearchCore.compile_query_info(
            query, self.var_regex.get(), self.var_case.get(), self.var_whole.get(), self.var_fuzzy.get()
        )
        if q_info["error"]:
            messagebox.showerror(TEXTS["err_header"], TEXTS["err_regex"])
            return

        self.current_query_info = q_info
        self.is_searching = True
        self.btn_find.config(text=TEXTS["btn_stop"])
        self.progress_var.set(0)

        scope_active_only = (self.var_scope.get() == TEXTS["scope_active"])
        self.sheets_queue = self.uno.get_sheets_to_scan(scope_active_only)

        if not self.sheets_queue:
            self._finish_search()
            messagebox.showinfo(TEXTS["header_msg"], "No open spreadsheets found.")
            return

        logger.info(f"Starting search for: '{query}'")
        self.root.after(10, self._process_next_sheet)

    def _process_next_sheet(self):
        from tkinter import messagebox

        if not self.is_searching or not self.sheets_queue or self.limit_reached:
            self._finish_search()
            return

        sheet_info = self.sheets_queue.pop(0)

        try:
            self.status.config(text=TEXTS["status_reading"].format(sheet_info["sheet_name"]))
            self.root.update_idletasks()
        except Exception:
            return

        start_col, start_row, data, total_rows, total_cells = self.uno.fetch_sheet_data(sheet_info["sheet"])

        if data is None and total_rows > 0:
            msg = TEXTS["warn_large_sheet"].format(sheet_info["sheet_name"], total_rows, total_cells)
            if messagebox.askyesno(TEXTS["header_msg"], msg):
                start_col, start_row, data, _, _ = self.uno.fetch_sheet_data(sheet_info["sheet"], force=True)
            else:
                self.root.after(10, self._process_next_sheet)
                return

        if not data:
            self.root.after(10, self._process_next_sheet)
            return

        # UI ipliğinden bağımsız kalan kapasiteyi hesapla
        remaining_capacity = MAX_RESULTS - len(self.results)
        if remaining_capacity <= 0:
            self.root.after(10, self._process_next_sheet)
            return

        t = threading.Thread(
            target=self._worker_task,
            args=(sheet_info, self.current_query_info, data, start_col, start_row, remaining_capacity)
        )
        t.daemon = True
        t.start()

    def _worker_task(self, sheet_info, q_info, data, start_col, start_row, remaining_capacity):
        try:
            sheet_name = sheet_info["sheet_name"]

            def progress_cb(cur_row, tot_row):
                pct = (cur_row / tot_row) * 100 if tot_row > 0 else 0

                def update_ui():
                    if self.is_searching:
                        self.progress_var.set(pct)
                        self.status.config(text=TEXTS["status_searching"].format(sheet_name, cur_row, tot_row, pct))

                try:
                    self.root.after(0, update_ui)
                except Exception:
                    pass

            raw_results = SearchCore.scan_data(
                data, start_col, start_row, q_info,
                max_allowed=remaining_capacity,
                check_cancel_cb=lambda: not self.is_searching,
                progress_cb=progress_cb
            )

            del data

            # Puanlamaya göre sırala (En uygun sonuç en üstte)
            raw_results.sort(key=lambda x: x["score"], reverse=True)

            try:
                if self.is_searching:
                    self.root.after(0, self._on_sheet_finished, sheet_info, raw_results)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Worker Error: {e}", exc_info=True)
            try:
                self.root.after(0, self._on_sheet_finished, sheet_info, [])
            except Exception:
                pass

    def _on_sheet_finished(self, sheet_info, raw_results):
        try:
            for r in raw_results:
                if len(self.results) >= MAX_RESULTS:
                    self.limit_reached = True
                    break

                cell_name = SearchCore.get_cell_name(r["col"], r["row"])
                item_id = self.tree.insert("", "end", values=(
                    f"%{r['score']}", sheet_info["doc_title"], sheet_info["sheet_name"], cell_name, r["val"]
                ))

                self.results[item_id] = {
                    "doc": sheet_info["doc"], "sheet": sheet_info["sheet"],
                    "col": r["col"], "row": r["row"]
                }
        except Exception as e:
            logger.error(f"UI Update Error: {e}")
        finally:
            try:
                self.root.after(10, self._process_next_sheet)
            except Exception:
                pass

    def _finish_search(self):
        try:
            self.progress_var.set(100)
            status_txt = TEXTS["status_found"] if self.is_searching else TEXTS["status_stopped"]
            final_text = status_txt.format(len(self.results))

            if self.limit_reached:
                final_text += " " + TEXTS["status_limit"].format(MAX_RESULTS)

            self.status.config(text=final_text)
            self.is_searching = False
            self.btn_find.config(text=TEXTS["btn_find"])
        except Exception:
            pass

    def on_click(self, event):
        sel = self.tree.selection()
        if not sel: return
        target = self.results.get(sel[0])
        if target:
            self.uno.focus_cell(target["doc"], target["sheet"], target["col"], target["row"])

    def _update_history(self, query):
        if query not in self.search_history:
            self.search_history.insert(0, query)
            self.search_history = self.search_history[:HISTORY_LIMIT]
            self.cmb_search['values'] = self.search_history

    def export_csv(self):
        from tkinter import filedialog, messagebox
        if not self.results: return

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path: return

        if os.path.exists(path):
            if not messagebox.askyesno(TEXTS["header_msg"], TEXTS["warn_overwrite"]):
                return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [TEXTS["col_score"], TEXTS["col_doc"], TEXTS["col_sheet"], TEXTS["col_cell"], TEXTS["col_val"]])
                for child in self.tree.get_children():
                    writer.writerow(self.tree.item(child)["values"])
            messagebox.showinfo(TEXTS["header_msg"], TEXTS["status_csv_saved"])
        except Exception as e:
            logger.error(f"CSV Export Error: {e}", exc_info=True)
            messagebox.showerror(TEXTS["err_header"], str(e))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_value(self):
        sel = self.tree.selection()
        if sel:
            try:
                val = self.tree.item(sel[0])['values'][4]
                self.root.clipboard_clear()
                self.root.clipboard_append(str(val))
            except Exception as e:
                logger.warning(f"Clipboard Error: {e}")

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Config load error: {e}")
            try:
                os.replace(CONFIG_FILE, CONFIG_FILE + ".bak")
            except Exception:
                pass
        return {}

    def save_config(self):
        cfg = {
            "fuzzy": self.var_fuzzy.get(), "regex": self.var_regex.get(),
            "case": self.var_case.get(), "whole": self.var_whole.get(),
            "history": self.search_history
        }
        tmp_file = CONFIG_FILE + ".tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, CONFIG_FILE)
        except Exception as e:
            logger.error(f"Config save error: {e}", exc_info=True)
            try:
                if os.path.exists(tmp_file): os.remove(tmp_file)
            except Exception:
                pass


# ==========================================
# 6. MACRO ENTRY POINT
# ==========================================
def run_gui(desktop):
    """
    NOT: LibreOffice makro ortamında Tkinter ana UNO thread'i bloke etmesin diye
    kasıtlı olarak arka plan (daemon) thread'inde çalıştırılır.
    Windows ve Linux'ta güvenlidir. MacOS'ta nadiren pencere odağı sorunları yapabilir.
    """
    try:
        import tkinter as tk
        root = tk.Tk()

        root.update_idletasks()
        w, h = 1000, 600
        x = (root.winfo_screenwidth() // 2) - (w // 2)
        y = (root.winfo_screenheight() // 2) - (h // 2)
        root.geometry(f"{w}x{h}+{x}+{y}")

        app = SearchApp(root, desktop)

        root.attributes("-topmost", True)
        root.after(500, lambda: root.attributes("-topmost", False))

        root.mainloop()
    except Exception as e:
        logger.critical(f"GUI Crash: {e}", exc_info=True)


def CokluAramaMacro(*args):
    try:
        desktop = XSCRIPTCONTEXT.getDesktop()
        t = threading.Thread(target=run_gui, args=(desktop,))
        t.daemon = True
        t.start()
    except Exception as e:
        logger.critical(f"Macro Start Error: {e}", exc_info=True)


g_exportedScripts = (CokluAramaMacro,)