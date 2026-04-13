import time
import os
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
import mss
import keyboard
import win32api
import win32con

# =========================
# CONFIGURAÇÕES DO JOGO
# =========================
WINDOW_TITLE_CONTAINS = os.environ.get("CURRENT_ACCOUNT", "Sallazzar")
VICTORY_TEMPLATE = os.path.join("templates", "combat", "victory.png")

SKILL_KEYS = ["1", "2", "3"]
DELAY_BETWEEN_SKILLS = 0.01   # era 0.04

CLICK_COUNT = 2
CLICK_INTERVAL = 0.02
JITTER_PX = 2
SAVE_DEBUG_IMAGES = False  # desativado para ganhar velocidade


def fast_click(x: int, y: int):
    """Clique direto via win32api — sem overhead do pyautogui."""
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

# ================================================================
#  FILTRO DE ÁREA SEGURA DE TILES
#  Tiles fora dessa margem (% da largura/altura da janela) são ignorados.
#  Isso elimina falsos positivos como o tile em (28, 230) no canto esquerdo.
# ================================================================
MARGEM_BORDA_X = 0.08   # Ignora tiles nos primeiros 8% e últimos 8% da largura
MARGEM_BORDA_Y = 0.08   # Ignora tiles nos primeiros 8% e últimos 8% da altura

@dataclass
class WindowRect:
    left: int; top: int; right: int; bottom: int
    @property
    def w(self) -> int: return self.right - self.left
    @property
    def h(self) -> int: return self.bottom - self.top

@dataclass
class TileCandidate:
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    confianca: float

def find_window_rect(title_part: str) -> Optional[WindowRect]:
    import win32gui
    matches = []
    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd): return
        t = (win32gui.GetWindowText(hwnd) or "").strip()
        if title_part.lower() in t.lower(): matches.append(hwnd)
    win32gui.EnumWindows(enum_handler, None)
    if not matches: return None
    left, top, right, bottom = win32gui.GetWindowRect(matches[0])
    return WindowRect(left, top, right, bottom)

def grab_window_bgr(rect: WindowRect) -> np.ndarray:
    monitor = {"left": rect.left, "top": rect.top, "width": rect.w, "height": rect.h}
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def tile_dentro_da_area_segura(cx: int, cy: int, frame_w: int, frame_h: int) -> bool:
    """Retorna True se o tile está longe das bordas da janela (área de jogo real)."""
    x_min = int(frame_w * MARGEM_BORDA_X)
    x_max = int(frame_w * (1.0 - MARGEM_BORDA_X))
    y_min = int(frame_h * MARGEM_BORDA_Y)
    y_max = int(frame_h * (1.0 - MARGEM_BORDA_Y))
    return x_min < cx < x_max and y_min < cy < y_max

def detect_tiles(frame_bgr: np.ndarray) -> List[TileCandidate]:
    h_frame, w_frame = frame_bgr.shape[:2]

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mascara = cv2.inRange(hsv, np.array([90, 100, 100]), np.array([130, 255, 255]))

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidatos = []
    for cnt in contornos:
        area = cv2.contourArea(cnt)
        if 600 < area < 3500:
            x, y, w, h = cv2.boundingRect(cnt)
            cx, cy = x + w // 2, y + h // 2
            if tile_dentro_da_area_segura(cx, cy, w_frame, h_frame):
                candidatos.append(TileCandidate(center=(cx, cy), bbox=(x, y, w, h), confianca=1.0))

    return candidatos

def check_victory(frame_bgr: np.ndarray, victory_tpl: Optional[np.ndarray]) -> bool:
    if victory_tpl is None: return False
    frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(frame_gray, victory_tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= 0.80

def save_debug(frame: np.ndarray, candidates: List[TileCandidate], skill_num: int):
    if not SAVE_DEBUG_IMAGES: return
    os.makedirs("debug", exist_ok=True)
    annotated = frame.copy()
    for c in candidates:
        x, y, w, h = c.bbox
        cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.circle(annotated, c.center, 5, (0, 0, 255), -1)
    ts = time.strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(f"debug/IA_skill_{skill_num}_{ts}.png", annotated)

def main():
    rect = find_window_rect(WINDOW_TITLE_CONTAINS)
    if not rect:
        print(f"[ERRO] Janela não encontrada: '{WINDOW_TITLE_CONTAINS}'")
        return

    victory_tpl = None
    if os.path.isfile(VICTORY_TEMPLATE):
        victory_tpl = cv2.imread(VICTORY_TEMPLATE, cv2.IMREAD_GRAYSCALE)

    centro_x = rect.left + rect.w // 2
    centro_y = rect.top + rect.h // 2

    for idx, key in enumerate(SKILL_KEYS, start=1):
        frame = grab_window_bgr(rect)
        if check_victory(frame, victory_tpl):
            fast_click(centro_x, centro_y)
            return

        keyboard.press_and_release(key)
        time.sleep(0.03)

        frame = grab_window_bgr(rect)
        tiles = detect_tiles(frame)

        if tiles:
            save_debug(frame, tiles, idx)
            for tile in tiles:
                keyboard.press_and_release(key)
                time.sleep(0.03)
                fast_click(rect.left + tile.center[0], rect.top + tile.center[1])
                time.sleep(0.02)
            fast_click(centro_x, centro_y)

        time.sleep(DELAY_BETWEEN_SKILLS)

    fast_click(centro_x, centro_y)

if __name__ == "__main__":
    main()
