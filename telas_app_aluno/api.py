import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PROMPT DE ENTREVISTA RÁPIDA ---
SISTEMA_VOCACIONAL = (
    "Você é o MarIO, um orientador vocacional ultra objetivo e técnico. "
    "\n\nREGRAS DE CONDUTA:"
    "\n1. SEJA DIRETO: Assim que souber o nome, faça perguntas curtas (uma por vez)."
    "\n2. NÃO DÊ DIAGNÓSTICOS PRECOCES: Não sugira nada até chegar na 10ª pergunta."
    "\n3. FOCO EM AUTOCONHECIMENTO: Pergunte sobre rotina, habilidades, medos e paixões."
    "\n4. LIMITE: A entrevista deve ter exatamente 10 perguntas."
    "\n5. DIAGNÓSTICO FINAL: Somente na última resposta, apresente 3 áreas distintas. "
    "Use uma estrutura clara: 'Baseado no seu perfil, avalie estas áreas: 1, 2 e 3'. "
    "Encerre dizendo que a decisão final é exclusivamente do aluno."
)

historico = [{"role": "system", "content": SISTEMA_VOCACIONAL}]

class Mensagem(BaseModel):
    texto: str

@app.post("/conversar")
async def conversar(msg: Mensagem):
    # Contador de interação para forçar o fim
    interacoes = len([m for m in historico if m['role'] == 'user'])
    
    if len(historico) == 1:
        # Primeiro contato: recebe o nome e já dispara a pergunta 1
        comando_inicial = f"Meu nome é {msg.texto}. Comece a entrevista. Pergunte apenas a questão 1 de 10."
        historico.append({"role": "user", "content": comando_inicial})
    else:
        # Próximas perguntas
        contexto_pergunta = f"Resposta do aluno: {msg.texto}. (Estamos na pergunta {interacoes} de 10)."
        historico.append({"role": "user", "content": contexto_pergunta})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=historico,
            temperature=0.4, # Menos criativo, mais direto
        )
        
        resposta_ia = completion.choices[0].message.content
        historico.append({"role": "assistant", "content": resposta_ia})
        
        return {"resposta": resposta_ia}
    
    except Exception as e:
        print(f"Erro: {e}")
        return {"resposta": "Ops, tive um soluço técnico. Pode repetir?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)