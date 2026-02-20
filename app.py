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

# Estilização CSS para Mobile e Interface
st.markdown("""
    <style>
        .stSelectbox div[data-baseweb="select"] input { inputmode: none !important; }
        .espaco-reservado {
            padding: 12px; border-radius: 8px; background-color: #fff5f5;
            border-left: 6px solid #ff5252; margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .espaco-livre {
            padding: 12px; border-radius: 8px; background-color: #f0fdf4;
            border-left: 6px solid #4ade80; margin-bottom: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .nome-card { text-align: center; font-weight: bold; font-size: 12px; margin-top: 5px; color: #333; }
    </style>
""", unsafe_allow_html=True)

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

# --- SUA LISTA DE ESPAÇOS ATUALIZADA ---
ESPACOS_ESCOLA = [
    "Data show", 
    "Auditório", 
    "Sala de informática", 
    "Biblioteca", 
    "Refeitório", 
    "Lab. de ciências", 
    "Aparelho de som"
]

PERIODOS = ["1º Horário", "2º Horário", "3º Horário", "4º Horário", "5º Horário", "6º Horário", "Contra-turno"]

# ==================================================
# 2. FUNÇÕES AUXILIARES
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
    except: return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return None

# ==================================================
# 3. SIDEBAR
# ==================================================
with st.sidebar:
    col_centro = st.columns([1, 2, 1])[1]
    with col_centro:
        if os.path.exists("logo_erempam.png"): st.image("logo_erempam.png", use_container_width=True)
        else: st.markdown("<h1>🏫</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center; margin-top: 0;'>SIGPAM</h2>", unsafe_allow_html=True)
    
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Fotograma", "Reservas", "Frequência", "Reposicionar", "Cadastro", "Importação"],
        icons=["camera-fill", "calendar-check-fill", "clipboard-check-fill", "arrow-left-right", "person-plus-fill", "cloud-upload-fill"],
        default_index=1, # Inicia direto em Reservas para testar
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# ==================================================
# 4. TELAS
# ==================================================

# --- TELA: RESERVAS ---
if menu_escolhido == "Reservas":
    st.title("📅 Reserva de Espaços e Recursos")
    aba_ver, aba_nova = st.tabs(["🔍 Consultar Agenda", "📝 Nova Reserva"])
    
    with aba_ver:
        c1, c2 = st.columns([1, 1])
        data_consulta = c1.date_input("Data:", value=date.today())
        
        # FILTRO POR ESPAÇO (Para quem usa sempre o mesmo)
        filtro_espaco = c2.selectbox("Filtrar por Espaço:", ["Todos"] + ESPACOS_ESCOLA)
        
        query = supabase.table("reservas").select("*").eq("data_reserva", str(data_consulta))
        if filtro_espaco != "Todos":
            query = query.eq("espaco", filtro_espaco)
        
        res = query.execute()
        df_res = pd.DataFrame(res.data)
        
        st.subheader(f"Agenda: {data_consulta.strftime('%d/%m/%Y')}")
        
        # Definir quais espaços mostrar
        espacos_para_exibir = ESPACOS_ESCOLA if filtro_espaco == "Todos" else [filtro_espaco]
        
        for espaco in espacos_para_exibir:
            reservas_local = df_res[df_res['espaco'] == espaco] if not df_res.empty else pd.DataFrame()
            
            if not reservas_local.empty:
                for _, r in reservas_local.iterrows():
                    st.markdown(f"""<div class='espaco-reservado'>
                        <b>🔴 {espaco}</b><br>
                        Professor: <b>{r['professor']}</b><br>
                        Horário: <b>{r['periodo']}</b>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='espaco-livre'><b>🟢 {espaco}</b> - Disponível para reserva</div>", unsafe_allow_html=True)

    with aba_nova:
        with st.form("form_reserva"):
            st.info("Preencha os dados abaixo para reservar um recurso.")
            prof = st.text_input("Seu Nome:")
            esp = st.selectbox("O que deseja reservar?", ESPACOS_ESCOLA)
            dat = st.date_input("Para qual dia?", value=date.today())
            per = st.select_slider("Qual horário?", options=PERIODOS)
            
            if st.form_submit_button("Confirmar Reserva"):
                if dat < date.today():
                    st.error("Não é possível reservar datas passadas.")
                elif not prof:
                    st.error("Por favor, identifique-se (Nome do Professor).")
                else:
                    # Checar conflito exato: Espaço + Data + Período
                    check = supabase.table("reservas").select("*").eq("espaco", esp).eq("data_reserva", str(dat)).eq("periodo", per).execute()
                    
                    if check.data:
                        st.error(f"OPS! O {esp} já está ocupado no {per} por {check.data[0]['professor']}.")
                    else:
                        supabase.table("reservas").insert({
                            "espaco": esp, "professor": prof.upper().strip(),
                            "data_reserva": str(dat), "periodo": per
                        }).execute()
                        st.success(f"Sucesso! {esp} reservado para {dat.strftime('%d/%m')}.")
                        time.sleep(1)
                        st.rerun()

# --- TELA: FOTOGRAMA (MAPA DE SALA) ---
elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    if lista_turmas:
        turma_sel = st.pills("Selecione a Turma:", options=lista_turmas, default=lista_turmas[0])
        if turma_sel:
            alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
            mapa_fotos = listar_arquivos_bucket()
            st.divider()
            cols = st.columns(4)
            for idx, a in enumerate(alunos):
                with cols[idx % 4]:
                    with st.container(border=True):
                        chave = limpar_texto(a['nome'])
                        arq_real = mapa_fotos.get(chave)
                        if arq_real: st.image(get_foto_url(arq_real), use_container_width=True)
                        else: st.markdown("<div style='height:100px; display:flex; align-items:center; justify-content:center; background:#f5f5f5; border-radius:5px;'>👤</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='nome-card'>{a['nome']}</div>", unsafe_allow_html=True)

# --- TELA: IMPORTAÇÃO E MANUTENÇÃO ---
elif menu_escolhido == "Importação":
    st.title("📤 Manutenção e Dados")
    st.info("Área destinada a importação de alunos e limpeza anual do sistema.")
    
    # Manutenção de Reservas (Somente no fim do ano)
    with st.expander("🧹 Limpeza Anual de Reservas"):
        hoje = date.today()
        if hoje.month == 12 and hoje.day == 31:
            st.warning("Atenção: A limpeza de dados está liberada hoje (31/12).")
            if st.button("Executar Limpeza para Novo Ano"):
                supabase.table("reservas").delete().lte("data_reserva", f"{hoje.year}-12-31").execute()
                st.success("Tabela de reservas limpa!")
        else:
            st.error(f"Bloqueado. A limpeza só pode ser feita em 31/12/{hoje.year}.")

# (Demais telas como Cadastro, Reposicionar e Frequência permanecem iguais)
