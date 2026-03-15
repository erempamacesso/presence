import os
import face_recognition
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import numpy as np
from PIL import Image

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

    for arquivo in arquivos:
        caminho_completo = os.path.join(PASTA_FOTOS, arquivo)
        nome_aluno = os.path.splitext(arquivo)[0] 
        print(f"\nProcessing: {nome_aluno}...")

        try:
            # 1. Abrir com PIL
            pil_image = Image.open(caminho_completo)
            
            # 2. Forçar RGB
            pil_image = pil_image.convert("RGB")
            
            # 3. Converter para array NUMPY FORÇANDO O TIPO UINT8 (O Segredo!)
            # O dlib só aceita uint8. Se for int32 ou float, ele trava.
            imagem_np = np.array(pil_image, dtype=np.uint8)

            # DIAGNÓSTICO (Vai aparecer no terminal)
            print(f"   ℹ️  Debug Info: Tipo={imagem_np.dtype}, Shape={imagem_np.shape}")

            # 4. Extrair digital
            encodings = face_recognition.face_encodings(imagem_np)

            if len(encodings) > 0:
                rosto_matematica = encodings[0].tolist()
                
                # Prepara dados (simples validação de turma)
                turma = "Desconhecida"
                if "_" in nome_aluno:
                    parts = nome_aluno.split("_")
                    if len(parts[-1]) <= 3:
                        nome_aluno = parts[0]
                        turma = parts[-1]

                dados = {
                    "nome": nome_aluno,
                    "turma": turma,
                    "face_encoding": json.dumps(rosto_matematica)
                }
                
                supabase.table("alunos").insert(dados).execute()
                print("   ✅ SUCESSO! Salvo no Supabase.")
            else:
                print("   ⚠️  Nenhum rosto encontrado.")

        except Exception as e:
            print(f"   ❌ ERRO CRÍTICO: {e}")
            # Se der erro, tenta imprimir o tipo da variável pra gente entender
            try: print(f"   Tipo da imagem no momento do erro: {type(imagem_np)}") 
            except: pass

if __name__ == "__main__":
    migrar_tudo()