import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

BASE_URL = "https://erempamxmd.streamlit.app/?t="

# Cria uma pasta nova pra não misturar com os antigos
pasta_destino = "qrcodes_com_texto"
if not os.path.exists(pasta_destino):
    os.makedirs(pasta_destino)

print("🚀 Gerando QR Codes com a turma no centro...")

for token, turma in MAPA_TURMAS.items():
    link_completo = BASE_URL + token
    
    # 1. Gera o QR Code com alta correção (para podermos cobrir o meio)
    qr = qrcode.QRCode(
        version=5, # Versão um pouco maior pra ter mais "pontinhos" e facilitar a leitura
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(link_completo)
    qr.make(fit=True)

    # Cria a imagem do QR Code e converte para RGB (para podermos desenhar nela)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # 2. Prepara para desenhar o quadrado no centro
    draw = ImageDraw.Draw(img_qr)
    img_width, img_height = img_qr.size
    
    # O tamanho do quadrado branco será 25% do tamanho do QR Code
    box_size = int(img_width * 0.25)
    xmin = (img_width - box_size) // 2
    ymin = (img_height - box_size) // 2
    xmax = xmin + box_size
    ymax = ymin + box_size
    
    # Desenha o fundo branco no meio
    draw.rectangle([xmin, ymin, xmax, ymax], fill="white", outline="black", width=3)
    
    # 3. Tenta carregar uma fonte bonita do Windows (Arial). Se não achar, usa a básica.
    try:
        font = ImageFont.truetype("arialbd.ttf", int(box_size * 0.35)) # Arial Bold
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", int(box_size * 0.35))
        except IOError:
            font = ImageFont.load_default()

    # 4. Centraliza o texto "1º A" dentro do quadradinho branco
    try:
        # Para versões mais novas do Python/Pillow
        bbox = draw.textbbox((0, 0), turma, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except AttributeError:
        # Para versões mais antigas
        text_w, text_h = draw.textsize(turma, font=font)
        
    text_x = xmin + (box_size - text_w) // 2
    text_y = ymin + (box_size - text_h) // 2 - (text_h * 0.1) # Um leve ajuste vertical
    
    # Escreve o texto
    draw.text((text_x, text_y), turma, fill="black", font=font)

    # Salva a imagem na nova pasta
    nome_arquivo = turma.replace("º ", "_").replace(" ", "_") + ".png"
    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo)
    img_qr.save(caminho_arquivo)
    
    print(f"✅ Feito: {nome_arquivo}")

print(f"🎉 Pronto! Abra a pasta '{pasta_destino}' e veja o resultado!")