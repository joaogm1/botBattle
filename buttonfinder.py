import cv2
import numpy as np
import mss
import time
import os

# ==========================================
# CONFIGURAÇÕES
# ==========================================
# Se os seus templates estiverem em uma pasta específica, coloque o caminho aqui.
# Ex: PASTA = "templates/combat" (Deixe "" se estiverem na mesma pasta do script)
PASTA = "templates/combat" 

# Nível de exigência (0.0 a 1.0). 0.85 significa 85% de semelhança exata (incluindo cor)
CONFIANCA_MINIMA = 0.85 

botoes = {
    "CHOOSE (Desafios)": os.path.join(PASTA, "choose.png"),
    "MEU TURNO (Ativo)": os.path.join(PASTA, "endturn.png"),
    "ESPERANDO (Cinza)": os.path.join(PASTA, "endturn_gray.png")
}

# Carrega os templates FORÇANDO a leitura das cores (cv2.IMREAD_COLOR)
templates_carregados = {}
for nome, caminho in botoes.items():
    img = cv2.imread(caminho, cv2.IMREAD_COLOR)
    if img is None:
        print(f"❌ ERRO: Não achei a imagem '{caminho}' para o botão {nome}.")
    else:
        templates_carregados[nome] = img

if len(templates_carregados) < 3:
    print("⚠️  Arrume os caminhos das imagens antes de continuar.")
    exit()

print("🤖 Radar de Botões Ativado!")
print("Deixe o jogo visível. O script vai printar o que ele está enxergando.")
print("Pressione Ctrl+C no terminal para parar.\n")
print("-" * 40)

def procurar_botao(frame_tela, template, confianca_minima):
    """Procura um template colorido na tela colorida e retorna se achou."""
    resultado = cv2.matchTemplate(frame_tela, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(resultado)
    return max_val >= confianca_minima, max_val

# Loop principal de captura
with mss.mss() as sct:
    monitor = sct.monitors[1]  # Pega o monitor principal inteiro

    while True:
        # 1. Tira print da tela muito rápido
        sct_img = sct.grab(monitor)
        
        # 2. Converte para o formato de cores padrão do OpenCV (BGR)
        frame_tela = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
        
        detectados = []
        
        # 3. Testa cada botão na tela atual
        for nome, template in templates_carregados.items():
            achou, confianca_atual = procurar_botao(frame_tela, template, CONFIANCA_MINIMA)
            
            if achou:
                detectados.append(f"✅ {nome} (Confiança: {confianca_atual:.2f})")
        
        # 4. Limpa o console e mostra o resultado atualizado (estilo painel)
        os.system('cls' if os.name == 'nt' else 'clear')
        print("🔍 ESCANEANDO BOTÕES...\n")
        
        if detectados:
            for d in detectados:
                print(d)
        else:
            print("Nenhum botão detectado na tela no momento.")
            
        # Pausa pequena para não fritar o processador e dar tempo de você ler
        time.sleep(0.5)