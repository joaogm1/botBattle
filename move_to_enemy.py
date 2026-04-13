import time
import os
import math
from typing import List, Optional, Tuple

import cv2
import numpy as np
import mss
import win32api
import win32con

# =========================
# CONFIGURAÇÕES
# =========================
WINDOW_TITLE_CONTAINS = os.environ.get("CURRENT_ACCOUNT", "Sallazzar")

MARGEM_BORDA_X = 0.08
MARGEM_BORDA_Y = 0.08

ADJACENT_THRESHOLD_PX = 80   # distância do centro da janela para considerar já adjacente
SAVE_DEBUG_IMAGES = True    # salva debug/move_*.png para diagnosticar detecção


# =========================
# ESTRUTURAS E UTILIDADES
# =========================

def fast_click(x: int, y: int):
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


class WindowRect:
    def __init__(self, left, top, right, bottom):
        self.left = left; self.top = top
        self.right = right; self.bottom = bottom

    @property
    def w(self): return self.right - self.left
    @property
    def h(self): return self.bottom - self.top


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


def _dentro_da_area_segura(cx: int, cy: int, frame_w: int, frame_h: int) -> bool:
    x_min = int(frame_w * MARGEM_BORDA_X)
    x_max = int(frame_w * (1.0 - MARGEM_BORDA_X))
    y_min = int(frame_h * MARGEM_BORDA_Y)
    y_max = int(frame_h * (1.0 - MARGEM_BORDA_Y))
    return x_min < cx < x_max and y_min < cy < y_max


def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


# =========================
# DETECÇÃO
# =========================

HSV_GREEN_LOW  = [60, 120, 120]
HSV_GREEN_HIGH = [90, 255, 255]

HSV_GREEN_LOW_FALLBACK  = [55, 80, 100]
HSV_GREEN_HIGH_FALLBACK = [95, 255, 255]


def detect_move_tiles(frame_bgr: np.ndarray) -> List[Tuple[int, int]]:
    """Detecta tiles verdes disponíveis para movimento."""
    h_frame, w_frame = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, np.array(HSV_GREEN_LOW), np.array(HSV_GREEN_HIGH))
    raw_pixels = int(np.sum(mask > 0))
    print(f"[detect_move_tiles] pixels verdes brutos (primário): {raw_pixels}")

    contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tiles = _filter_tiles(contornos, w_frame, h_frame)

    if not tiles:
        print("[detect_move_tiles] 0 tiles no range primário — tentando fallback")
        mask_fb = cv2.inRange(hsv, np.array(HSV_GREEN_LOW_FALLBACK), np.array(HSV_GREEN_HIGH_FALLBACK))
        raw_pixels_fb = int(np.sum(mask_fb > 0))
        print(f"[detect_move_tiles] pixels verdes brutos (fallback): {raw_pixels_fb}")
        contornos_fb, _ = cv2.findContours(mask_fb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        tiles = _filter_tiles(contornos_fb, w_frame, h_frame)

    return tiles


def _filter_tiles(contornos, w_frame: int, h_frame: int) -> List[Tuple[int, int]]:
    tiles = []
    for cnt in contornos:
        area = cv2.contourArea(cnt)
        if not (300 < area < 4000):
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy = x + w // 2, y + h // 2
        if _dentro_da_area_segura(cx, cy, w_frame, h_frame):
            tiles.append((cx, cy))
    return tiles


def detect_enemies(frame_bgr: np.ndarray) -> List[Tuple[int, int]]:
    """Detecta inimigos pelo contorno vermelho + corpo preto."""
    h_frame, w_frame = frame_bgr.shape[:2]
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    mask_red1 = cv2.inRange(hsv, np.array([0, 160, 100]), np.array([10, 255, 255]))
    mask_red2 = cv2.inRange(hsv, np.array([170, 160, 100]), np.array([180, 255, 255]))
    mask_red = cv2.bitwise_or(mask_red1, mask_red2)

    kernel = np.ones((18, 18), np.uint8)
    mask_red_dilated = cv2.dilate(mask_red, kernel, iterations=1)

    mask_black = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 80, 80]))
    mask_black_near_red = cv2.bitwise_and(mask_black, mask_red_dilated)

    contornos, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    inimigos = []
    for cnt in contornos:
        area = cv2.contourArea(cnt)
        if not (40 < area < 8000):
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy = x + w // 2, y + h // 2
        if not _dentro_da_area_segura(cx, cy, w_frame, h_frame):
            continue
        roi = mask_black_near_red[y:y+h, x:x+w]
        if int(np.sum(roi > 0)) < 30:
            continue
        inimigos.append((cx, cy))
    return inimigos


def already_adjacent(enemies: List[Tuple[int, int]], frame_w: int, frame_h: int) -> bool:
    """True se algum inimigo está a menos de ADJACENT_THRESHOLD_PX do centro da janela."""
    centro = (frame_w // 2, frame_h // 2)
    return any(_dist(e, centro) < ADJACENT_THRESHOLD_PX for e in enemies)


def detect_enemy_mask(frame_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask_red1 = cv2.inRange(hsv, np.array([0, 160, 100]), np.array([10, 255, 255]))
    mask_red2 = cv2.inRange(hsv, np.array([170, 160, 100]), np.array([180, 255, 255]))
    return cv2.bitwise_or(mask_red1, mask_red2)


def _tile_over_enemy(tile: Tuple[int, int], enemy_mask: np.ndarray) -> bool:
    x, y = tile
    radius = 18
    y0 = max(0, y - radius)
    y1 = min(enemy_mask.shape[0], y + radius)
    x0 = max(0, x - radius)
    x1 = min(enemy_mask.shape[1], x + radius)
    return int(np.sum(enemy_mask[y0:y1, x0:x1] > 0)) > 0


# =========================
# DEBUG
# =========================

def _save_debug(frame: np.ndarray, tiles: List[Tuple[int, int]],
                inimigos: List[Tuple[int, int]],
                tile_alvo: Tuple[int, int] = None,
                inimigo_alvo: Tuple[int, int] = None):
    if not SAVE_DEBUG_IMAGES:
        return
    os.makedirs("debug", exist_ok=True)
    annotated = frame.copy()
    for cx, cy in tiles:
        cv2.circle(annotated, (cx, cy), 8, (0, 255, 0), 2)   # tiles verdes
    for cx, cy in inimigos:
        cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), 2)   # inimigos vermelho
    if inimigo_alvo:
        cv2.circle(annotated, inimigo_alvo, 12, (0, 0, 200), 3)
    if tile_alvo:
        cv2.circle(annotated, tile_alvo, 12, (0, 200, 0), 3)
        cv2.line(annotated, tile_alvo, inimigo_alvo or tile_alvo, (255, 255, 0), 1)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = f"debug/move_{ts}.png"
    cv2.imwrite(path, annotated)
    print(f"[move_to_enemy] debug salvo: {path}")


# =========================
# PONTO DE ENTRADA
# =========================

def move_to_enemy():
    rect = find_window_rect(WINDOW_TITLE_CONTAINS)
    if not rect:
        print(f"[move_to_enemy] Janela não encontrada: '{WINDOW_TITLE_CONTAINS}'")
        return

    frame = grab_window_bgr(rect)
    h_frame, w_frame = frame.shape[:2]

    tiles = detect_move_tiles(frame)
    print(f"[move_to_enemy] tiles verdes: {len(tiles)}")
    if not tiles:
        _save_debug(frame, [], [])
        return  # sem tiles verdes — não é fase de movimento

    inimigos = detect_enemies(frame)
    print(f"[move_to_enemy] inimigos: {len(inimigos)}")
    if not inimigos:
        _save_debug(frame, tiles, [])
        return  # sem inimigos detectados

    if already_adjacent(inimigos, w_frame, h_frame):
        print(f"[move_to_enemy] já adjacente — sem movimento")
        _save_debug(frame, tiles, inimigos)
        return  # já está perto o suficiente

    centro_janela = (w_frame // 2, h_frame // 2)
    enemy_mask = detect_enemy_mask(frame)

    # Inimigo mais próximo do centro da janela
    inimigo_alvo = min(inimigos, key=lambda e: _dist(e, centro_janela))

    # Exclui tiles ocupados por qualquer inimigo (evita clicar no próprio inimigo)
    TILE_OCUPADO_PX = 80
    tiles_livres = [
        t for t in tiles
        if all(_dist(t, e) > TILE_OCUPADO_PX for e in inimigos)
        and not _tile_over_enemy(t, enemy_mask)
    ]
    print(f"[move_to_enemy] tiles livres (>{TILE_OCUPADO_PX}px de inimigos e sem vermelho): {len(tiles_livres)}/{len(tiles)}")
    if not tiles_livres:
        print("[move_to_enemy] nenhum tile livre — abortando")
        _save_debug(frame, tiles, inimigos)
        return

    # Tile livre mais próximo do inimigo alvo
    tile_alvo = min(tiles_livres, key=lambda t: _dist(t, inimigo_alvo))

    print(f"[move_to_enemy] inimigo_alvo={inimigo_alvo}  tile_alvo={tile_alvo}")
    _save_debug(frame, tiles, inimigos, tile_alvo, inimigo_alvo)

    fast_click(rect.left + tile_alvo[0], rect.top + tile_alvo[1])
    time.sleep(0.8)


if __name__ == "__main__":
    move_to_enemy()
