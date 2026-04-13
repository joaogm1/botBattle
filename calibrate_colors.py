import cv2
import numpy as np
import mss
from typing import Tuple

# =========================
# CONFIG
# =========================
WINDOW_TITLE_CONTAINS = "Sallazzar"
BUTTON_SEARCH_REGION = (0.60, 0.70, 1.0, 1.0)
ENDTURN_TEMPLATE_PATH = "templates/combat/endturn.png"
# =========================


def find_window_rect_by_title(title_part: str) -> Tuple[int, int, int, int]:
    """Encontra retângulo da janela pelo título"""
    import win32gui

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


def grab_window_region(window_rect: Tuple[int, int, int, int], 
                       region_frac: Tuple[float, float, float, float]) -> np.ndarray:
    """Captura uma região específica da janela"""
    x, y, w, h = window_rect
    x1_frac, y1_frac, x2_frac, y2_frac = region_frac
    
    region_x = x + int(w * x1_frac)
    region_y = y + int(h * y1_frac)
    region_w = int(w * (x2_frac - x1_frac))
    region_h = int(h * (y2_frac - y1_frac))
    
    monitor = {
        "left": region_x,
        "top": region_y,
        "width": region_w,
        "height": region_h
    }
    
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def find_button_and_extract_colors(frame_bgr: np.ndarray, template_path: str):
    """Encontra o botão e analisa suas cores"""
    try:
        template = cv2.imread(template_path)
        if template is None:
            print(f"[ERRO] Não consegui carregar template: {template_path}")
            return None
        
        # Template matching
        result = cv2.matchTemplate(frame_bgr, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        if max_val < 0.5:
            print(f"[AVISO] Template matching baixo: {max_val:.3f}")
            return None
        
        h, w = template.shape[:2]
        x, y = max_loc
        
        # Extrai região do botão
        button_region = frame_bgr[y:y+h, x:x+w]
        
        return button_region, (x, y, w, h)
    except Exception as e:
        print(f"[ERRO] {e}")
        return None


def analyze_colors(button_region: np.ndarray, label: str):
    """Analisa e mostra estatísticas de cor"""
    print(f"\n{'='*60}")
    print(f"Análise do botão: {label}")
    print('='*60)
    
    # Estatísticas BGR
    b_mean = np.mean(button_region[:, :, 0])
    g_mean = np.mean(button_region[:, :, 1])
    r_mean = np.mean(button_region[:, :, 2])
    
    b_std = np.std(button_region[:, :, 0])
    g_std = np.std(button_region[:, :, 1])
    r_std = np.std(button_region[:, :, 2])
    
    print(f"\nCor média (BGR):")
    print(f"  B (azul):  {b_mean:.1f} ± {b_std:.1f}")
    print(f"  G (verde): {g_mean:.1f} ± {g_std:.1f}")
    print(f"  R (vermelho): {r_mean:.1f} ± {r_std:.1f}")
    
    # Converte para HSV para análise adicional
    hsv = cv2.cvtColor(button_region, cv2.COLOR_BGR2HSV)
    h_mean = np.mean(hsv[:, :, 0])
    s_mean = np.mean(hsv[:, :, 1])
    v_mean = np.mean(hsv[:, :, 2])
    
    print(f"\nCor média (HSV):")
    print(f"  H (matiz):      {h_mean:.1f}")
    print(f"  S (saturação):  {s_mean:.1f}")
    print(f"  V (brilho):     {v_mean:.1f}")
    
    # Valores mínimos e máximos
    b_min, b_max = np.min(button_region[:, :, 0]), np.max(button_region[:, :, 0])
    g_min, g_max = np.min(button_region[:, :, 1]), np.max(button_region[:, :, 1])
    r_min, r_max = np.min(button_region[:, :, 2]), np.max(button_region[:, :, 2])
    
    print(f"\nRange BGR:")
    print(f"  B: [{b_min}, {b_max}]")
    print(f"  G: [{g_min}, {g_max}]")
    print(f"  R: [{r_min}, {r_max}]")
    
    # Sugestão de threshold
    # Usa média ± 2*desvio padrão para cobrir ~95% dos pixels
    b_low = max(0, b_mean - 2*b_std)
    b_high = min(255, b_mean + 2*b_std)
    g_low = max(0, g_mean - 2*g_std)
    g_high = min(255, g_mean + 2*g_std)
    r_low = max(0, r_mean - 2*r_std)
    r_high = min(255, r_mean + 2*r_std)
    
    print(f"\n✅ THRESHOLD SUGERIDO para usar no código:")
    print(f"   {label.upper()}_BGR_MIN = np.array([{int(b_low)}, {int(g_low)}, {int(r_low)}])")
    print(f"   {label.upper()}_BGR_MAX = np.array([{int(b_high)}, {int(g_high)}, {int(r_high)}])")
    
    # Salva imagem para inspeção visual
    filename = f"debug_{label.lower()}.png"
    cv2.imwrite(filename, button_region)
    print(f"\n💾 Imagem salva: {filename}")


def main():
    print("="*70)
    print("CALIBRAÇÃO DE CORES - Detector de Turno")
    print("="*70)
    print("\nEste script vai analisar as cores dos botões verde e cinza")
    print("e sugerir os valores BGR ideais para detecção.\n")
    
    # Encontra janela
    window_rect = find_window_rect_by_title(WINDOW_TITLE_CONTAINS)
    if not window_rect:
        print(f"[ERRO] Janela não encontrada: '{WINDOW_TITLE_CONTAINS}'")
        return
    
    x, y, w, h = window_rect
    print(f"[OK] Janela encontrada: {w}x{h} em ({x}, {y})\n")
    
    print("-"*70)
    print("PASSO 1: Análise do botão VERDE (meu turno)")
    print("-"*70)
    input("Certifique-se que o botão está VERDE e pressione Enter...")
    
    frame_green = grab_window_region(window_rect, BUTTON_SEARCH_REGION)
    result_green = find_button_and_extract_colors(frame_green, ENDTURN_TEMPLATE_PATH)
    
    if result_green:
        button_green, bbox = result_green
        analyze_colors(button_green, "green")
    else:
        print("[ERRO] Não consegui encontrar o botão verde")
        return
    
    print("\n\n" + "-"*70)
    print("PASSO 2: Análise do botão CINZA (não é meu turno)")
    print("-"*70)
    input("Agora aguarde até o botão ficar CINZA e pressione Enter...")
    
    frame_gray = grab_window_region(window_rect, BUTTON_SEARCH_REGION)
    result_gray = find_button_and_extract_colors(frame_gray, ENDTURN_TEMPLATE_PATH)
    
    if result_gray:
        button_gray, bbox = result_gray
        analyze_colors(button_gray, "gray")
    else:
        print("[ERRO] Não consegui encontrar o botão cinza")
        return
    
    print("\n\n" + "="*70)
    print("CALIBRAÇÃO COMPLETA!")
    print("="*70)
    print("\nCopie os valores sugeridos acima para o script turn_detector_v2.py")
    print("nas variáveis GREEN_BGR_MIN/MAX e GRAY_BGR_MIN/MAX\n")


if __name__ == "__main__":
    main()
