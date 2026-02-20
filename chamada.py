import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import unicodedata
from urllib.parse import quote

# 1. Configuração e Conexão
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="wide")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Estilização para fotos grandes e cards
st.markdown("""
    <style>
        .aluno-card {
            border: 1px solid #ddd; padding: 10px; border-radius: 15px;
            background-color: #fcfcfc; text-align: center; margin-bottom: 15px;
        }
        .stCheckbox { font-size: 18px; font-weight: bold; }
        img { border-radius: 10px; border: 2px solid #ff4b4b; }
    </style>
""", unsafe_allow_html=True)

# --- 2. MAPA DE MÁSCARA (AQUI ESTÁ A SEGURANÇA) ---
# O aluno só vê o código do QR Code. Ele não sabe qual código pertence a qual turma.
MAPA_TURMAS = {
    "9f1a": "1A", "2b3c": "1B", "x7y8": "2A", "k4m2": "3A",
    "m5n6": "1C", "p7q8": "2C", "r9s0": "3C" # Adicione todos os seus códigos aqui
}

# 3. Pega o Token pela URL (ex: ?t=9f1a)
params = st.query_params
token_url = params.get("t", None)

def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto).split(".")[0])
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").strip()

if token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📝 Chamada: {turma_real}")
    
    # 4. Busca alunos da turma
    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error("Erro ao carregar alunos."); st.stop()

    if not alunos:
        st.warning("Nenhuma lista encontrada para esta turma.")
    else:
        with st.form("form_chamada", clear_on_submit=False):
            fuso = pytz.timezone('America/Recife')
            data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
            st.write(f"📅 **Data:** {datetime.now(fuso).strftime('%d/%m/%Y')}")
            
            presencas = {}
            
            # 5. LAYOUT DE FOTOS GRANDES (1 por linha ou 2 colunas largas)
            # Use columns(2) para que no celular a foto fique bem grande
            cols = st.columns(2)
            
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    st.markdown('<div class="aluno-card">', unsafe_allow_html=True)
                    
                    # Lógica da Foto
                    nome_limpo = limpar_texto(aluno['nome'])
                    url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_limpo)}.jpg"
                    
                    # Mostra a foto grande
                    st.image(url_foto, use_container_width=True)
                    
                    # Checkbox de presença (Começa marcado = Presente)
                    presencas[aluno['nome']] = st.checkbox("Presente", value=True, key=f"check_{i}")
                    st.write(f"**{aluno['nome'].split()[0]}**") # Mostra apenas o primeiro nome para ser rápido
                    
                    st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            enviar = st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True)
            
            if enviar:
                dados_enviar = []
                for nome, presente in presencas.items():
                    dados_enviar.append({
                        "turma": turma_real,
                        "aluno_nome": nome,
                        "status": "P" if presente else "F",
                        "data_chamada": data_hoje
                    })
                
                try:
                    # Limpa e Insere (Evita duplicados)
                    supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                    supabase.table("frequencia").insert(dados_enviar).execute()
                    st.success("✅ Chamada enviada com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
else:
    st.error("🚫 Link Inválido ou Expirado.")
    st.info("Aponte a câmera para o QR Code oficial da sua sala.")
