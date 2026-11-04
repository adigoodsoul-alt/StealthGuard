import os
import sys
import re
import threading
import urllib.parse
import ctypes


def url_to_path(url: str, location_name: str = "") -> str:
    r"""
    Преобразует file:// или search-ms: URL (из IWebBrowserApp.LocationURL)
    в стандартный нормализованный локальный или UNC путь Windows.
    Поддерживает:
      - file:///C:/Users/User/Secret%20Folder -> C:\Users\User\Secret Folder
      - search-ms:displayname=...&crumb=location:C%3A%5CSecret -> search-ms://C:\Secret|query
    """
    if not url:
        return ""

    low_url = url.lower()

    # 1. Обработка поисковых запросов Проводника Windows 11 (search-ms:)
    if low_url.startswith("search-ms:"):
        unquoted = urllib.parse.unquote(url)
        unquoted = urllib.parse.unquote(unquoted)  # Двойной unquote для вложенных параметров crumb=location:...
        scope_path = ""
        if "crumb=location:" in unquoted.lower():
            idx = unquoted.lower().find("crumb=location:") + len("crumb=location:")
            rest = unquoted[idx:]
            for sep in ("&", "|"):
                if sep in rest:
                    rest = rest.split(sep, 1)[0]
            scope_path = os.path.normpath(rest.strip())
        return f"search-ms://{scope_path}|{unquoted}|{location_name}"

    # 2. Обработка обычных файловых URL (file://)
    if not low_url.startswith("file:"):
        return url

    parsed = urllib.parse.urlsplit(url)
    unquoted_path = urllib.parse.unquote(parsed.path)

    if len(unquoted_path) >= 3 and unquoted_path[0] == "/" and unquoted_path[2] == ":":
        path = unquoted_path[1:]
    elif parsed.netloc:
        path = f"\\\\{parsed.netloc}{unquoted_path}"
    else:
        path = unquoted_path

    return os.path.normpath(path)


def normalize_path(path: str) -> str:
    """
    Возвращает нормализованный абсолютный путь в нижнем регистре без завершающего слэша.
    """
    if not path:
        return ""
    if path.startswith("search-ms://"):
        return path.lower()
    try:
        clean = os.path.normpath(os.path.abspath(path))
        return os.path.normcase(clean).rstrip("\\/")
    except Exception:
        return path.strip().lower().rstrip("\\/")


def is_path_matching(current_path: str, rule_target_path: str) -> bool:
    """
    Проверяет, совпадает ли текущий путь вкладки Проводника с защищаемым путём правила,
    является ли его подпапкой, либо поисковым запросом Проводника (search-ms:),
    затрагивающим защищаемую папку или её имя.
    """
    if not current_path or not rule_target_path:
        return False

    norm_target = normalize_path(rule_target_path)
    if not norm_target:
        return False

    # Проверка поисковой выдачи Проводника (search-ms://scope|raw_query|location_name)
    if current_path.startswith("search-ms://"):
        payload = current_path[len("search-ms://"):]
        parts = payload.split("|", 2)
        scope_path = parts[0] if len(parts) > 0 else ""
        raw_query = (parts[1] if len(parts) > 1 else "").lower()
        loc_name = (parts[2] if len(parts) > 2 else "").lower()

        # А) Если поиск запущен внутри самой защищаемой папки или её подпапки
        if scope_path:
            norm_scope = normalize_path(scope_path)
            if norm_scope == norm_target or norm_scope.startswith(norm_target + "\\"):
                return True

        # Б) Если в строке поиска вбито название защищаемой папки или путь к ней
        target_name = os.path.basename(norm_target).lower()
        if target_name and len(target_name) >= 2:
            if target_name in raw_query or target_name in loc_name:
                return True
        if norm_target in raw_query:
            return True

        # В) Проверка по глобальному индексу PROTECTED_ITEM_NAMES
        # Защита от поиска Windows Search по имени скрытого файла/подпапки при поиске с корня диска
        try:
            from core.file_cloaker import get_protected_item_names
            prot_names = get_protected_item_names()
            if prot_names:
                query_tokens = set(re.findall(r"[\w\.\-]+", raw_query + " " + loc_name))
                system_ignore = {
                    "search-ms", "displayname", "crumb", "location", "query",
                    "search", "results", "this", "computer", "local", "disk"
                }
                for t in query_tokens:
                    t_low = t.strip().lower()
                    if len(t_low) >= 3 and t_low not in system_ignore:
                        if t_low in prot_names:
                            return True
                for name in prot_names:
                    if len(name) >= 3 and name in raw_query:
                        return True
        except Exception:
            pass

        return False

    norm_current = normalize_path(current_path)
    if not norm_current:
        return False

    if norm_current == norm_target:
        return True

    target_prefix = norm_target + "\\"
    return norm_current.startswith(target_prefix)


def show_native_error_dialog(title: str, message: str, parent_hwnd: int = 0):
    """
    Отображает системный диалог ошибки Windows MessageBoxW в фоновом потоке.
    """
    def _worker():
        flags = 0x00000010 | 0x00010000 | 0x00040000
        try:
            ctypes.windll.user32.MessageBoxW(parent_hwnd, message, title, flags)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
