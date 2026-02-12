import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time
from datetime import datetime
from streamlit_option_menu import option_menu
import streamlit.components.v1 as components
from urllib.parse import quote

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO INTELIGENTE
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# A MÁGICA ACONTECE AQUI:
# 1. load_dotenv() lê o seu arquivo .env automaticamente
load_dotenv()

# 2. O código tenta pegar a senha dos Segredos do Streamlit (para quando for pra nuvem)
# 3. Se não achar, ele pega do os.getenv (que leu do seu .env local)
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

# Verificação de segurança
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO: Credenciais não encontradas. Verifique seu arquivo .env")
    st.stop()

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
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
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq.get('name') if isinstance(arq, dict) else getattr(arq, 'name', '')
                if not nome_real or nome_real == ".emptyFolderPlaceholder": continue
                chave = limpar_texto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except Exception as e: 
        return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR
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
    
    st.markdown("<h3 style='text-align: center;'>SIGPAM</h3>", unsafe_allow_html=True)
    
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Fotograma", "Frequência", "Reposicionar Estudante", "Cadastro", "Importação"],
        icons=["camera-fill", "clipboard-check-fill", "arrow-left-right", "person-plus-fill", "cloud-upload-fill"],
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "nav-link-selected": {"background-color": "#ff4b4b"},
        }
    )

if st.session_state['menu_atual'] != menu_escolhido:
    st.session_state['menu_atual'] = menu_escolhido
    st.rerun()

# ==================================================
# 4. CONTEÚDO
# ==================================================

# --- FOTOGRAMA ---
if menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []

    if not lista_turmas:
        st.warning("Nenhuma turma cadastrada.")
    else:
        turma_selecionada = st.selectbox("📂 Selecione a Turma:", lista_turmas)
        data_alunos = supabase.table("alunos").select("*").eq("turma", turma_selecionada).execute().data
        
        if data_alunos: data_alunos.sort(key=lambda x: x['nome']) 
        mapa_fotos = listar_arquivos_bucket()
        st.markdown("---")
        
        if not data_alunos:
            st.info("Turma vazia.")
        else:
            qtde_por_linha = 4
            for i in range(0, len(data_alunos), qtde_por_linha):
                batch = data_alunos[i : i + qtde_por_linha]
                cols = st.columns(qtde_por_linha)
                for idx, aluno in enumerate(batch):
                    with cols[idx]:
                        with st.container(border=True):
                            chave = limpar_texto(aluno['nome'])
                            arq_real = mapa_fotos.get(chave)
                            if arq_real:
                                st.image(get_foto_url(arq_real), use_container_width=True)
                            else:
                                st.markdown("<div style='height:80px; display:flex; align-items:center; justify-content:center; background:#f0f0f0; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                            st.markdown(f"<p style='text-align:center; font-weight:bold; font-size:12px; margin-top:5px;'>{aluno['nome']}</p>", unsafe_allow_html=True)

# --- FREQUÊNCIA ---
elif menu_escolhido == "Frequência":
    st.title("📊 Painel de Frequência")
    col_data, _ = st.columns([1, 3])
    with col_data:
        data_selecionada = st.date_input("📅 Data", value=datetime.now(), format="DD/MM/YYYY")
    
    data_str = data_selecionada.strftime('%Y-%m-%d')
    try:
        rows = supabase.table("frequencia").select("*").eq("data_chamada", data_str).execute().data
    except: rows = []
    
    st.divider()
    if not rows:
        st.info(f"Nenhuma chamada registrada para {data_selecionada.strftime('%d/%m/%Y')}.")
    else:
        df = pd.DataFrame(rows)
        total = len(df)
        presencas = len(df[df['status'] == 'P'])
        faltas = len(df[df['status'] == 'F'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", total)
        c2.metric("Presentes", presencas)
        c3.metric("Faltas", faltas, delta_color="inverse")
        
        st.markdown("### ⚠️ Ausências")
        df_faltas = df[df['status'] == 'F'][['turma', 'aluno_nome']].sort_values(['turma', 'aluno_nome'])
        if df_faltas.empty: st.success("Todos presentes!")
        else: st.dataframe(df_faltas, use_container_width=True, hide_index=True)

# --- REPOSICIONAR ---
elif menu_escolhido == "Reposicionar Estudante":
    st.title("🔄 Reposicionar")
    try:
        res = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
    except: lista_turmas = []
    
    turma_origem = st.selectbox("Turma Atual:", lista_turmas)
    data_alunos = supabase.table("alunos").select("*").eq("turma", turma_origem).execute().data
    if data_alunos: data_alunos.sort(key=lambda x: x['nome'])
    mapa_fotos = listar_arquivos_bucket()
    
    st.divider()
    for aluno in data_alunos:
        c1, c2, c3 = st.columns([1, 4, 3])
        with c1:
            chave = limpar_texto(aluno['nome'])
            if mapa_fotos.get(chave): st.image(get_foto_url(mapa_fotos.get(chave)), width=40)
            else: st.markdown("👤")
        with c2: st.write(aluno['nome'])
        with c3:
            try: idx = lista_turmas.index(aluno['turma'])
            except: idx = 0
            nova = st.selectbox("Mudar", lista_turmas, index=idx, key=f"r_{aluno['id']}", label_visibility="collapsed")
            if nova != aluno['turma']:
                supabase.table("alunos").update({"turma": nova}).eq("id", aluno['id']).execute()
                st.toast(f"Movido para {nova}")
                time.sleep(0.5)
                st.rerun()

# --- CADASTRO ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Novo Aluno")
    with st.form("form_cad"):
        nome = st.text_input("Nome")
        turma = st.text_input("Turma")
        if st.form_submit_button("Salvar"):
            supabase.table("alunos").insert({"nome": nome.upper().strip(), "turma": turma.upper().strip()}).execute()
            st.success("Salvo!")

# --- IMPORTAÇÃO ---
elif menu_escolhido == "Importação":
    st.title("📤 Importar Excel/CSV")
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
                check = supabase.table("alunos").select("id").eq("nome", nome).execute()
                if not check.data:
                    supabase.table("alunos").insert({"nome": nome, "turma": str(t).strip()}).execute()
                    count += 1
            except: pass
        st.success(f"{count} alunos importados.")
        time.sleep(2)
        st.rerun()
