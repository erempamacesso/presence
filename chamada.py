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
            min-height: 350px;
        }
        .stCheckbox { font-size: 18px; font-weight: bold; }
        img { border-radius: 10px; border: 2px solid #ff4b4b; object-fit: cover; height: 250px !important; }
        .nome-chamada { font-weight: bold; font-size: 1.1rem; color: #333; margin-top: 10px; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# --- 2. MAPA DE MÁSCARA (Dicionário de Tokens) ---
MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

# 3. Funções de Limpeza e Busca de Fotos
def limpar_texto_absoluto(texto):
    """Igual à lógica do Mapa de Sala para garantir compatibilidade"""
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=600)
def listar_arquivos_bucket():
    """Lista os nomes reais dos arquivos no storage"""
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        for arq in arquivos:
            nome_real = arq.get('name')
            if nome_real and nome_real != ".emptyFolderPlaceholder":
                chave = limpar_texto_absoluto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except:
        return {}

# 4. Lógica de Acesso
params = st.query_params
token_url = params.get("t", None)

if token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📝 Chamada: {turma_real}")
    
    # Busca arquivos no bucket para conferência
    mapa_fotos = listar_arquivos_bucket()
    
    # Busca alunos da turma
    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error("Erro ao conectar com o banco de dados."); st.stop()

    if not alunos:
        st.warning(f"Nenhuma lista encontrada para a turma '{turma_real}'.")
    else:
        with st.form("form_chamada", clear_on_submit=False):
            fuso = pytz.timezone('America/Recife')
            data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
            st.info(f"📅 **Data:** {datetime.now(fuso).strftime('%d/%m/%Y')}")
            
            presencas = {}
            cache_buster = int(time.time())
            
            cols = st.columns(2)
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    st.markdown('<div class="aluno-card">', unsafe_allow_html=True)
                    
                    # Tenta encontrar a foto no mapa gerado pelo bucket
                    chave_aluno = limpar_texto_absoluto(aluno['nome'])
                    nome_arquivo_real = mapa_fotos.get(chave_aluno)
                    
                    if nome_arquivo_real:
                        url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arquivo_real)}?t={cache_buster}"
                        st.image(url_foto, use_container_width=True)
                    else:
                        # Imagem padrão se não encontrar
                        st.image("https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png", use_container_width=True)
                    
                    st.markdown(f"<div class='nome-chamada'>{aluno['nome'].split()[0]}</div>", unsafe_allow_html=True)
                    presencas[aluno['nome']] = st.checkbox("Presente", value=True, key=f"check_{i}")
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
                    supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                    supabase.table("frequencia").insert(dados_enviar).execute()
                    st.success("✅ Chamada enviada com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
else:
    st.error("🚫 Acesso não autorizado.")
    st.info("Utilize o QR Code oficial da sua turma.")
