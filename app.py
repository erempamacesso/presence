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
        .espaco-reservado {
            padding: 12px; border-radius: 8px; background-color: #fff5f5;
            border-left: 6px solid #ff5252; margin-bottom: 10px;
        }
        .espaco-livre {
            padding: 12px; border-radius: 8px; background-color: #f0fdf4;
            border-left: 6px solid #4ade80; margin-bottom: 10px;
        }
        .nome-card { text-align: center; font-weight: bold; font-size: 12px; margin-top: 5px; color: #333; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# Configurações de Espaços e Aulas
ESPACOS_ESCOLA = ["Data show", "Auditório", "Sala de informática", "Biblioteca", "Refeitório", "Lab. de ciências", "Aparelho de som"]
LISTA_AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]

# ==================================================
# 2. FUNÇÕES AUXILIARES
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").strip()

@st.cache_data(ttl=600)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list()
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos}
    except: return {}

def get_foto_url(nome_real_arquivo):
    url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(nome_real_arquivo)}"
    return f"{url_base}?t={int(time.time())}"

# ==================================================
# 3. SIDEBAR (NOVA ORDEM SOLICITADA)
# ==================================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>SIGPAM</h2>", unsafe_allow_html=True)
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Frequência", "Reservas", "Fotograma", "Cadastro", "Importação"],
        icons=["clipboard-check-fill", "calendar-check-fill", "camera-fill", "person-plus-fill", "cloud-upload-fill"],
        default_index=1,
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# ==================================================
# 4. TELAS
# ==================================================

# --- TELA: RESERVAS (COM MÚLTIPLAS AULAS) ---
if menu_escolhido == "Reservas":
    st.title("📅 Reserva de Espaços")
    aba_ver, aba_nova = st.tabs(["🔍 Consultar Agenda", "📝 Nova Reserva"])
    
    with aba_ver:
        col1, col2 = st.columns(2)
        data_con = col1.date_input("Data:", value=date.today(), key="view_date")
        esp_filtro = col2.selectbox("Filtrar Espaço:", ["Todos"] + ESPACOS_ESCOLA)
        
        res = supabase.table("reservas").select("*").eq("data_reserva", str(data_con)).execute()
        df_res = pd.DataFrame(res.data)
        
        exibir = ESPACOS_ESCOLA if esp_filtro == "Todos" else [esp_filtro]
        for e in exibir:
            reservas_e = df_res[df_res['espaco'] == e] if not df_res.empty else pd.DataFrame()
            if not reservas_e.empty:
                # Agrupa aulas reservadas pelo mesmo professor
                for prof, dados in reservas_e.groupby("professor"):
                    aulas_list = ", ".join(sorted(dados["periodo"].tolist()))
                    st.markdown(f"<div class='espaco-reservado'><b>🔴 {e}</b><br>Professor: {prof}<br>Aulas: {aulas_list}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='espaco-livre'><b>🟢 {e}</b> - Disponível</div>", unsafe_allow_html=True)

    with aba_nova:
        with st.form("form_multi_reserva"):
            prof_nome = st.text_input("Seu Nome:")
            esp_escolhido = st.selectbox("Recurso:", ESPACOS_ESCOLA)
            data_res = st.date_input("Data:", value=date.today())
            
            st.write("---")
            st.write("📂 **Selecione as Aulas (toque para marcar várias):**")
            aulas_selecionadas = st.pills("Horários", options=LISTA_AULAS, selection_mode="multi")
            
            if st.form_submit_button("Confirmar Reservas"):
                if not prof_nome or not aulas_selecionadas:
                    st.error("Preencha seu nome e selecione pelo menos uma aula.")
                elif data_res < date.today():
                    st.error("Não é possível reservar datas passadas.")
                else:
                    sucesso = []
                    erros = []
                    
                    for aula in aulas_selecionadas:
                        # Checa se a aula específica já está ocupada
                        check = supabase.table("reservas").select("*").eq("espaco", esp_escolhido).eq("data_reserva", str(data_res)).eq("periodo", aula).execute()
                        
                        if check.data:
                            erros.append(f"{aula} (por {check.data[0]['professor']})")
                        else:
                            supabase.table("reservas").insert({
                                "espaco": esp_escolhido, "professor": prof_nome.upper().strip(),
                                "data_reserva": str(data_res), "periodo": aula
                            }).execute()
                            sucesso.append(aula)
                    
                    if sucesso: st.success(f"Reservado: {', '.join(sucesso)}")
                    if erros: st.error(f"Já ocupados: {', '.join(erros)}")
                    time.sleep(1.5)
                    st.rerun()

# --- TELA: FOTOGRAMA ---
elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    if lista_turmas:
        turma_sel = st.pills("Turma:", options=lista_turmas, default=lista_turmas[0])
        alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
        mapa = listar_arquivos_bucket()
        cols = st.columns(4)
        for idx, a in enumerate(alunos):
            with cols[idx % 4]:
                with st.container(border=True):
                    arq = mapa.get(limpar_texto(a['nome']))
                    if arq: st.image(get_foto_url(arq), use_container_width=True)
                    else: st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#f5f5f5; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='nome-card'>{a['nome']}</div>", unsafe_allow_html=True)

# --- TELAS VAZIAS (Aguardando seu código de Frequência) ---
elif menu_escolhido == "Frequência":
    st.title("📊 Chamada Diária")
    st.info("Aguardando inserção do código de frequência...")

elif menu_escolhido == "Cadastro":
    st.title("👤 Cadastro de Alunos")

elif menu_escolhido == "Importação":
    st.title("📤 Importação de Dados")
