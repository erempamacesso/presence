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

# Estilização CSS personalizada
st.markdown("""
    <style>
        .stSelectbox div[data-baseweb="select"] input { inputmode: none !important; }
        .espaco-reservado {
            padding: 12px; border-radius: 8px; background-color: #fff5f5;
            border-left: 6px solid #ff5252; margin-bottom: 10px;
        }
        .espaco-livre {
            padding: 12px; border-radius: 8px; background-color: #f0fdf4;
            border-left: 6px solid #4ade80; margin-bottom: 10px;
        }
        .nome-card { 
            text-align: center; font-weight: bold; font-size: 11px; 
            margin-top: 5px; color: #333; line-height: 1.2;
        }
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
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 2000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos if arq['name'] != ".emptyFolderPlaceholder"}
    except: return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{path_seguro}"
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
        default_index=0,
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# ==================================================
# 4. TELAS
# ==================================================

# --- TELA: FREQUÊNCIA (INTEGRADA DO SEU CÓDIGO) ---
if menu_escolhido == "Frequência":
    st.title("🏫 Dashboard de Gestão Escolar")
    st.markdown("---")

    with st.spinner("Carregando dados da escola..."):
        # Busca dados reais para o Dashboard
        response = supabase.table("alunos").select("id, nome, turma, face_encoding").execute()
        alunos_db = response.data

    if alunos_db:
        df = pd.DataFrame(alunos_db)
        df['Status Biometria'] = df['face_encoding'].apply(lambda x: "✅ OK" if x else "⚠️ Pendente")
        df['tem_bio'] = df['face_encoding'].apply(lambda x: 1 if x else 0)
        
        # Filtro de Turma (dentro da tela de frequência)
        lista_turmas_freq = sorted(list(set(df["turma"].dropna().unique())))
        turma_f = st.selectbox("Filtrar Turma para Relatório:", ["Todas"] + lista_turmas_freq)
        
        df_f = df if turma_f == "Todas" else df[df["turma"] == turma_f]

        # Métricas (KPIs)
        total_al = len(df_f)
        com_bio = df_f['tem_bio'].sum()
        sem_bio = total_al - com_bio
        perc = int((com_bio / total_al * 100)) if total_al > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total de Alunos", total_al)
        c2.metric("📸 Com Biometria", com_bio, delta="Prontos")
        c3.metric("⚠️ Sem Foto", sem_bio, delta_color="inverse")
        c4.metric("Adesão", f"{perc}%")

        st.markdown("---")
        aba_lista, aba_graf = st.tabs(["📋 Lista de Alunos", "📊 Gráfico de Adesão"])
        
        with aba_lista:
            st.dataframe(df_f[["nome", "turma", "Status Biometria"]], use_container_width=True, hide_index=True)
        
        with aba_graf:
            graf_df = df.groupby("turma")["tem_bio"].agg(['count', 'sum']).reset_index()
            graf_df.columns = ["Turma", "Total", "Com Biometria"]
            graf_df["Sem Biometria"] = graf_df["Total"] - graf_df["Com Biometria"]
            graf_long = pd.melt(graf_df, id_vars=["Turma"], value_vars=["Com Biometria", "Sem Biometria"], var_name="Status", value_name="Quantidade")
            
            chart = alt.Chart(graf_long).mark_bar().encode(
                x=alt.X('Turma', sort=None),
                y='Quantidade',
                color=alt.Color('Status', scale=alt.Scale(domain=['Com Biometria', 'Sem Biometria'], range=['#2ecc71', '#e74c3c'])),
                tooltip=['Turma', 'Status', 'Quantidade']
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Nenhum aluno encontrado no banco de dados.")

# --- TELA: RESERVAS (LIMPEZA AUTOMÁTICA) ---
elif menu_escolhido == "Reservas":
    st.title("📅 Reserva de Espaços")
    aba_ver, aba_nova = st.tabs(["🔍 Consultar Agenda", "📝 Nova Reserva"])
    
    with aba_ver:
        d_con = st.date_input("Data:", value=date.today())
        res_r = supabase.table("reservas").select("*").eq("data_reserva", str(d_con)).execute()
        df_r = pd.DataFrame(res_r.data)
        
        for esp in ESPACOS_ESCOLA:
            r_local = df_r[df_r['espaco'] == esp] if not df_r.empty else pd.DataFrame()
            if not r_local.empty:
                for prof, d_p in r_local.groupby("professor"):
                    st.markdown(f"<div class='espaco-reservado'><b>🔴 {esp}</b><br>Prof: {prof} | Aulas: {', '.join(d_p['periodo'].tolist())}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='espaco-livre'><b>🟢 {esp}</b> - Livre</div>", unsafe_allow_html=True)

    with aba_nova:
        with st.form("form_res", clear_on_submit=True):
            p_n = st.text_input("Seu Nome:")
            e_s = st.selectbox("Recurso:", ESPACOS_ESCOLA)
            d_s = st.date_input("Data:", value=date.today())
            a_s = st.pills("Aulas:", options=LISTA_AULAS, selection_mode="multi")
            
            if st.form_submit_button("Confirmar Reserva"):
                if p_n and a_s:
                    for a in a_s:
                        supabase.table("reservas").insert({"espaco": e_s, "professor": p_n.upper(), "data_reserva": str(d_s), "periodo": a}).execute()
                    st.success("Reserva realizada!")
                    time.sleep(1)
                    st.rerun()

# --- TELA: FOTOGRAMA (FOTOS CORRIGIDAS) ---
elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    list_t = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    
    if list_t:
        t_sel = st.pills("Selecione a Turma:", options=list_t, default=list_t[0])
        alunos = supabase.table("alunos").select("*").eq("turma", t_sel).order("nome").execute().data
        mapa_fotos = listar_arquivos_bucket()
        
        cols = st.columns(4)
        for idx, al in enumerate(alunos):
            with cols[idx % 4]:
                with st.container(border=True):
                    chave = limpar_texto(al['nome'])
                    arq = mapa_fotos.get(chave)
                    if arq: st.image(get_foto_url(arq), use_container_width=True)
                    else: st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#eee; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='nome-card'>{al['nome']}</div>", unsafe_allow_html=True)

# --- DEMAIS TELAS ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Cadastro")
    # Seu código de cadastro aqui

elif menu_escolhido == "Importação":
    st.title("📤 Importação")
    # Seu código de importação aqui
