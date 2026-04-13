import cv2
import numpy as np
import os, glob

# 1. Carrega a imagem da luta
tela_path = "tela.jpg" # Deixe uma imagem de teste na pasta com esse nome
if not os.path.exists(tela_path):
    debug_imgs = sorted(glob.glob("debug/*.png")) + sorted(glob.glob("*.jpg"))
    if debug_imgs:
        tela_path = debug_imgs[-1]
    else:
        print("[ERRO] Nenhuma imagem encontrada pra testar.")
        exit()

img = cv2.imread(tela_path)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# ==========================================
# PASSO 1: CRIAR A ZONA SEGURA (Chão Azul)
# ==========================================
azul_claro = np.array([90, 100, 100])
azul_escuro = np.array([130, 255, 255])
mascara_azul = cv2.inRange(hsv, azul_claro, azul_escuro)

# Aqui nós "inflamos" o azul em 60 pixels para engolir os inimigos 
# que estão pisando na borda do chão azul
kernel = np.ones((60, 60), np.uint8)
zona_segura = cv2.dilate(mascara_azul, kernel, iterations=1)

# ==========================================
# O 2: FILTRAR O VERMELHO VIBRANTE
# ==========================================
# Ajustado para pegar SÓ vermelho forte (ignora marrom e amarelo)
vermelho_baixo1 = np.array([0, 160, 160])
vermelho_alto1 = np.array([10, 255, 255])
vermelho_baixo2 = np.array([170, 160, 160])
vermelho_alto2 = np.array([180, 255, 255])

mascara_v1 = cv2.inRange(hsv, vermelho_baixo1, vermelho_alto1)
mascara_v2 = cv2.inRange(hsv, vermelho_baixo2, vermelho_alto2)
mascara_vermelha = mascara_v1 + mascara_v2

# ==========================================
# PASSO 3: O PULO DO GATO (Juntar as duas coisas)
# ==========================================
# Procura o vermelho APENAS onde a Zona Segura é branca
alvos_reais = cv2.bitwise_and(mascara_vermelha, mascara_vermelha, mask=zona_segura)

# ==========================================
# O 4: DESENHAR NA TELA
# ==========================================
contornos, _ = cv2.findContours(alvos_reais, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

tela_desenhada = img.copy()
qtd_inimigos = 0

for cnt in contornos:
    area = cv2.contourArea(cnt)
    # Tem que ter um tamanho mínimo pra não pegar poeira, nem o mapa todo
    if 50 < area < 2000:
        x, y, w, h = cv2.boundingRect(cnt)
        cx, cy = x + w//2, y + h//2
        
        # Desenha a mira vermelha
        cv2.rectangle(tela_desenhada, (x, y), (x+w, y+h), (0, 0, 255), 3)
        cv2.circle(tela_desenhada, (cx, cy), 5, (0, 255, 255), -1)
        cv2.putText(tela_desenhada, "ALVO", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        qtd_inimigos += 1

print(f"🔥 Achei {qtd_inimigos} inimigos!")

# Mostra o processo pro "pai" da criança ver
cv2.imshow("1. Zona Segura (Onde ele pode olhar)", zona_segura)
cv2.imshow("2. O que sobrou de Vermelho", alvos_reais)
cv2.imshow("3. Resultado Final", tela_desenhada)

cv2.waitKey(0)
cv2.destroyAllWindows()