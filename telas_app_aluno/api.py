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

# --- PROMPT REESTRUTURADO (ABORDAGEM PSICOLÓGICA) ---
SISTEMA_VOCACIONAL = (
    "Você é um Psicólogo de Orientação Vocacional com vasta experiência em autoconhecimento. "
    "Sua abordagem é intimista, empática e focada no protagonismo do aluno. "
    "\n\nFLUXO DA ENTREVISTA:"
    "\n1. IDENTIFICAÇÃO: Se não sabe o nome, pergunte carinhosamente: 'Oi! Como posso te chamar?'."
    "\n2. INTRODUÇÃO: Assim que souber o nome, diga: 'Oi [nome], vou te guiar nesta jornada de descoberta. "
    "Farei o meu máximo para que você tenha o melhor resultado e clareza sobre seu futuro. "
    "Vou te fazer algumas perguntas diretas para entendermos sua essência, seus valores e o que te brilha os olhos.'."
    "\n3. MÉTODO: Após a introdução, comece a fase de perguntas de autoconhecimento (uma por vez). "
    "Ex: 'O que você passaria o dia fazendo se não precisasse se preocupar com dinheiro?'"
    "\n4. CONCLUSÃO: Após 8-10 perguntas, apresente 3 ou mais áreas de sugestão. "
    "\n5. AVISO FINAL: DEIXE CLARO que são sugestões de áreas que a pessoa precisa avaliar e que SERÁ ELA que irá decidir o caminho final."
)

historico = [{"role": "system", "content": SISTEMA_VOCACIONAL}]

class Mensagem(BaseModel):
    texto: str

@app.post("/conversar")
async def conversar(msg: Mensagem):
    historico.append({"role": "user", "content": msg.texto})
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=historico,
            temperature=0.7,
        )
        
        resposta_ia = completion.choices[0].message.content
        historico.append({"role": "assistant", "content": resposta_ia})
        
        return {"resposta": resposta_ia}
    
    except Exception as e:
        print(f"Erro: {e}")
        return {"resposta": "Tive um probleminha. Pode repetir o seu nome ou sua última resposta?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)