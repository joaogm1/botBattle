import time
import os
import glob
import subprocess
import cv2
import numpy as np
import mss
import pyautogui
import win32gui
import win32con

# ==========================================
# CONFIGURAÇÕES DO CAÇADOR
# ==========================================
LIDER = "Sallazzar"
# Resolução padrão para todas as janelas
TARGET_X = 0
TARGET_Y = 0
TARGET_W = 1700
TARGET_H = 1300
PASTA_MOBS = "templates/mobs/*.png"
TEMPLATE_READY = "templates/combat/ready.png"
TEMPLATE_CHOOSE = "templates/combat/choose.png"
TEMPLATE_VICTORY = "templates/combat/victory.png"
TEMPLATE_ENDTURN = "templates/combat/endturn.png" # Adicionado para saber se já estamos lutando
CONFIANCA_MOB = 0.70  

# Lista de personagens (mesma do multi_bot.py)
PERSONAGENS = ["Sallazzar", "Osa-dos-sapos", "Osa-do-fogo", "Pristieamer"]

def redimensionar_todas_janelas():
    
    def set_borderless(hwnd):
        """Remove bordas da janela"""
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        style &= ~(
            win32con.WS_CAPTION | win32con.WS_THICKFRAME |
            win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | 
            win32con.WS_SYSMENU
        )
        ex_style &= ~(
            win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_CLIENTEDGE |
            win32con.WS_EX_STATICEDGE | win32con.WS_EX_WINDOWEDGE
        )
        
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        
        win32gui.SetWindowPos(
            hwnd, None, 0, 0, 0, 0,
            win32con.SWP_NOZORDER | win32con.SWP_NOMOVE | 
            win32con.SWP_NOSIZE | win32con.SWP_FRAMECHANGED
        )
    
    def aplicar_resolucao(hwnd):
        """Aplica resolução e posição configuradas"""
        win32gui.SetWindowPos(
            hwnd, None,
            TARGET_X, TARGET_Y, TARGET_W, TARGET_H,
            win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED
        )
    
    janelas_ajustadas = 0
    
    def enum_handler(hwnd, _):
        nonlocal janelas_ajustadas
        if not win32gui.IsWindowVisible(hwnd):
            return
        titulo = (win32gui.GetWindowText(hwnd) or "").strip()
        
        for personagem in PERSONAGENS:
            if personagem.lower() in titulo.lower():
                try:
                    # Restaura se estiver minimizada
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.1)
                    
                    # Aplica borderless e resolução
                    set_borderless(hwnd)
                    time.sleep(0.05)
                    aplicar_resolucao(hwnd)
                    
                    janelas_ajustadas += 1
                except Exception:
                    pass
                break
    
    win32gui.EnumWindows(enum_handler, None)
    time.sleep(0.3)

def encontrar_janela(nome):
    matches = []
    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd): return
        t = (win32gui.GetWindowText(hwnd) or "").strip()
        if nome.lower() in t.lower(): matches.append(hwnd)
    win32gui.EnumWindows(enum_handler, None)
    if matches:
        left, top, right, bottom = win32gui.GetWindowRect(matches[0])
        return {"left": left, "top": top, "width": right - left, "height": bottom - top}
    return None

def tirar_print_bgr(monitor):
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def procurar_imagem(frame, template_path, confianca=0.70):
    if not os.path.exists(template_path): return None
    tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None: return None
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    if max_val >= confianca:
        return (max_loc[0] + tpl.shape[1]//2, max_loc[1] + tpl.shape[0]//2)
    return None

# --- NOVA FUNÇÃO ---
def estou_em_combate(frame):
    """Verifica se qualquer botão de combate está visível"""
    if procurar_imagem(frame, TEMPLATE_CHOOSE, 0.70): return True
    if procurar_imagem(frame, TEMPLATE_READY, 0.70): return True
    if procurar_imagem(frame, TEMPLATE_ENDTURN, 0.60): return True
    return False

def main():
    redimensionar_todas_janelas()

    monitor = encontrar_janela(LIDER)
    if not monitor:
        print(f"[ERRO] Janela '{LIDER}' não encontrada!")
        return

    templates_mobs = glob.glob(PASTA_MOBS)
    if not templates_mobs:
        print("[ERRO] Nenhum template de monstro encontrado em 'templates/mobs/'!")
        return

    while True:
        frame = tirar_print_bgr(monitor)

        if estou_em_combate(frame):
            subprocess.run(["python", "multi_bot.py"])
            time.sleep(0.5)
            frame_pos_luta = tirar_print_bgr(monitor)
            if procurar_imagem(frame_pos_luta, TEMPLATE_VICTORY, confianca=0.70):
                pyautogui.press('enter')
                time.sleep(0.3)
            continue

        alvo_encontrado = None
        for tpl_mob in templates_mobs:
            pos = procurar_imagem(frame, tpl_mob, CONFIANCA_MOB)
            if pos:
                alvo_encontrado = pos
                break

        if alvo_encontrado:
            x_click = monitor['left'] + alvo_encontrado[0]
            y_click = monitor['top'] + alvo_encontrado[1]
            pyautogui.moveTo(x_click, y_click, duration=0.0)
            pyautogui.click()

            combate_iniciado = False
            tempo_limite = time.time() + 5.0
            while time.time() < tempo_limite:
                time.sleep(0.2)
                if estou_em_combate(tirar_print_bgr(monitor)):
                    combate_iniciado = True
                    break

            if combate_iniciado:
                subprocess.run(["python", "multi_bot.py"])
                time.sleep(0.5)
                if procurar_imagem(tirar_print_bgr(monitor), TEMPLATE_VICTORY, confianca=0.70):
                    pyautogui.press('enter')
                    time.sleep(0.3)

        time.sleep(0.5)

if __name__ == "__main__":
    main()