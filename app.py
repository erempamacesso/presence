import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Tenta carregar do arquivo .env (local) ou dos Segredos do Streamlit (nuvem)
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

# Trava de segurança
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO CRÍTICO: Credenciais do Supabase não encontradas.")
    st.stop()

# Conecta ao banco
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro ao conectar no Supabase: {e}")
    st.stop()

# ==================================================
# 2. FUNÇÕES AUXILIARES
# ==================================================
def limpar_texto(texto):
    """Padroniza textos para busca de fotos"""
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

def listar_arquivos_bucket():
    """Busca o mapa de fotos"""
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
    """Gera link público da foto"""
    try:
        url = supabase.storage.from_('fotos-alunos').get_public_url(nome_real_arquivo)
        return f"{url}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR (MENU E LOGO)
# ==================================================

# --- LOGO E TÍTULO CENTRALIZADOS ---
with st.sidebar:
    # Verifica se a logo existe no repositório antes de tentar mostrar
    if os.path.exists("logo_erempam.png"):
        c_logo1, c_logo2, c_logo3 = st.columns([1, 2, 1])
        with c_logo2:
            st.image("logo_erempam.png", use_container_width=True)
    else:
        # Se não tiver logo, mostra um ícone
        st.markdown("<h1 style='text-align: center;'>🏫</h1>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h1 style='margin:0; font-size: 32px; color: #E63946;'>SIGPAM</h1>
            <h3 style='margin:0; font-size: 14px; color: #666;'>Sistema de Gerenciamento EREMPAM</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # Menu Radio
    menu_escolhido = st.radio(
        "Navegação:",
        ("📸 Fotograma", 
         "🔄 Reposicionar", 
         "👤 Cadastro", 
         "📤 Importação")
    )

# ==================================================
# 4. LÓGICA DAS TELAS
# ==================================================

# --------------------------------------------------
# TELA 1: FOTOGRAMA
# --------------------------------------------------
if menu_escolhido == "📸 Fotograma":
    st.title("📸 Mapa de Sala (Fotograma)")
    
    # 1. Seleção de Turma
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
        st.stop()

    turma_selecionada = st.selectbox("📂 Selecione a Turma:", lista_turmas)

    # 2. Busca Alunos
    alunos = supabase.table("alunos").select("*").eq("turma", turma_selecionada).order("nome").execute().data
    mapa_fotos = listar_arquivos_bucket()

    st.markdown("---")
    
    if not alunos:
        st.info("Turma vazia.")
    else:
        # GRADE (4 por linha)
        colunas_por_linha = 4
        cols = st.columns(colunas_por_linha)
        
        for index, aluno in enumerate(alunos):
            col_atual = cols[index % colunas_por_linha]
            
            with col_atual:
                with st.container(border=True):
                    chave = limpar_texto(aluno['nome'])
                    arq_real = mapa_fotos.get(chave)
                    
                    if arq_real:
                        st.image(get_foto_url(arq_real), use_container_width=True)
                    else:
                        st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#eee;'>👤</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div style='text-align:center; font-weight:bold; font-size:14px;'>{aluno['nome']}</div>", unsafe_allow_html=True)

# --------------------------------------------------
# TELA 2: REPOSICIONAR
# --------------------------------------------------
elif menu_escolhido == "🔄 Reposicionar":
    st.title("🔄 Reposicionar Alunos")
    
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    turma_origem = st.selectbox("Filtrar Turma Atual:", lista_turmas)
    alunos = supabase.table("alunos").select("*").eq("turma", turma_origem).order("nome").execute().data
    mapa_fotos = listar_arquivos_bucket()

    st.divider()

    c1, c2, c3 = st.columns([1, 4, 3])
    c1.write("**Foto**")
    c2.write("**Nome**")
    c3.write("**Nova Turma**")

    for aluno in alunos:
        with st.container():
            col1, col2, col3 = st.columns([1, 4, 3])
            with col1:
                chave = limpar_texto(aluno['nome'])
                arq = mapa_fotos.get(chave)
                if arq: st.image(get_foto_url(arq), width=50)
                else: st.write("👤")
            with col2:
                st.write(f"**{aluno['nome']}**")
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
elif menu_escolhido == "👤 Cadastro":
    st.title("👤 Novo Aluno")
    with st.form("form_cad"):
        nome = st.text_input("Nome Completo")
        turma = st.text_input("Turma (Ex: 1º A)")
        if st.form_submit_button("Salvar"):
            if nome and turma:
                supabase.table("alunos").insert({"nome": nome.upper().strip(), "turma": turma.upper().strip()}).execute()
                st.success("Salvo!")

# --------------------------------------------------
# TELA 4: IMPORTAÇÃO
# --------------------------------------------------
elif menu_escolhido == "📤 Importação":
    st.title("📤 Importar em Massa")
    st.info("Arquivo Excel ou CSV com colunas: **Nome**, **Turma**")
    
    arquivo = st.file_uploader("Arquivo", type=["csv", "xlsx"])
    if arquivo and st.button("Processar"):
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
        st.success(f"{count} alunos importados.")
        time.sleep(2)
        st.rerun()
