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
import altair as alt

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
st.set_page_config(
    page_title="SIGPAM - EREMPAM", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Estilização CSS
st.markdown("""
    <style>
        .stSelectbox div[data-baseweb="select"] input { inputmode: none !important; }
        .espaco-reservado { padding: 12px; border-radius: 8px; background-color: #fff5f5; border-left: 6px solid #ff5252; margin-bottom: 10px; }
        .espaco-livre { padding: 12px; border-radius: 8px; background-color: #f0fdf4; border-left: 6px solid #4ade80; margin-bottom: 10px; }
        .nome-card { text-align: center; font-weight: bold; font-size: 11px; margin-top: 5px; color: #333; line-height: 1.2; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# Listas de Referência
ESPACOS_ESCOLA = ["Data show", "Auditório", "Sala de informática", "Biblioteca", "Refeitório", "Lab. de ciências", "Aparelho de som"]
LISTA_AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]

# ==================================================
# 2. FUNÇÕES AUXILIARES
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).split(".")[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 2000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos if arq['name'] != ".emptyFolderPlaceholder"}
    except: return {}

def get_foto_url(nome_real_arquivo):
    try:
        url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(nome_real_arquivo)}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR (ORDEM SOLICITADA)
# ==================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>SIGPAM</h2>", unsafe_allow_html=True)
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Frequência", "Reservas", "Fotograma", "Cadastro", "Importação"],
        icons=["clipboard-check-fill", "calendar-check-fill", "camera-fill", "person-plus-fill", "cloud-upload-fill"],
        default_index=0, # Garante que Frequência abra primeiro
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# ==================================================
# 4. TELAS
# ==================================================

# --- TELA 1: FREQUÊNCIA (RELATÓRIO DO DIA) ---
if menu_escolhido == "Frequência":
    st.title("📊 Relatório de Frequência Diária")
    hoje = date.today().isoformat()
    
    with st.spinner("Buscando dados de hoje..."):
        # 1. Busca total de alunos matriculados
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_matriculados = res_total.count
        
        # 2. Busca presenças registradas hoje pelo chamada.py na tabela 'frequencia'
        # Nota: Se sua tabela de logs de presença tiver outro nome, altere aqui.
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje).execute()
        df_presenca = pd.DataFrame(res_freq.data)

    if not df_presenca.empty:
        # Cálculos
        presentes = len(df_presenca.drop_duplicates(subset=['aluno_id'])) if 'aluno_id' in df_presenca.columns else len(df_presenca)
        faltas = total_matriculados - presentes
        perc_falta = int((faltas / total_matriculados) * 100) if total_matriculados > 0 else 0

        # Painel de Números
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matriculados", total_matriculados)
        c2.metric("Presentes Hoje", presentes, delta="Entradas")
        c3.metric("Faltas", faltas, delta_color="inverse")
        c4.metric("% de Ausência", f"{perc_falta}%")

        st.markdown("---")
        
        # Abas de visualização
        tab1, tab2 = st.tabs(["📈 Presença por Turma", "📝 Lista de Entradas"])
        
        with tab1:
            if 'turma' in df_presenca.columns:
                graf_data = df_presenca.groupby("turma").size().reset_index(name="Quantidade")
                chart = alt.Chart(graf_data).mark_bar(color='#ff4b4b').encode(
                    x=alt.X('turma:N', title="Turma"),
                    y=alt.Y('Quantidade:Q', title="Alunos Presentes"),
                    tooltip=['turma', 'Quantidade']
                ).properties(height=350).interactive()
                st.altair_chart(chart, use_container_width=True)
        
        with tab2:
            st.dataframe(df_presenca, use_container_width=True)
    else:
        st.warning(f"Nenhum registro de presença encontrado para hoje ({date.today().strftime('%d/%m/%Y')}).")
        st.info("Os dados aparecerão aqui assim que os alunos registrarem a entrada no 'chamada.py'.")

# --- TELA 2: RESERVAS (COM LIMPEZA AUTOMÁTICA) ---
elif menu_escolhido == "Reservas":
    st.title("📅 Reserva de Espaços")
    # ... (Mantido código anterior com st.pills e clear_on_submit=True)
    aba_ver, aba_nova = st.tabs(["🔍 Consultar Agenda", "📝 Nova Reserva"])
    
    with aba_ver:
        d_con = st.date_input("Ver dia:", value=date.today())
        res_r = supabase.table("reservas").select("*").eq("data_reserva", str(d_con)).execute()
        df_r = pd.DataFrame(res_r.data)
        for esp in ESPACOS_ESCOLA:
            r_l = df_r[df_r['espaco'] == esp] if not df_r.empty else pd.DataFrame()
            if not r_l.empty:
                for prof, d_p in r_l.groupby("professor"):
                    st.markdown(f"<div class='espaco-reservado'><b>🔴 {esp}</b><br>Prof: {prof} | Aulas: {', '.join(d_p['periodo'].tolist())}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='espaco-livre'><b>🟢 {esp}</b> - Disponível</div>", unsafe_allow_html=True)

    with aba_nova:
        with st.form("form_reserva", clear_on_submit=True):
            p_n = st.text_input("Nome do Professor:")
            e_s = st.selectbox("Recurso:", ESPACOS_ESCOLA)
            d_s = st.date_input("Data:", value=date.today())
            a_s = st.pills("Selecione as Aulas:", options=LISTA_AULAS, selection_mode="multi")
            if st.form_submit_button("Confirmar Reserva"):
                if p_n and a_s:
                    for a in a_s:
                        supabase.table("reservas").insert({"espaco": e_s, "professor": p_n.upper(), "data_reserva": str(d_s), "periodo": a}).execute()
                    st.success("Reserva realizada com sucesso!")
                    time.sleep(1)
                    st.rerun()

# --- TELA 3: FOTOGRAMA (CORRIGIDO) ---
elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    list_t = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    if list_t:
        t_sel = st.pills("Turma:", options=list_t, default=list_t[0])
        alunos = supabase.table("alunos").select("*").eq("turma", t_sel).order("nome").execute().data
        mapa_fotos = listar_arquivos_bucket()
        cols = st.columns(4)
        for idx, al in enumerate(alunos):
            with cols[idx % 4]:
                with st.container(border=True):
                    chave = limpar_texto(al['nome'])
                    arq = mapa_fotos.get(chave)
                    if arq: st.image(get_foto_url(arq), use_container_width=True)
                    else: st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#eee; border-radius:10px;'>👤</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='nome-card'>{al['nome']}</div>", unsafe_allow_html=True)

# --- DEMAIS TELAS ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Cadastro de Alunos")
elif menu_escolhido == "Importação":
    st.title("📤 Importação de Dados")
