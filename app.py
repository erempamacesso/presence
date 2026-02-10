import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Carrega variáveis
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO CRÍTICO: Credenciais do Supabase não encontradas.")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro ao conectar no Supabase: {e}")
    st.stop()

# ==================================================
# 2. FUNÇÕES AUXILIARES
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list()
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq['name']
                if nome_real == ".emptyFolderPlaceholder": continue
                chave = limpar_texto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except: return {}

def get_foto_url(nome_real_arquivo):
    try:
        url = supabase.storage.from_('fotos-alunos').get_public_url(nome_real_arquivo)
        return f"{url}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR E MENU
# ==================================================

if 'menu_atual' not in st.session_state:
    st.session_state['menu_atual'] = "Fotograma"

with st.sidebar:
    # --- LOGO SIDEBAR ---
    col_e, col_centro, col_d = st.columns([1, 1, 1])
    with col_centro:
        if os.path.exists("logo_erempam.png"):
            st.image("logo_erempam.png", use_container_width=True)
        else:
            st.markdown("<h1>🏫</h1>", unsafe_allow_html=True)
    
    st.markdown(
        """<div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin:0; font-size: 24px; color: #333;'>SIGPAM</h2>
            <p style='margin:0; font-size: 12px; color: #888;'>Gestão Escolar Inteligente</p>
        </div>""", 
        unsafe_allow_html=True
    )
    
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Fotograma", "Reposicionar Estudante", "Cadastro", "Importação"],
        icons=["camera-fill", "arrow-left-right", "person-plus-fill", "cloud-upload-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#ff4b4b"},
        }
    )

# --- AUTO-FECHAMENTO DA SIDEBAR ---
if st.session_state['menu_atual'] != menu_escolhido:
    st.session_state['menu_atual'] = menu_escolhido
    components.html("""
        <script>
            setTimeout(function(){
                const sidebarButton = window.parent.document.querySelector('[data-testid="stSidebar"] button');
                if(sidebarButton){ sidebarButton.click(); }
            }, 300); 
        </script>
    """, height=0, width=0)

# ==================================================
# 4. CONTEÚDO DAS TELAS
# ==================================================

# --------------------------------------------------
# TELA 1: FOTOGRAMA (COM CORREÇÃO DE ORDEM)
# --------------------------------------------------
if menu_escolhido == "Fotograma":
    
    # --- CABEÇALHO CENTRALIZADO ---
    # Colunas [3, 2, 3] forçam a coluna do meio a ser estreita e no centro.
    # use_container_width=True faz a imagem preencher essa coluna estreita.
    c1, c2, c3 = st.columns([3, 2, 3]) 
    with c2:
        if os.path.exists("logo_erempam.png"):
            st.image("logo_erempam.png", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align:center'>🏫</h1>", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center; margin-top: -10px;'>FOTOGRAMA</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
        st.stop()

    turma_selecionada = st.selectbox("📂 Selecione a Turma:", lista_turmas)
    
    # Busca alunos ordenados por nome
    alunos = supabase.table("alunos").select("*").eq("turma", turma_selecionada).order("nome").execute().data
    mapa_fotos = listar_arquivos_bucket()

    st.markdown("---")
    
    if not alunos:
        st.info("Turma vazia.")
    else:
        # --- FIX PARA ORDEM NO MOBILE ---
        # Processamos em lotes de 4. 
        # Isso garante que a linha 1 seja preenchida (Alunos 1,2,3,4) antes de criar a linha 2.
        # No celular, ele mostra o lote 1, depois o lote 2, mantendo a ordem.
        
        qtde_por_linha = 4
        
        for i in range(0, len(alunos), qtde_por_linha):
            # Pega um grupo de 4 alunos
            grupo = alunos[i : i + qtde_por_linha]
            
            # Cria 4 colunas para esse grupo
            cols = st.columns(qtde_por_linha)
            
            for index, aluno in enumerate(grupo):
                with cols[index]:
                    with st.container(border=True):
                        chave = limpar_texto(aluno['nome'])
                        arq_real = mapa_fotos.get(chave)
                        
                        if arq_real:
                            st.image(get_foto_url(arq_real), use_container_width=True)
                        else:
                            st.markdown("<div style='height:80px; display:flex; align-items:center; justify-content:center; background:#f0f0f0; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-top:5px;'>{aluno['nome']}</p>", unsafe_allow_html=True)

# --------------------------------------------------
# TELA 2: REPOSICIONAR ESTUDANTE
# --------------------------------------------------
elif menu_escolhido == "Reposicionar Estudante":
    st.title("🔄 Reposicionar Estudante")
    
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    turma_origem = st.selectbox("Filtrar Turma Atual:", lista_turmas)
    alunos = supabase.table("alunos").select("*").eq("turma", turma_origem).order("nome").execute().data
    mapa_fotos = listar_arquivos_bucket()

    st.divider()

    c1, c2, c3 = st.columns([1, 4, 3])
    c1.markdown("**Foto**")
    c2.markdown("**Nome**")
    c3.markdown("**Nova Turma**")

    for aluno in alunos:
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 3])
            with col1:
                chave = limpar_texto(aluno['nome'])
                arq = mapa_fotos.get(chave)
                if arq: st.image(get_foto_url(arq), width=40)
                else: st.markdown("👤")
            with col2:
                st.markdown(f"<span style='font-size:14px'>{aluno['nome']}</span>", unsafe_allow_html=True)
            with col3:
                try: idx = lista_turmas.index(aluno['turma'])
                except: idx = 0
                nova = st.selectbox("Mudar", lista_turmas, index=idx, key=f"r_{aluno['id']}", label_visibility="collapsed")
                if nova != aluno['turma']:
                    supabase.table("alunos").update({"turma": nova}).eq("id", aluno['id']).execute()
                    st.toast(f"✅ Movido para {nova}")
                    time.sleep(0.5)
                    st.rerun()
            st.markdown("---")

# --------------------------------------------------
# TELA 3: CADASTRO
# --------------------------------------------------
elif menu_escolhido == "Cadastro":
    st.title("👤 Novo Aluno")
    with st.container(border=True):
        with st.form("form_cad"):
            st.write("Dados do Estudante")
            nome = st.text_input("Nome Completo")
            turma = st.text_input("Turma (Ex: 1º A)")
            if st.form_submit_button("💾 Salvar Cadastro", use_container_width=True):
                if nome and turma:
                    supabase.table("alunos").insert({"nome": nome.upper().strip(), "turma": turma.upper().strip()}).execute()
                    st.success("Aluno salvo com sucesso!")

# --------------------------------------------------
# TELA 4: IMPORTAÇÃO
# --------------------------------------------------
elif menu_escolhido == "Importação":
    st.title("📤 Importação em Massa")
    st.info("Suporta arquivos Excel (.xlsx) ou CSV.")
    
    arquivo = st.file_uploader("Arraste o arquivo aqui", type=["csv", "xlsx"])
    if arquivo and st.button("🚀 Processar Arquivo", use_container_width=True):
        if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo)
        else: df = pd.read_excel(arquivo)
        
        df.columns = [str(c).lower().strip() for c in df.columns]
        count = 0
        bar = st.progress(0)
        
        for i, row in df.iterrows():
            bar.progress((i+1)/len(df))
            try:
                nome = str(row['nome']).upper().strip()
                t = row.get('turma', 'SEM TURMA')
                if 'serie' in df.columns: t = f"{row['serie']} {t}"
                
                check = supabase.table("alunos").select("id").eq("nome", nome).execute()
                if not check.data:
                    supabase.table("alunos").insert({"nome": nome, "turma": str(t).strip()}).execute()
                    count += 1
            except: pass
        st.success(f"Sucesso! {count} alunos importados.")
        time.sleep(2)
        st.rerun()
