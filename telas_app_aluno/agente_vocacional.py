import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Carrega a chave de API (Certifique-se que o .env está na mesma pasta ou na raiz)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Erro: Chave da API não encontrada.")
    exit()

genai.configure(api_key=api_key)

# 2. Configuração do Modelo (Ajustado para evitar o erro 404)
# Note que usamos apenas 'gemini-1.5-flash' sem o prefixo 'models/' se der erro
PROMPT_SISTEMA = (
    "Você é o 'Guia Vocacional IA'. Ajude jovens brasileiros a encontrar sua carreira. "
    "Seja empático, faça uma pergunta por vez e foque em habilidades reais."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Nome simplificado para compatibilidade
    system_instruction=PROMPT_SISTEMA
)

def iniciar_agente():
    chat = model.start_chat(history=[])
    
    print("="*60)
    print("🎓 GUIA VOCACIONAL IA - AGENTE ATUALIZADO")
    print("="*60)
    
    # Mensagem inicial manual para evitar delay
    print("\nGuia: Olá! Vi que você mencionou que estaria construindo casas de alvenaria. Isso é muito interessante! Você gosta mais da parte de planejar como a casa será ou de colocar a mão na massa e ver a estrutura subir?")

    while True:
        mensagem = input("\nVocê: ")
        
        if mensagem.lower() in ['encerrar', 'fim', 'sair']:
            resumo = chat.send_message("Gere o relatório final com 3 sugestões de carreira baseadas no nosso papo.")
            print(f"\n--- 📝 RELATÓRIO FINAL ---\n{resumo.text}")
            break
            
        try:
            # Enviando a mensagem para o Gemini
            resposta = chat.send_message(mensagem)
            print(f"\nGuia: {resposta.text}")
        except Exception as e:
            print(f"\nErro técnico: {e}")
            print("Dica: Verifique se o nome do modelo está correto ou se sua chave tem permissão.")
            break

if __name__ == "__main__":
    iniciar_agente()