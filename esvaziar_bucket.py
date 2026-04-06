from supabase import create_client

# Suas credenciais
SUPABASE_URL = "https://ykbwrfstozvvreuoloxg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlrYndyZnN0b3p2dnJldW9sb3hnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzAzMDI3NzQsImV4cCI6MjA4NTg3ODc3NH0.mC8vanbKYCg-JjhVj01STA-z31VgEQ_3drPY8fXFHdE"

BUCKET_NAME = "fotos-alunos"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def esvaziar_bucket():
    print(f"🧨 Preparando para esvaziar o bucket '{BUCKET_NAME}'...\n")
    
    total_deletado = 0
    
    while True:
        # Pede uma leva de arquivos
        arquivos = supabase.storage.from_(BUCKET_NAME).list("", {"limit": 500})
        
        # Filtra os nomes, ignorando pastas vazias do sistema
        nomes = [arq['name'] for arq in arquivos if arq['name'] not in [".emptyFolderPlaceholder", ".DS_Store"]]
        
        if not nomes:
            break # Se não tem mais nada, sai do loop
            
        print(f"🗑️ Apagando lote de {len(nomes)} fotos...")
        # A API do Supabase permite deletar uma lista inteira de vez
        supabase.storage.from_(BUCKET_NAME).remove(nomes)
        total_deletado += len(nomes)
        
    print(f"\n✅ LIXEIRA ESVAZIADA! Total de {total_deletado} arquivos deletados permanentemente.")

if __name__ == "__main__":
    esvaziar_bucket()