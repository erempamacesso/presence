import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components
from urllib.parse import quote

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
    """
    Padronização ROBUSTA (Igual ao Upload Web).
    Remove acentos, espaços, underlines e traços.
    """
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    
    # Remove tudo que não for letra/número para garantir o match
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

def listar_arquivos_bucket():
    """
    Cria um MAPA (Dicionário) de fotos.
    Busca até 5000 arquivos para não faltar foto.
    """
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq.get('name') if isinstance(arq, dict) else getattr(arq, 'name', '')
                
                if not nome_real or nome_real == ".emptyFolderPlaceholder": continue
                
                # Cria a chave limpa para busca
                chave = limpar_texto(nome_real)
                # Guarda o nome real para o link
                mapa[chave] = nome_real
        return mapa
    except Exception as e: 
        return {}

def get_foto_url(nome_real_arquivo):
    try:
        # Usa quote para garantir que espaços no nome do arquivo não quebrem o link
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR E LÓGICA DE MENU
# ==================================================

if 'menu_atual' not in st.session_state:
    st.session_state['menu_atual'] = "Fotograma"

with st.sidebar:
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

if st.session_state['menu_atual'] != menu_escolhido:
    st.session_state['menu_atual'] = menu_escolhido
    js = """
    <script>
        var sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            var closeBtn = window.parent.document.querySelector('[data-testid="stSidebar"] button');
            if (closeBtn) { closeBtn.click(); }
        }
    </script>
    """
    components.html(js, height=0, width=0)
    st.rerun()

# ==================================================
# 4. CONTEÚDO DAS TELAS
# ==================================================

# --------------------------------------------------
# TELA 1: FOTOGRAMA
# --------------------------------------------------
if menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
        st.stop()

    turma_selecionada = st.selectbox("📂 Selecione a Turma:", lista_turmas)

    # Busca alunos
    data_alunos = supabase.table("alunos").select("*").eq("turma", turma_selecionada).execute().data
    
    # --- CORREÇÃO DE ORDEM (FORÇA PYTHON A ORDENAR) ---
    if data_alunos:
        data_alunos.sort(key=lambda x: x['nome']) # Garante A-Z no celular

    # Busca Mapa de Fotos
    mapa_fotos = listar_arquivos_bucket()

    st.markdown("---")
    
    if not data_alunos:
        st.info("Turma vazia.")
    else:
        colunas_por_linha = 4
        cols = st.columns(colunas_por_linha)
        
        for index, aluno in enumerate(data_alunos):
            col_atual = cols[index % colunas_por_linha]
            with col_atual:
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

    col_filtro, _ = st.columns([1, 2])
    with col_filtro:
        turma_origem = st.selectbox("Filtrar Turma Atual:", lista_turmas)
    
    # Busca alunos
    data_alunos = supabase.table("alunos").select("*").eq("turma", turma_origem).execute().data
    
    # --- CORREÇÃO DE ORDEM ---
    if data_alunos:
        data_alunos.sort(key=lambda x: x['nome']) # Garante A-Z no celular

    mapa_fotos = listar_arquivos_bucket()

    st.divider()

    c1, c2, c3 = st.columns([1, 4, 3])
    c1.markdown("**Foto**")
    c2.markdown("**Nome**")
    c3.markdown("**Nova Turma**")

    for aluno in data_alunos:
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
