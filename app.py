import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from datetime import datetime, date
from streamlit_option_menu import option_menu
from urllib.parse import quote

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO OTIMIZADA
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("ERRO CRÍTICO: Credenciais do Supabase não encontradas.")
        st.stop()
    return create_client(url, key)

supabase = init_connection()

# Configuração dos Trimestres (Mantido conforme sua regra de negócio 2026)
TRIMESTRES = {
    "1º Trimestre": (date(2026, 2, 2), date(2026, 5, 20)),
    "2º Trimestre": (date(2026, 5, 21), date(2026, 9, 11)),
    "3º Trimestre": (date(2026, 9, 12), date(2026, 12, 30))
}

# ==================================================
# 2. FUNÇÕES AUXILIARES COM CACHE
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).split(".")[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=600)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 2000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos if arq['name'] != ".emptyFolderPlaceholder"}
    except:
        return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

@st.cache_data(ttl=60)
def carregar_dados_frequencia():
    try:
        res = supabase.table("frequencia").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_chamada'] = pd.to_datetime(df['data_chamada']).dt.date
        return df
    except:
        return pd.DataFrame()

# ==================================================
# 3. SIDEBAR E NAVEGAÇÃO
# ==================================================
with st.sidebar:
    col_e, col_centro, col_d = st.columns([1, 1, 1])
    with col_centro:
        if os.path.exists("logo_erempam.png"):
            st.image("logo_erempam.png", use_container_width=True)
        else:
            st.markdown("<h1>🏫</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center; margin-top: 0;'>SIGPAM</h2>", unsafe_allow_html=True)
    
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Fotograma", "Frequência", "Reposicionar", "Cadastro", "Importação"],
        icons=["camera-fill", "clipboard-check-fill", "arrow-left-right", "person-plus-fill", "cloud-upload-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "nav-link-selected": {"background-color": "#ff4b4b"},
        }
    )

# ==================================================
# 4. CONTEÚDO DAS TELAS
# ==================================================

# --- TELA: FOTOGRAMA ---
if menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
    else:
        turma_sel = st.selectbox("📂 Selecione a Turma:", lista_turmas)
        alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
        mapa_fotos = listar_arquivos_bucket()
        
        st.divider()
        if not alunos:
            st.info("Turma vazia.")
        else:
            cols = st.columns(4)
            for idx, aluno in enumerate(alunos):
                with cols[idx % 4]:
                    with st.container(border=True):
                        chave = limpar_texto(aluno['nome'])
                        arq_real = mapa_fotos.get(chave)
                        if arq_real:
                            st.image(get_foto_url(arq_real), use_container_width=True)
                        else:
                            st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#f0f0f0; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px;'>{aluno['nome']}</p>", unsafe_allow_html=True)

# --- TELA: FREQUÊNCIA ---
elif menu_escolhido == "Frequência":
    st.title("📊 Gestão de Frequência")
    df = carregar_dados_frequencia()
    
    aba1, aba2, aba3 = st.tabs(["📅 Visão Diária", "🚨 Busca Ativa", "👤 Histórico"])

    with aba1:
        data_sel = st.date_input("Data de Análise:", value=date.today())
        df_hoje = df[df['data_chamada'] == data_sel] if not df.empty else pd.DataFrame()
        
        if not df_hoje.empty:
            p = len(df_hoje[df_hoje['status'] == 'P'])
            f = len(df_hoje[df_hoje['status'] == 'F'])
            c1, c2, c3 = st.columns(3)
            c1.metric("Presentes", p)
            c2.metric("Faltosos", f, delta_color="inverse")
            c3.metric("% Adesão", f"{int(p/(p+f)*100)}%" if (p+f)>0 else "0%")
            st.dataframe(df_hoje[['turma', 'aluno_nome', 'status']], use_container_width=True, hide_index=True)
        else:
            st.info("Sem lançamentos para esta data.")

    with aba2:
        escolha_trim = st.radio("Período:", list(TRIMESTRES.keys()), horizontal=True)
        ini, fim = TRIMESTRES[escolha_trim]
        if not df.empty:
            df_trim = df[(df['data_chamada'] >= ini) & (df['data_chamada'] <= fim)]
            faltas = df_trim[df_trim['status'] == 'F'].groupby(['turma', 'aluno_nome']).size().reset_index(name='Total')
            alerta = st.slider("Mínimo de faltas:", 1, 20, 5)
            st.dataframe(faltas[faltas['Total'] >= alerta].sort_values(by='Total', ascending=False), use_container_width=True)

    with aba3:
        if not df.empty:
            aluno_sel = st.selectbox("Pesquisar Aluno:", sorted(df['aluno_nome'].unique()))
            df_aluno = df[df['aluno_nome'] == aluno_sel].sort_values(by='data_chamada', ascending=False)
            st.metric("Frequência Global", f"{((len(df_aluno[df_aluno['status']=='P'])/len(df_aluno))*100):.1f}%" if not df_aluno.empty else "0%")
            st.table(df_aluno[['data_chamada', 'status']].head(10))

# --- TELA: REPOSICIONAR ---
elif menu_escolhido == "Reposicionar":
    st.title("🔄 Troca de Turma")
    res_t = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    t_origem = st.selectbox("Turma Atual:", lista_turmas)
    alunos = supabase.table("alunos").select("*").eq("turma", t_origem).order("nome").execute().data
    
    for a in alunos:
        c1, c2, c3 = st.columns([1, 3, 2])
        c2.write(a['nome'])
        nova = c3.selectbox("Mudar para:", lista_turmas, index=lista_turmas.index(a['turma']), key=a['id'])
        if nova != a['turma']:
            supabase.table("alunos").update({"turma": nova}).eq("id", a['id']).execute()
            st.success(f"{a['nome']} movido!")
            time.sleep(0.5)
            st.rerun()

# --- TELA: CADASTRO ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Novo Aluno")
    with st.form("cad_form"):
        n = st.text_input("Nome Completo")
        t = st.text_input("Turma (ex: 1º A)")
        if st.form_submit_button("Salvar"):
            if n and t:
                supabase.table("alunos").insert({"nome": n.upper().strip(), "turma": t.upper().strip()}).execute()
                st.success("Cadastrado com sucesso!")

# --- TELA: IMPORTAÇÃO ---
elif menu_escolhido == "Importação":
    st.title("📤 Importação em Massa")
    arq = st.file_uploader("Excel ou CSV", type=['xlsx', 'csv'])
    if arq and st.button("Processar"):
        df_imp = pd.read_excel(arq) if arq.name.endswith('xlsx') else pd.read_csv(arq)
        df_imp.columns = [c.lower().strip() for c in df_imp.columns]
        for _, row in df_imp.iterrows():
            try:
                supabase.table("alunos").insert({"nome": str(row['nome']).upper().strip(), "turma": str(row['turma']).upper().strip()}).execute()
            except: pass
        st.success("Importação concluída!")
