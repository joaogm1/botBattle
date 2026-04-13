"""
Calibrador de Tiles Azuis - Ajuste os valores HSV interativamente.

Uso:
  1. Rode o script e posicione a janela do jogo com tiles azuis visiveis
  2. Clique nos tiles azuis para ver os valores HSV
  3. Ajuste os sliders ate a mascara detectar apenas os tiles
  4. Copie os valores finais para cast_skill_and_click.py

Controles:
  - Clique esquerdo: mostra HSV do pixel
  - Tecla 'c': captura nova screenshot
  - Tecla 'q': sai e mostra valores finais
  - Tecla 's': salva imagens de debug
"""

import cv2
import numpy as np
import mss
from typing import Tuple, Optional
import os


# =========================
# CONFIG
# =========================
WINDOW_TITLE_CONTAINS = os.environ.get("CURRENT_ACCOUNT", "Sallazzar")

# Valores iniciais (atuais do cast_skill_and_click.py)
INITIAL_H_LOW = 85
INITIAL_S_LOW = 60
INITIAL_V_LOW = 40
INITIAL_H_HIGH = 145
INITIAL_S_HIGH = 255
INITIAL_V_HIGH = 255
# =========================


def find_window_rect(title_part: str) -> Optional[Tuple[int, int, int, int]]:
    """Encontra retangulo da janela pelo titulo"""
    try:
        import win32gui
    except ImportError:
        print("[ERRO] pywin32 nao instalado. Rode: pip install pywin32")
        return None

    matches = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        t = (win32gui.GetWindowText(hwnd) or "").strip()
        if title_part.lower() in t.lower():
            matches.append(hwnd)

    win32gui.EnumWindows(enum_handler, None)
    if not matches:
        return None

    left, top, right, bottom = win32gui.GetWindowRect(matches[0])
    return (left, top, right - left, bottom - top)


def grab_window(rect: Tuple[int, int, int, int]) -> np.ndarray:
    """Captura a janela"""
    x, y, w, h = rect
    monitor = {"left": x, "top": y, "width": w, "height": h}
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


class BlueTileCalibrator:
    def __init__(self, window_rect: Tuple[int, int, int, int]):
        self.rect = window_rect
        self.frame = None
        self.hsv_frame = None
        
        # Valores HSV
        self.h_low = INITIAL_H_LOW
        self.s_low = INITIAL_S_LOW
        self.v_low = INITIAL_V_LOW
        self.h_high = INITIAL_H_HIGH
        self.s_high = INITIAL_S_HIGH
        self.v_high = INITIAL_V_HIGH
        
        # Historico de clicks
        self.clicked_hsv = []
        
    def capture(self):
        """Captura nova screenshot"""
        self.frame = grab_window(self.rect)
        self.hsv_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
        print("[OK] Nova captura realizada")
        
    def get_mask(self) -> np.ndarray:
        """Gera mascara com valores HSV atuais"""
        if self.hsv_frame is None:
            return None
        lower = np.array([self.h_low, self.s_low, self.v_low], dtype=np.uint8)
        upper = np.array([self.h_high, self.s_high, self.v_high], dtype=np.uint8)
        mask = cv2.inRange(self.hsv_frame, lower, upper)
        # Morfologia leve
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        return mask
    
    def on_trackbar(self, val):
        """Callback dos trackbars (nao faz nada, valores sao lidos diretamente)"""
        pass
    
    def mouse_callback(self, event, x, y, flags, param):
        """Callback de clique do mouse"""
        if event == cv2.EVENT_LBUTTONDOWN and self.hsv_frame is not None:
            if 0 <= y < self.hsv_frame.shape[0] and 0 <= x < self.hsv_frame.shape[1]:
                h, s, v = self.hsv_frame[y, x]
                b, g, r = self.frame[y, x]
                self.clicked_hsv.append((h, s, v))
                print(f"\n[CLICK] Posicao ({x}, {y})")
                print(f"  HSV: H={h}, S={s}, V={v}")
                print(f"  BGR: B={b}, G={g}, R={r}")
                
                if len(self.clicked_hsv) > 1:
                    h_vals = [c[0] for c in self.clicked_hsv]
                    s_vals = [c[1] for c in self.clicked_hsv]
                    v_vals = [c[2] for c in self.clicked_hsv]
                    print(f"\n  [SUGESTAO baseada em {len(self.clicked_hsv)} cliques]:")
                    print(f"    H: {min(h_vals)} - {max(h_vals)}")
                    print(f"    S: {min(s_vals)} - {max(s_vals)}")
                    print(f"    V: {min(v_vals)} - {max(v_vals)}")
    
    def run(self):
        """Loop principal"""
        self.capture()  # Captura primeiro para ter dimensoes
        
        cv2.namedWindow("Calibrador Blue Tiles", cv2.WINDOW_NORMAL)
        cv2.namedWindow("Mascara HSV", cv2.WINDOW_NORMAL)
        
        # Mostra imagens iniciais antes de criar trackbars
        cv2.imshow("Calibrador Blue Tiles", self.frame)
        cv2.imshow("Mascara HSV", self.get_mask())
        cv2.waitKey(1)
        
        # Trackbars
        cv2.createTrackbar("H Low", "Mascara HSV", self.h_low, 180, self.on_trackbar)
        cv2.createTrackbar("H High", "Mascara HSV", self.h_high, 180, self.on_trackbar)
        cv2.createTrackbar("S Low", "Mascara HSV", self.s_low, 255, self.on_trackbar)
        cv2.createTrackbar("S High", "Mascara HSV", self.s_high, 255, self.on_trackbar)
        cv2.createTrackbar("V Low", "Mascara HSV", self.v_low, 255, self.on_trackbar)
        cv2.createTrackbar("V High", "Mascara HSV", self.v_high, 255, self.on_trackbar)
        
        cv2.setMouseCallback("Calibrador Blue Tiles", self.mouse_callback)
        
        print("\n" + "="*60)
        print("CALIBRADOR DE TILES AZUIS")
        print("="*60)
        print("Controles:")
        print("  - Clique esquerdo: mostra HSV do pixel")
        print("  - 'c': captura nova screenshot")
        print("  - 's': salva imagens de debug")
        print("  - 'q': sai e mostra valores finais")
        print("="*60 + "\n")
        
        while True:
            # Le valores dos trackbars
            self.h_low = cv2.getTrackbarPos("H Low", "Mascara HSV")
            self.h_high = cv2.getTrackbarPos("H High", "Mascara HSV")
            self.s_low = cv2.getTrackbarPos("S Low", "Mascara HSV")
            self.s_high = cv2.getTrackbarPos("S High", "Mascara HSV")
            self.v_low = cv2.getTrackbarPos("V Low", "Mascara HSV")
            self.v_high = cv2.getTrackbarPos("V High", "Mascara HSV")
            
            # Gera mascara
            mask = self.get_mask()
            if mask is None:
                continue
            
            # Analisa contornos
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Desenha resultado na imagem
            display = self.frame.copy()
            blue_pixels = cv2.countNonZero(mask)
            
            # Desenha contornos e info
            valid_tiles = 0
            for c in contours:
                area = cv2.contourArea(c)
                if area < 50:
                    continue
                    
                x, y, w, h = cv2.boundingRect(c)
                ratio = w / float(h) if h > 0 else 0
                
                # Calcula solidez
                hull = cv2.convexHull(c)
                hull_area = cv2.contourArea(hull)
                solidity = area / hull_area if hull_area > 0 else 0
                
                # Cor baseada em se passa nos filtros
                # Filtros normais: area 150-6000, ratio 1.4-2.8, solidez 0.88+
                if 150 <= area <= 6000 and 1.4 <= ratio <= 2.8 and solidity >= 0.88:
                    color = (0, 255, 0)  # Verde = passaria filtro normal
                    valid_tiles += 1
                elif 60 <= area <= 20000 and 1.05 <= ratio <= 4.0 and solidity >= 0.70:
                    color = (0, 255, 255)  # Amarelo = passaria fallback
                else:
                    color = (0, 0, 255)  # Vermelho = nao passa
                
                cv2.rectangle(display, (x, y), (x+w, y+h), color, 2)
                cv2.putText(display, f"a={int(area)}", (x, y-25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(display, f"r={ratio:.2f}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(display, f"s={solidity:.2f}", (x+w-50, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Info no topo
            info = f"Blue pixels: {blue_pixels} | Tiles validos: {valid_tiles} | HSV: ({self.h_low}-{self.h_high}, {self.s_low}-{self.s_high}, {self.v_low}-{self.v_high})"
            cv2.putText(display, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
            
            # Legenda
            cv2.putText(display, "Verde=normal | Amarelo=fallback | Vermelho=rejeitado", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(display, "Verde=normal | Amarelo=fallback | Vermelho=rejeitado", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            
            # Mostra mascara colorida
            mask_display = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            
            cv2.imshow("Calibrador Blue Tiles", display)
            cv2.imshow("Mascara HSV", mask_display)
            
            key = cv2.waitKey(50) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.capture()
            elif key == ord('s'):
                ts = __import__('time').strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"debug/calibrate_frame_{ts}.png", display)
                cv2.imwrite(f"debug/calibrate_mask_{ts}.png", mask)
                print(f"[OK] Salvo debug/calibrate_*_{ts}.png")
        
        cv2.destroyAllWindows()
        
        # Mostra valores finais
        print("\n" + "="*60)
        print("VALORES FINAIS PARA cast_skill_and_click.py:")
        print("="*60)
        print(f"\n# Azul do tile (HSV)")
        print(f"HSV_LOWER = ({self.h_low}, {self.s_low}, {self.v_low})")
        print(f"HSV_UPPER = ({self.h_high}, {self.s_high}, {self.v_high})")
        
        if self.clicked_hsv:
            h_vals = [c[0] for c in self.clicked_hsv]
            s_vals = [c[1] for c in self.clicked_hsv]
            v_vals = [c[2] for c in self.clicked_hsv]
            print(f"\n# Baseado nos {len(self.clicked_hsv)} cliques:")
            margin = 10
            h_min = max(0, min(h_vals) - margin)
            h_max = min(180, max(h_vals) + margin)
            s_min = max(0, min(s_vals) - 30)
            s_max = min(255, max(s_vals) + 30)
            v_min = max(0, min(v_vals) - 30)
            v_max = min(255, max(v_vals) + 30)
            print(f"HSV_LOWER = ({h_min}, {s_min}, {v_min})")
            print(f"HSV_UPPER = ({h_max}, {s_max}, {v_max})")
        
        print("\n" + "="*60)


def main():
    print("="*60)
    print("CALIBRADOR DE TILES AZUIS")
    print("="*60)
    print(f"\nProcurando janela: '{WINDOW_TITLE_CONTAINS}'...")
    
    rect = find_window_rect(WINDOW_TITLE_CONTAINS)
    if not rect:
        print(f"[ERRO] Janela nao encontrada: '{WINDOW_TITLE_CONTAINS}'")
        print("\nDica: defina a variavel WINDOW_TITLE_CONTAINS ou")
        print("      CURRENT_ACCOUNT com parte do titulo da janela.")
        return
    
    x, y, w, h = rect
    print(f"[OK] Janela encontrada: {w}x{h} em ({x}, {y})")
    
    # Cria pasta debug se nao existir
    os.makedirs("debug", exist_ok=True)
    
    calibrator = BlueTileCalibrator(rect)
    calibrator.run()


if __name__ == "__main__":
    main()
