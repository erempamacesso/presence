import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time

# ==================================================
# 1. CONFIGURAÇÃO E CREDENCIAIS
# ==================================================
st.set_page_config(page_title="Gestão Escolar - Cadastro", layout="wide")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO: Credenciais não encontradas.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================================================
# 2. FUNÇÕES DE APOIO E FOTOS (GITHUB)
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    # Remove extensão se houver
    if "." in str(texto):
        texto = str(texto).rsplit(".", 1)[0]
    
    nfkd = unicodedata.normalize('NFKD', str(texto))
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

@st.cache_data(ttl=3600)
def carregar_fotos_github():
    """Busca as fotos diretamente no repositório do GitHub"""
    try:
        from github import Github, Auth
        if "GITHUB_TOKEN" not in st.secrets:
            return {}
            
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception:
        return {}

# ==================================================
# 3. LÓGICA DE NAVEGAÇÃO PERSISTENTE
# ==================================================
# Criamos um estado para a aba para não resetar no rerun
if 'aba_atual' not in st.session_state:
    st.session_state.aba_atual = "📤 Importação"

def mudar_aba(nova_aba):
    st.session_state.aba_atual = nova_aba

# CSS para transformar o radio em botões que parecem abas
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    .stRadio [data-testid="stWidgetLabel"] { display: none; }
    div[data-testid="stMarkdownContainer"] hr { margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏫 Sistema de Gestão Escolar")

# Menu de navegação que substitui o st.tabs para manter o estado
opcoes_menu = ["📤 Importação", "👤 Cadastro Manual", "📸 Turmas e Fotos"]
escolha = st.radio("Navegação", opcoes_menu, index=opcoes_menu.index(st.session_state.aba_atual), 
                   horizontal=True, key="nav_main", on_change=lambda: st.session_state.update({"aba_atual": st.session_state.nav_main}))

st.divider()

# ==================================================
# 4. CONTEÚDO DAS ABAS
# ==================================================

# --- ABA 1: IMPORTAÇÃO ---
if st.session_state.aba_atual == "📤 Importação":
    st.subheader("Importar Dados")
    st.write("Importar planilha Excel ou CSV.")
    arquivo = st.file_uploader("Upload Arquivo", type=["csv", "xlsx"])
    if arquivo:
        if st.button("Processar Arquivo"):
            try:
                if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo)
                else: df = pd.read_excel(arquivo)
                df.columns = [c.lower().strip() for c in df.columns]
                count = 0
                for index, row in df.iterrows():
                    try:
                        nome = str(row['nome']).upper().strip()
                        turma = f"{row['serie']} {row['turma']}".strip()
                        existe = supabase.table("alunos").select("id").eq("nome", nome).execute()
                        if not existe.data:
                            supabase.table("alunos").insert({"nome": nome, "turma": turma}).execute()
                            count += 1
                    except: pass
                st.success(f"Processados: {count}")
            except Exception as e: st.error(f"Erro: {e}")

# --- ABA 2: CADASTRO MANUAL ---
elif st.session_state.aba_atual == "👤 Cadastro Manual":
    st.subheader("Novo Estudante")
    with st.form("form_manual", clear_on_submit=True):
        nome_man = st.text_input("Nome Completo")
        turma_man = st.text_input("Turma (Ex: 1º A)")
        if st.form_submit_button("Cadastrar"):
            if nome_man and turma_man:
                supabase.table("alunos").insert({"nome": nome_man.upper(), "turma": turma_man.upper()}).execute()
                st.success("Estudante cadastrado com sucesso!")

# --- ABA 3: GESTÃO VISUAL (FOTOS E TURMAS) ---
elif st.session_state.aba_atual == "📸 Turmas e Fotos":
    st.subheader("Gestão de Turmas")

    # 1. Carrega dados de apoio
    res = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res.data if x['turma']])))
    
    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada no banco de dados.")
    else:
        # 2. Seleção de Turma
        turma_escolhida = st.selectbox("Selecione a Turma para Visualizar:", lista_turmas)
        
        # 3. Carrega Fotos do GitHub e Alunos
        mapa_fotos = carregar_fotos_github()
        res_alunos = supabase.table("alunos").select("*").eq("turma", turma_escolhida).order("nome").execute()
        alunos = res_alunos.data

        st.markdown(f"### Alunos da Turma: {turma_escolhida}")
        
        c_h1, c_h2, c_h3 = st.columns([1, 4, 2])
        c_h1.markdown("**FOTO**")
        c_h2.markdown("**NOME DO ESTUDANTE**")
        c_h3.markdown("**MUDAR TURMA**")

        for aluno in alunos:
            st.divider()
            c1, c2, c3 = st.columns([1, 4, 2])
            uid = aluno['id']
            nome_aluno = aluno['nome']

            # --- COLUNA 1: FOTO (GITHUB) ---
            with c1:
                chave_busca = limpar_texto(nome_aluno)
                url_foto = mapa_fotos.get(chave_busca)
                if url_foto:
                    st.image(url_foto, width=60)
                else:
                    st.markdown("<div style='font-size:30px; text-align:center;'>👤</div>", unsafe_allow_html=True)

            # --- COLUNA 2: NOME ---
            with c2:
                st.write(f"**{nome_aluno}**")
                if not url_foto:
                    st.caption("⚠️ Foto pendente no GitHub")

            # --- COLUNA 3: MUDANÇA DE TURMA (SEM RESET DE ABA) ---
            with c3:
                try: 
                    idx_turma = lista_turmas.index(aluno['turma'])
                except: 
                    idx_turma = 0
                
                nova_turma = st.selectbox(
                    "Mudar", 
                    lista_turmas, 
                    index=idx_turma, 
                    key=f"change_t_{uid}", 
                    label_visibility="collapsed"
                )
                
                if nova_turma != aluno['turma']:
                    with st.spinner("Atualizando..."):
                        supabase.table("alunos").update({"turma": nova_turma}).eq("id", uid).execute()
                        st.toast(f"{nome_aluno} movido para {nova_turma}!")
                        time.sleep(1)
                        # Como st.session_state.aba_atual já é "📸 Turmas e Fotos", 
                        # o rerun agora voltará exatamente para esta tela.
                        st.rerun()