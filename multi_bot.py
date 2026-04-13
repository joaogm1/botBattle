import time
import os
import subprocess
import cv2
import numpy as np
import mss
import pyautogui
import keyboard
import win32gui
import win32con
from dataclasses import dataclass

# ================================================================
#  CONFIGURAÇÃO DE CONTAS E AÇÕES
# ================================================================
# "play" -> O bot vai usar skills (cast_skill_and_click.py) e passar turno.
# "pass" -> O bot vai IGNORAR os ataques e apenas passar o turno (TAB).
ACCOUNTS_CONFIG = {
    "Sallazzar": "play",
    "Osa-dos-sapos": "play",
    "Osa-do-fogo": "play",
    "Pristieamer": "play",
}

# ================================================================
#  CARREGAMENTO DE IMAGENS (COM CORES REAIS)
# ================================================================
COMBAT_TEMPLATES_DIR = "templates/combat"

def carregar_imagem(nome_arquivo):
    return cv2.imread(os.path.join(COMBAT_TEMPLATES_DIR, nome_arquivo), cv2.IMREAD_COLOR)

TPL_CHOOSE       = carregar_imagem("choose.png")
TPL_READY        = carregar_imagem("ready.png")
TPL_ENDTURN      = carregar_imagem("endturn.png")       # Verde
TPL_ENDTURN_GRAY = carregar_imagem("endturn_gray.png")  # Cinza
TPL_VICTORY      = carregar_imagem("victory.png")

# ================================================================
#  CONFIANÇA POR TEMPLATE
#  - Verde e Vitória: mais exigente (cores únicas, não tem falso positivo)
#  - Cinza e Ready: mais tolerante (pode variar por sombra/rato)
# ================================================================
CONFIANCA_VERDE   = 0.85
CONFIANCA_VITORIA = 0.85
CONFIANCA_READY   = 0.75  # ← Mais tolerante
CONFIANCA_CINZA   = 0.70  # ← Mais tolerante (principal causa do timeout anterior)
CONFIANCA_CHOOSE  = 0.75

# ================================================================
#  SEGURANÇA
# ================================================================
LIMITE_DESISTENCIA = 30  # Aumentado de 15 → 30 (cada ciclo = ~0.5s, então 15s de tolerância)

@dataclass
class BotAccount:
    name: str
    hwnd: int
    rect: dict
    victory: bool = False

def encontrar_janelas():
    matches = []
    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = (win32gui.GetWindowText(hwnd) or "").strip()
        for acc_name in ACCOUNTS_CONFIG.keys():
            if acc_name.lower() in t.lower():
                matches.append((acc_name, hwnd))
                break
    win32gui.EnumWindows(enum_handler, None)

    contas = []
    for nome, hwnd in matches:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        rect = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        contas.append(BotAccount(name=nome, hwnd=hwnd, rect=rect))
    return contas

def procurar_botao(frame_tela, template, confianca_minima):
    if template is None:
        return False
    resultado = cv2.matchTemplate(frame_tela, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(resultado)
    return max_val >= confianca_minima

def main():
    contas = encontrar_janelas()
    if not contas:
        print("❌ Nenhuma janela de conta encontrada!")
        return

    turnos_sem_ver_nada = 0

    with mss.mss() as sct:
        monitor_inteiro = sct.monitors[1]  # Pega o monitor principal

        while True:
            sct_img = sct.grab(monitor_inteiro)
            frame_tela = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)

            alguem_em_combate = False

            for acc in contas:
                if acc.victory:
                    continue

                x, y = acc.rect["left"], acc.rect["top"]
                w, h = acc.rect["width"], acc.rect["height"]

                if w <= 0 or h <= 0:
                    continue

                frame_janela = frame_tela[y:y+h, x:x+w]
                if frame_janela.size == 0:
                    continue

                # ============================================================
                # DETECÇÃO COM CONFIANÇA INDIVIDUAL POR BOTÃO + LOG DE VALORES
                # ============================================================
                achou_choose  = procurar_botao(frame_janela, TPL_CHOOSE,       CONFIANCA_CHOOSE)
                achou_ready   = procurar_botao(frame_janela, TPL_READY,        CONFIANCA_READY)
                achou_verde   = procurar_botao(frame_janela, TPL_ENDTURN,      CONFIANCA_VERDE)
                achou_cinza   = procurar_botao(frame_janela, TPL_ENDTURN_GRAY, CONFIANCA_CINZA)
                achou_vitoria = procurar_botao(frame_janela, TPL_VICTORY,      CONFIANCA_VITORIA)

                # 1. VERIFICAÇÃO DE COMBATE
                if achou_choose or achou_ready or achou_verde or achou_cinza or achou_vitoria:
                    alguem_em_combate = True
                    turnos_sem_ver_nada = 0

                # 2. AÇÕES
                if achou_vitoria:
                    acc.victory = True
                    keyboard.press_and_release('enter')
                    continue

                elif achou_choose:
                    keyboard.press_and_release('tab')
                    time.sleep(0.15)

                elif achou_ready:
                    keyboard.press_and_release('tab')
                    time.sleep(0.03)
                    keyboard.press_and_release('tab')
                    time.sleep(0.15)

                elif achou_verde:
                    acao_da_conta = ACCOUNTS_CONFIG.get(acc.name, "pass")

                    if acao_da_conta == "play":
                        env_vars = os.environ.copy()
                        env_vars["CURRENT_ACCOUNT"] = acc.name
                        subprocess.run(["python", "cast_skill_and_click.py"], env=env_vars)
                    elif acao_da_conta == "pass":
                        time.sleep(0.3)

                    keyboard.press_and_release('tab')
                    time.sleep(0.25)

            # === LÓGICA DE SEGURANÇA (FAILSAFE) ===
            if not alguem_em_combate:
                turnos_sem_ver_nada += 1
                if turnos_sem_ver_nada >= LIMITE_DESISTENCIA:
                    print("TIMEOUT")
                    break

            if all(acc.victory for acc in contas):
                break

            time.sleep(0.08)  # era 0.3

if __name__ == "__main__":
    if TPL_CHOOSE is None or TPL_READY is None or TPL_ENDTURN is None or TPL_ENDTURN_GRAY is None:
        print("\n❌ ERRO FATAL: Alguma imagem de botão (ready, endturn, endturn_gray) está faltando na pasta 'templates/combat/'. O bot não pode iniciar.")
    else:
        main()
