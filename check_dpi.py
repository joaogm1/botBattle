"""Diagnostica DPI scaling e sistema de coordenadas."""
import ctypes
import ctypes.wintypes
import pyautogui
import mss

# Checar DPI scaling
try:
    awareness = ctypes.c_int()
    ctypes.windll.shcore.GetProcessDpiAwareness(0, ctypes.byref(awareness))
    print(f"DPI Awareness atual: {awareness.value}  (0=unaware, 1=system, 2=per-monitor)")
except Exception as e:
    print(f"Nao conseguiu checar DPI awareness: {e}")

# Resolucao pyautogui vs mss
pa_w, pa_h = pyautogui.size()
print(f"pyautogui.size(): {pa_w}x{pa_h}")

with mss.mss() as sct:
    mon = sct.monitors[1]
    print(f"mss monitor[1]: {mon['width']}x{mon['height']} at ({mon['left']},{mon['top']})")

# DPI do monitor
try:
    hdc = ctypes.windll.user32.GetDC(0)
    dpi_x = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
    dpi_y = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    scale = dpi_x / 96.0
    print(f"DPI: {dpi_x}x{dpi_y} (scale={scale:.0%})")
except Exception as e:
    print(f"Nao conseguiu checar DPI: {e}")

# Diferenca de resolucao
mss_w = mon["width"]
mss_h = mon["height"]
if pa_w != mss_w or pa_h != mss_h:
    scale_x = mss_w / pa_w
    scale_y = mss_h / pa_h
    print(f"\n*** MISMATCH DETECTADO ***")
    print(f"  mss captura em {mss_w}x{mss_h} (pixels fisicos)")
    print(f"  pyautogui usa {pa_w}x{pa_h} (pixels logicos)")
    print(f"  Fator de escala: {scale_x:.3f}x, {scale_y:.3f}y")
    print(f"  CORRECAO: dividir coordenadas do mss por {scale_x:.3f}")
else:
    print(f"\nResolucoes iguais - sem DPI mismatch")

# GetWindowRect vs ClientToScreen
try:
    import win32gui
    matches = []
    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = (win32gui.GetWindowText(hwnd) or "").strip()
        if any(k in t.lower() for k in ["sallazzar", "osa", "dofus", "retro"]):
            matches.append((hwnd, t))
    win32gui.EnumWindows(enum_handler, None)
    
    for hwnd, title in matches:
        wr = win32gui.GetWindowRect(hwnd)
        cr = win32gui.GetClientRect(hwnd)
        print(f'\nWindow "{title}":')
        print(f"  GetWindowRect: {wr}  -> {wr[2]-wr[0]}x{wr[3]-wr[1]}")
        print(f"  GetClientRect: {cr}  -> {cr[2]}x{cr[3]}")
        pt = ctypes.wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))
        print(f"  Client (0,0) -> Screen ({pt.x},{pt.y})")
        print(f"  Title bar height: {pt.y - wr[1]}")
        print(f"  Border left: {pt.x - wr[0]}")
except Exception as e:
    print(f"Erro ao checar janela: {e}")
