import os
import face_recognition
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import numpy as np
from PIL import Image  # Vamos usar a PIL (Pillow) que é mais compatível

# 1. Carregar configurações
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("❌ ERRO: Configure o arquivo .env com as chaves do Supabase!")
    exit()

supabase: Client = create_client(url, key)

PASTA_FOTOS = "students_db"

def migrar_tudo():
    print(f"📂 Lendo pasta: {PASTA_FOTOS}...")
    
    if not os.path.exists(PASTA_FOTOS):
        print(f"❌ A pasta {PASTA_FOTOS} não existe!")
        return

    arquivos = [f for f in os.listdir(PASTA_FOTOS) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"📊 Encontrados {len(arquivos)} arquivos de imagem.")
    
    sucesso = 0
    erros = 0

    for arquivo in arquivos:
        caminho_completo = os.path.join(PASTA_FOTOS, arquivo)
        nome_aluno = os.path.splitext(arquivo)[0] 
        
        # Tenta extrair turma do nome
        turma = "Desconhecida"
        if "_" in nome_aluno:
            partes = nome_aluno.split("_")
            nome_limpo = partes[0]
            turma_detectada = partes[-1]
            if len(turma_detectada) <= 3: 
                nome_aluno = nome_limpo
                turma = turma_detectada

        print(f"Processing: {nome_aluno}...", end=" ")

        try:
            # --- MUDANÇA AQUI: Usar PIL para forçar formato padrão ---
            # 1. Abre a imagem
            imagem_pil = Image.open(caminho_completo)
            
            # 2. Converte para RGB (Remove transparência, converte 16bit->8bit, etc)
            # Isso resolve o erro "Unsupported image type"
            imagem_pil = imagem_pil.convert('RGB')
            
            # 3. Transforma em números (numpy array)
            imagem_np = np.array(imagem_pil)

            # 4. Extrai a digital do rosto
            encodings = face_recognition.face_encodings(imagem_np)

            if len(encodings) > 0:
                rosto_matematica = encodings[0].tolist()
                
                dados = {
                    "nome": nome_aluno,
                    "turma": turma,
                    "face_encoding": json.dumps(rosto_matematica)
                }
                
                # Salvar no Supabase
                supabase.table("alunos").insert(dados).execute()
                print("✅ SUCESSO!")
                sucesso += 1
            else:
                print("⚠️  Nenhum rosto detectado na foto.")
                erros += 1

        except Exception as e:
            print(f"❌ Erro Técnico: {e}")
            erros += 1

    print("-" * 30)
    print(f"🏁 Fim da Migração. Sucessos: {sucesso} | Falhas: {erros}")

if __name__ == "__main__":
    migrar_tudo()