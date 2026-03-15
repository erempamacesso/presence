import os
import face_recognition
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import numpy as np
from PIL import Image

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)
PASTA_FOTOS = "students_db"

def tentar_codificar(imagem_np, nome_metodo):
    """Tenta extrair o rosto e retorna o resultado ou None"""
    try:
        # Tenta pegar os encodings
        encs = face_recognition.face_encodings(imagem_np)
        if len(encs) > 0:
            print(f"      ✅ Funcionou com método: {nome_metodo}")
            return encs[0].tolist()
    except Exception as e:
        # Se o erro for o que já conhecemos, ignoramos para tentar o próximo
        if "Unsupported image type" not in str(e):
            print(f"      ⚠️  Erro estranho no método {nome_metodo}: {e}")
    return None

def migrar_tudo():
    print(f"📂 Lendo pasta: {PASTA_FOTOS}...")
    arquivos = [f for f in os.listdir(PASTA_FOTOS) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"📊 Encontrados {len(arquivos)} arquivos.")

    for arquivo in arquivos:
        caminho = os.path.join(PASTA_FOTOS, arquivo)
        nome = os.path.splitext(arquivo)[0]
        print(f"\nProcessing: {nome}...")

        # 1. Carrega imagem base com PIL
        pil_base = Image.open(caminho)
        rosto_codigo = None

        # --- TENTATIVA 1: RGB Padrão + Memória Contígua ---
        # (O comando ascontiguousarray organiza os bytes na memória para o C++ ler)
        img_rgb = pil_base.convert("RGB")
        np_rgb = np.ascontiguousarray(np.array(img_rgb, dtype=np.uint8))
        rosto_codigo = tentar_codificar(np_rgb, "RGB Padrão")

        # --- TENTATIVA 2: Se falhou, tenta Preto e Branco ---
        if rosto_codigo is None:
            img_gray = pil_base.convert("L") # L = Grayscale (8-bit pixels, black and white)
            np_gray = np.ascontiguousarray(np.array(img_gray, dtype=np.uint8))
            rosto_codigo = tentar_codificar(np_gray, "Preto e Branco")

        # --- TENTATIVA 3: Se falhou, Redimensiona (Diminui a resolução) ---
        if rosto_codigo is None:
            # Reduz para max 800px de largura mantendo proporção
            pil_small = pil_base.convert("RGB")
            pil_small.thumbnail((800, 800)) 
            np_small = np.ascontiguousarray(np.array(pil_small, dtype=np.uint8))
            rosto_codigo = tentar_codificar(np_small, "Reduzido")

        # --- RESULTADO FINAL ---
        if rosto_codigo:
            # Salvar no Banco
            turma = "Desconhecida"
            if "_" in nome:
                parts = nome.split("_")
                if len(parts[-1]) <= 3:
                    nome = parts[0]
                    turma = parts[-1]

            dados = {"nome": nome, "turma": turma, "face_encoding": json.dumps(rosto_codigo)}
            supabase.table("alunos").insert(dados).execute()
            print("   🎉 SUCESSO! Salvo no Supabase.")
        else:
            print("   ❌ FALHOU! Nenhuma das 3 tentativas funcionou para esta foto.")

if __name__ == "__main__":
    migrar_tudo()