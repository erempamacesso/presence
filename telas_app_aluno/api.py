import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai  # Biblioteca nova oficial
from dotenv import load_dotenv

# 1. Carregamento e Configuração
load_dotenv()
CHAVE = os.getenv("GEMINI_API_KEY")

# Inicializa o cliente novo
client = genai.Client(api_key=CHAVE)

app = FastAPI()

# Configuração de CORS para o seu index.html funcionar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Definição do Agente com o modelo que apareceu na sua lista
ID_MODELO = "gemini-2.5-flash" 
INSTRUCAO = (
    "Você é o 'Guia Vocacional IA'. Ajude jovens a encontrar sua carreira. "
    "Seja moderno, empático e faça uma pergunta por vez. "
    "Foque em transformar interesses (como construir casas) em profissões reais."
)

# Criando a sessão de chat com a nova sintaxe
chat = client.chats.create(
    model=ID_MODELO,
    config={"system_instruction": INSTRUCAO}
)

class Msg(BaseModel):
    texto: str

@app.post("/conversar")
async def conversar(msg: Msg):
    try:
        # Na biblioteca nova, usamos apenas .send_message
        resposta = chat.send_message(msg.texto)
        return {"resposta": resposta.text}
    except Exception as e:
        print(f"Erro detalhado: {e}")
        return {"resposta": "Tive um probleminha para processar. Pode repetir?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)