import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import unicodedata
import time
from urllib.parse import quote

# 1. Configuração e Conexão
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="centered")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ESTILIZAÇÃO PARA LISTA HORIZONTAL ---
st.markdown("""
    <style>
        .aluno-row {
            display: flex;
            align-items: center;
            background-color: white;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #eee;
            margin-bottom: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .foto-container {
            flex: 0 0 60px;
            margin-right: 15px;
        }
        .foto-container img {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #ff4b4b;
        }
        .info-container {
            flex-grow: 1;
        }
        .nome-aluno {
            font-weight: bold;
            font-size: 14px;
            color: #333;
            text-transform: uppercase;
        }
        /* Ajuste para o Checkbox parecer um botão */
        .stCheckbox {
            background-color: #e8f5e9;
            padding: 5px 10px;
            border-radius: 8px;
            border: 1px solid #2e7d32;
        }
    </style>
""", unsafe_allow_html=True)

MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto_absoluto(arq.get('name')): arq.get('name') for arq in arquivos if arq.get('name')}
    except: return {}

# ==========================================
# 2. CAPTURA DO LINK (BLINDADA)
# ==========================================
token_url = None

try:
    if "t" in st.query_params:
        raw_token = st.query_params["t"]
        if isinstance(raw_token, list):
            token_url = str(raw_token[0]).lower().strip()
        else:
            token_url = str(raw_token).lower().strip()
except Exception as e:
    try:
        params = st.experimental_get_query_params()
        if "t" in params:
            token_url = str(params["t"][0]).lower().strip()
    except:
        pass

# ==========================================
# 3. LÓGICA DA CHAMADA
# ==========================================
if token_url and token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📝 Chamada: {turma_real}")
    
    mapa_fotos = listar_arquivos_bucket()
    
    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except:
        st.error("Erro no banco."); st.stop()

    if alunos:
        # Pega a data de hoje baseada no fuso de Recife
        fuso = pytz.timezone('America/Recife')
        data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
        st.caption(f"📅 Data: {datetime.now(fuso).strftime('%d/%m/%Y')}")

        # ====================================================================
        # NOVO: BUSCA SE JÁ EXISTE CHAMADA FEITA HOJE PARA ESTA TURMA
        # ====================================================================
        presencas_salvas = {}
        try:
            res_chamada_hoje = supabase.table("frequencia").select("aluno_nome, status").eq("turma", turma_real).eq("data_chamada", data_hoje).execute()
            if res_chamada_hoje.data:
                # Cria um dicionário rápido: {'João': 'P', 'Maria': 'F'}
                presencas_salvas = {registro['aluno_nome']: registro['status'] for registro in res_chamada_hoje.data}
        except Exception as e:
            pass # Se der erro, segue o jogo como se fosse a primeira chamada
        # ====================================================================

        with st.form("form_chamada"):
            presencas = {}
            cache_buster = int(time.time())
            
            for i, aluno in enumerate(alunos):
                col_foto, col_nome, col_check = st.columns([1, 3, 2])
                
                chave_aluno = limpar_texto_absoluto(aluno['nome'])
                nome_arq = mapa_fotos.get(chave_aluno)
                
                with col_foto:
                    if nome_arq:
                        url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cache_buster}"
                        st.image(url_foto, width=60)
                    else:
                        st.image("https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png", width=60)
                
                with col_nome:
                    st.markdown(f"<div style='padding-top:15px'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                
                with col_check:
                    st.write("") # Espaçador
                    
                    # --- LÓGICA DE MANTER O BOTÃO COMO ESTAVA ---
                    status_atual = presencas_salvas.get(aluno['nome'])
                    if status_atual == "F":
                        marcado = False  # Se tomou falta antes, aparece desmarcado
                    else:
                        marcado = True   # Se tomou presença (ou se é a primeira chamada do dia), aparece marcado
                    
                    presencas[aluno['nome']] = st.checkbox("Presente", value=marcado, key=f"c_{i}")

            st.markdown("---")
            if st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True):
                dados = [{"turma": turma_real, "aluno_nome": n, "status": "P" if p else "F", "data_chamada": data_hoje} for n, p in presencas.items()]
                try:
                    supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                    supabase.table("frequencia").insert(dados).execute()
                    st.success("Chamada salva/atualizada com sucesso!")
                    st.balloons()
                except Exception as e: st.error(f"Erro: {e}")
    else:
        st.info(f"Nenhum aluno encontrado na turma {turma_real} no banco de dados.")
else:
    st.error("🚫 Use o QR Code da sala.")
    if token_url:
        st.warning(f"⚠️ Link não reconhecido: '{token_url}'")
