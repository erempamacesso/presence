import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Carrega a chave de API do arquivo .env por segurança
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Erro: Chave da API não encontrada. Certifique-se de ter criado o arquivo .env com a variável GEMINI_API_KEY.")
    exit()

genai.configure(api_key=api_key)

# 2. O "Cérebro" do Agente (Instruções de Sistema)
PROMPT_SISTEMA = (
    "Você é o 'Guia Vocacional IA', um orientador de carreiras experiente, focado em ajudar jovens brasileiros. "
    "Seu objetivo é guiar o usuário para descobrir caminhos profissionais baseados em seus interesses, "
    "habilidades e na realidade do mercado de trabalho (incluindo faculdade, cursos técnicos ou empreendedorismo). "
    "DIRETRIZES: "
    "- Seja empático, encorajador e use uma linguagem natural de conversa. "
    "- Faça apenas UMA pergunta por vez para não sobrecarregar o jovem. "
    "- Investigue hobbies, matérias escolares favoritas e atividades que o jovem faz no tempo livre. "
    "- Vá afunilando as opções aos poucos com base nas respostas. "
    "- Quando for solicitado o relatório final, forneça 3 sugestões de carreiras, explicando o 'porquê' "
    "do match para cada uma e indicando próximos passos práticos."
)

# 3. Inicialização do Modelo Gemini
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=PROMPT_SISTEMA
)

# 4. Motor da Conversa
def iniciar_agente():
    # Inicia o chat com memória vazia
    chat = model.start_chat(history=[])
    
    print("="*60)
    print("🎓 BEM-VINDO AO GUIA VOCACIONAL IA")
    print("Vamos desenhar o seu futuro profissional juntos!")
    print("(Digite 'encerrar' a qualquer momento para receber seu relatório final)")
    print("="*60)
    
    # Pergunta inicial de quebra-gelo
    print("\nGuia: Olá! Que bom ter você aqui. Para a gente começar a mapear o seu perfil, me conta: se você tivesse um sábado inteiro livre e dinheiro não fosse problema, o que você passaria o dia fazendo?")

    while True:
        mensagem = input("\nVocê: ")
        
        # Lógica de encerramento e geração do relatório
        if mensagem.lower() in ['encerrar', 'fim', 'sair']:
            print("\nGuia: Entendido! Estou analisando tudo o que conversamos para montar o seu perfil de carreira...")
            try:
                # O agente faz uma última auto-consulta para gerar o resumo com base no histórico
                pedido_resumo = "O usuário decidiu encerrar a sessão. Com base em todo o nosso histórico de conversa, crie o relatório final. Sugira 3 carreiras adequadas, detalhando os motivos e os próximos passos práticos no Brasil."
                resumo = chat.send_message(pedido_resumo)
                
                print(f"\n{'-'*20} 📝 SEU RELATÓRIO VOCACIONAL {'-'*20}\n")
                print(resumo.text)
                print(f"\n{'-'*65}")
            except Exception as e:
                print(f"Erro ao gerar o relatório: {e}")
            break
            
        # Lógica da conversa contínua
        try:
            resposta = chat.send_message(mensagem)
            print(f"\nGuia: {resposta.text}")
        except Exception as e:
            print(f"\nOps, ocorreu um erro de comunicação com a IA: {e}")

if __name__ == "__main__":
    iniciar_agente()