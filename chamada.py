import streamlit as st
from supabase import create_client, Client
import os
from datetime import datetime, time as dt_time
import pytz
import unicodedata
import time
from urllib.parse import quote

# ==========================================
# 1. CONFIGURAÇÃO, CONEXÃO E CSS
# ==========================================
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="centered")

# CONEXÃO CORRIGIDA COM OS NOMES DO SEU SECRETS
try:
    # Usando os nomes exatos que você enviou no secrets.toml
    SUPABASE_URL = st.secrets["SUPABASE_URL_ALUNOS"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY_ALUNOS"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError as e:
    st.error(f"🚨 Erro: A chave {e} não foi encontrada no Secrets do Streamlit.")
    st.stop()
except Exception as e:
    st.error(f"🚨 Erro de conexão: {e}")
    st.stop()

# --- ESTILIZAÇÃO CSS ---
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
        .nome-aluno { font-weight: bold; font-size: 14px; color: #333; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto).strip().lower()
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join(filter(str.isalnum, sem_acento))

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        for arq in arquivos:
            nome_original = arq.get('name')
            if nome_original:
                nome_sem_ext = nome_original.rsplit('.', 1)[0] if '.' in nome_original else nome_original
                mapa[limpar_texto_absoluto(nome_sem_ext)] = nome_original
        return mapa
    except: return {}

def descobrir_aula_atual(hora_agora):
    if hora_agora < dt_time(7, 30): return "Pré-aula"
    elif hora_agora < dt_time(8, 20): return "1º Aula"
    elif hora_agora < dt_time(9, 10): return "2º Aula"
    elif hora_agora < dt_time(9, 30): return "Intervalo (Manhã)"
    elif hora_agora < dt_time(10, 20): return "3º Aula"
    elif hora_agora < dt_time(11, 10): return "4º Aula"
    elif hora_agora < dt_time(12, 00): return "5º Aula"
    elif hora_agora < dt_time(13, 20): return "Intervalo (Almoço)"
    elif hora_agora < dt_time(14, 10): return "6º Aula"
    elif hora_agora < dt_time(15, 00): return "7º Aula"
    elif hora_agora < dt_time(15, 20): return "Intervalo (Tarde)"
    elif hora_agora < dt_time(16, 00): return "8º Aula"
    elif hora_agora < dt_time(16, 40): return "9º Aula"
    else: return "Encerrado"

# ==========================================
# 3. LOGICA PRINCIPAL
# ==========================================
token_url = st.query_params.get("t", None)
if isinstance(token_url, list): token_url = token_url[0]

if token_url and token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📱 Painel: {turma_real}")
    
    mapa_fotos = listar_arquivos_bucket()
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    data_hoje = agora.strftime('%Y-%m-%d')
    hora_atual = agora.time()
    
    # BUSCA DE ALUNOS - TABELA CORRIGIDA PARA 'alunos'
    try:
        # Usando a tabela 'alunos' que existe no banco ykbw... (ChamadaEscolar)
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error(f"Erro ao carregar tabela 'alunos': {e}")
        st.stop()

    if alunos:
        tab1, tab2 = st.tabs(["📝 Chamada Manhã", "🏃 Registro de Evasão"])
        cache_buster = int(time.time())

        with tab1:
            presencas_salvas = {}
            try:
                res_chamada = supabase.table("frequencia").select("aluno_nome, status").eq("turma", turma_real).eq("data_chamada", data_hoje).execute()
                if res_chamada.data:
                    presencas_salvas = {r['aluno_nome']: r['status'] for r in res_chamada.data}
            except: pass

            with st.form("form_chamada"):
                presencas = {}
                for i, aluno in enumerate(alunos):
                    col_foto, col_nome, col_check = st.columns([1, 3, 2])
                    nome_limpo = limpar_texto_absoluto(aluno['nome'])
                    nome_arq = mapa_fotos.get(nome_limpo)
                    
                    with col_foto:
                        url_img = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cache_buster}" if nome_arq else "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
                        st.image(url_img, width=60)
                    
                    with col_nome:
                        st.markdown(f"<div style='padding-top:15px'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                    
                    with col_check:
                        marcado = False if presencas_salvas.get(aluno['nome']) == "F" else True
                        presencas[aluno['nome']] = st.checkbox("Presente", value=marcado, key=f"c_{i}")

                if st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True):
                    dados = [{"turma": turma_real, "aluno_nome": n, "status": "P" if p else "F", "data_chamada": data_hoje} for n, p in presencas.items()]
                    try:
                        supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                        supabase.table("frequencia").insert(dados).execute()
                        st.success("Chamada salva!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Erro ao salvar: {e}")

        with tab2:
            aula_sug = descobrir_aula_atual(hora_atual)
            lista_aulas = ["1º Aula", "2º Aula", "3º Aula", "4º Aula", "5º Aula", "6º Aula", "7º Aula", "8º Aula", "9º Aula"]
            idx_aula = lista_aulas.index(aula_sug) if aula_sug in lista_aulas else 0
            aula_sel = st.selectbox("Selecione a Aula:", lista_aulas, index=idx_aula)
            
            try:
                res_ev = supabase.table("evasoes").select("aluno_nome").eq("data_registro", data_hoje).eq("aula_periodo", aula_sel).eq("turma", turma_real).execute()
                fugoes = [r['aluno_nome'] for r in res_ev.data] if res_ev.data else []
            except: fugoes = []

            for i, aluno in enumerate(alunos):
                c1, c2, c3 = st.columns([1, 3, 2])
                with c1: st.write("") # Espaço para foto se quiser repetir a lógica
                with c2: st.markdown(f"<div style='padding-top:10px'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                with c3:
                    if aluno['nome'] in fugoes:
                        st.error("🚨 Ausente")
                    else:
                        if st.button("🏃 Registrar", key=f"fuga_{i}", use_container_width=True):
                            try:
                                supabase.table("evasoes").insert({"data_registro": data_hoje, "turma": turma_real, "aluno_nome": aluno['nome'], "aula_periodo": aula_sel}).execute()
                                st.toast(f"Registrado: {aluno['nome']}")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
    else:
        st.info(f"Nenhum aluno em {turma_real}.")
else:
    st.error("🚫 Use o QR Code da sala.")