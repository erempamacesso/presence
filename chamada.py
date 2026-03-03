import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, time as dt_time
import pytz
import unicodedata
import time
from urllib.parse import quote

# =========================================================
# 1. CONFIGURAÇÕES INICIAIS E CONEXÃO
# =========================================================
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="centered")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# 2. ESTILIZAÇÃO (CSS)
# =========================================================
st.markdown("""
    <style>
        .stCheckbox { background-color: #e8f5e9; padding: 5px 10px; border-radius: 8px; border: 1px solid #2e7d32; }
        .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 3. FUNÇÕES DE APOIO (HORÁRIOS, TEXTO E BUCKET)
# =========================================================
MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

def limpar_texto_absoluto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").replace("_", "").strip()

def descobrir_aula_atual(hora_agora):
    """Retorna a aula atual baseada na grade horária oficial"""
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

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None)
        return {limpar_texto_absoluto(arq['name']): arq['name'] for arq in arquivos if arq.get('name')}
    except: return {}

# =========================================================
# 4. CONTROLE DE TOKEN E SEGURANÇA (TRAVA 17H)
# =========================================================
token_url = st.query_params.get("t", "").lower().strip()

if token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    data_hoje = agora.strftime('%Y-%m-%d')
    hora_atual = agora.time()

    st.title(f"📱 Painel: {turma_real}")
    
    # --- TRAVA DE SEGURANÇA 17:00 ---
    if hora_atual >= dt_time(23, 0):
        st.error("🔒 **Sistema Bloqueado.** O registro de presença e evasão só é permitido até as 17:00.")
        st.stop()

    st.caption(f"📅 {agora.strftime('%d/%m/%Y')} | ⏰ {agora.strftime('%H:%M')}")

    # Busca lista de alunos e fotos
    alunos = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute().data
    mapa_fotos = listar_arquivos_bucket()

if alunos:
        tab1, tab2 = st.tabs(["📝 Chamada Manhã", "🏃 Registro de Evasão"])
        mapa_fotos = listar_arquivos_bucket()
        cb = int(time.time()) # Cache buster

        # ---------------------------------------------------------
        # BLOCO ABA 1: CHAMADA MATINAL
        # ---------------------------------------------------------
        with tab1:
            st.write("Registre quem chegou na escola hoje:")
            res_freq = supabase.table("frequencia").select("aluno_nome, status").eq("turma", turma_real).eq("data_chamada", data_hoje).execute()
            pres_salvas = {r['aluno_nome']: r['status'] for r in res_freq.data} if res_freq.data else {}
            
            with st.form("form_chamada"):
                presencas = {}
                for i, aluno in enumerate(alunos):
                    c1, c2, c3 = st.columns([1, 3, 2])
                    
                    # --- LÓGICA DE FOTO APERFEIÇOADA ---
                    nome_completo_limpo = limpar_texto_absoluto(aluno['nome'])
                    primeiro_nome_limpo = limpar_texto_absoluto(aluno['nome'].split()[0])
                    
                    # Tenta nome completo, se não der, tenta só o primeiro nome
                    nome_arq = mapa_fotos.get(nome_completo_limpo) or mapa_fotos.get(primeiro_nome_limpo)
                    
                    with c1:
                        if nome_arq:
                            url = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cb}"
                        else:
                            url = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
                        st.image(url, width=55)
                    
                    with c2: 
                        st.markdown(f"<p style='margin-top:15px; font-size:14px;'><b>{aluno['nome']}</b></p>", unsafe_allow_html=True)
                    
                    with c3:
                        marcado = pres_salvas.get(aluno['nome']) != "F"
                        presencas[aluno['nome']] = st.checkbox("Presente", value=marcado, key=f"p_{i}")
                
                if st.form_submit_button("🚀 SALVAR CHAMADA", use_container_width=True):
                    dados = [{"turma": turma_real, "aluno_nome": n, "status": "P" if p else "F", "data_chamada": data_hoje} for n, p in presencas.items()]
                    supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                    supabase.table("frequencia").insert(dados).execute()
                    st.success("Salvo!")
                    st.rerun()

        # ---------------------------------------------------------
        # BLOCO ABA 2: REGISTRO DE EVASÃO
        # ---------------------------------------------------------
        with tab2:
            st.subheader("🕵️ Alunos fora de sala")
            aula_sug = descobrir_aula_atual(hora_atual)
            lista_aulas = ["1º Aula", "2º Aula", "3º Aula", "4º Aula", "5º Aula", "6º Aula", "7º Aula", "8º Aula", "9º Aula"]
            idx_aula = lista_aulas.index(aula_sug) if aula_sug in lista_aulas else 0
            aula_sel = st.selectbox("Aula em ocorrência:", lista_aulas, index=idx_aula)
            
            fugoes = [r['aluno_nome'] for r in supabase.table("evasoes").select("aluno_nome").eq("data_registro", data_hoje).eq("aula_periodo", aula_sel).eq("turma", turma_real).execute().data]

            for i, aluno in enumerate(alunos):
                c1, c2, c3 = st.columns([1, 3, 2])
                
                # Mesma lógica de foto da Aba 1
                nome_limpo = limpar_texto_absoluto(aluno['nome'])
                prim_limpo = limpar_texto_absoluto(aluno['nome'].split()[0])
                nome_arq = mapa_fotos.get(nome_limpo) or mapa_fotos.get(prim_limpo)
                
                with c1: 
                    url = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cb}" if nome_arq else "https://cdn-icons-png.flaticon.com/512/149/149071.png"
                    st.image(url, width=50)
                
                with c2: st.markdown(f"<p style='margin-top:10px;'><b>{aluno['nome']}</b></p>", unsafe_allow_html=True)
                
                with c3:
                    if aluno['nome'] in fugoes:
                        st.error("🚨 Ausente")
                    else:
                        if st.button("🏃 Registrar", key=f"f_{i}", use_container_width=True):
                            supabase.table("evasoes").insert({"data_registro": data_hoje, "turma": turma_real, "aluno_nome": aluno['nome'], "aula_periodo": aula_sel}).execute()
                            st.toast("Registrado!")
                            time.sleep(0.5)
                            st.rerun()
       
       
else:
    st.error("🚫 Link inválido. Por favor, utilize o QR Code da sua sala.")


