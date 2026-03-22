import google.generativeai as genai

# COLE AQUI E SÓ AQUI
MINHA_CHAVE = " AIzaSyAa2Ukn74VHy7A6DuWeM2DJTfnoh9N3bYMI ".strip() 

genai.configure(api_key=MINHA_CHAVE)

try:
    # Listar modelos é o teste mais básico de saúde da chave
    print("Testando validade da chave...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Chave ativa! Modelo encontrado: {m.name}")
            break # Se achou um, a chave tá viva!
except Exception as e:
    print(f"❌ O Google rejeitou a chave novamente: {e}")