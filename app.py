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

# 1. CONFIGURAÇÃO E CONEXÃO
st.set_page_config(page_title="SIGPAM - EREMPAM", layout="wide")

@st.cache_resource
def init_connection():
    load_dotenv()
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = init_connection()

# --- DADOS MESTRES ---
LISTA_PROFESSORES = [
    "ALEXANDRO", "AUGUSTO", "BRUNO LARDIÃO", "CAMILA", "CATARINA", 
    "CELSO GOMES", "CLEBSON", "EDINEI NOVAIS", "EDVÂNIA", "GABRIEL", 
    "GELSON", "HUGO", "IGOR", "JACKSON", "JAMES", "JÉSSICA VITORINO", 
    "LILIAN JORDÃO", "LYLIAN CABRAL", "PATRICIA", "PEDRO", "RAFAEL", 
    "ROBERTA", "SÉRGIO", "SEVERINO", "TYAGO", "VIVIANE"
]

AULAS_OPCOES = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula", "7ª Aula", "8ª Aula", "9ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Laboratório de Informática", "Biblioteca", "Refeitório", "Quadra", "Nenhum (Só Equipamento)"]

TOTAL_DATASHOWS = 5
TOTAL_CAIXAS = 3
TOTAL_MICROFONES = 2

# --- FUNÇÕES AUXILIARES PARA O FOTOGRAMA ---
def limpar_texto(texto):
    if not texto: return ""
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list()
        return {limpar_texto(arq['name'].split('.')[0]): arq['name'] for arq in arquivos}
    except: return {}

def get_foto_url(nome_arquivo):
    try:
        return f"{st.secrets['SUPABASE_URL']}/storage/v1/object/public/fotos-alunos/{quote(nome_arquivo)}"
    except: return None

# 2. SIDEBAR MENU (FREQUÊNCIA AGORA É O INDEX 0)
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>SIGPAM</h2>", unsafe_allow_html=True)
    menu_escolhido = option_menu(
        menu_title=None,
        options=["Frequência", "Reservas", "Fotograma", "Cadastro", "Importação"],
        icons=["clipboard-check", "calendar-check", "camera", "person-plus", "cloud-upload"],
        default_index=0, # ALTERAÇÃO: Frequência abre primeiro
        styles={"nav-link-selected": {"background-color": "#ff4b4b"}}
    )

# 3. TELAS
if menu_escolhido == "Frequência":
    st.title("📊 Relatório de Frequência Diária")
    hoje = date.today().isoformat()
    
    # Busca dados de presença para os gráficos
    try:
        res_total = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_total.count
        res_freq = supabase.table("frequencia").select("*").eq("data_chamada", hoje).execute()
        df_presenca = pd.DataFrame(res_freq.data)

        if not df_presenca.empty:
            presentes = len(df_presenca.drop_duplicates(subset=['aluno_id']))
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Alunos", total_alunos)
            c2.metric("Presentes Hoje", presentes)
            c3.metric("Faltas", total_alunos - presentes)
            st.divider()
            st.dataframe(df_presenca, use_container_width=True)
        else:
            st.info(f"Nenhum registro de frequência para hoje ({date.today().strftime('%d/%m/%Y')}).")
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

elif menu_escolhido == "Reservas":
    st.title("📅 Sistema de Reservas")
    col1, col2 = st.columns([1, 2])
    with col1:
        data_sel = st.date_input("Data da Reserva:", value=date.today(), format="DD/MM/YYYY")
    with col2:
        selecionar_tudo = st.checkbox("Dia Inteiro")
        aulas_selecionadas = st.pills("Selecione as Aulas:", options=AULAS_OPCOES, selection_mode="multi", default=AULAS_OPCOES if selecionar_tudo else [])

    if aulas_selecionadas:
        try:
            res_r = supabase.table("reservas").select("*").eq("data_reserva", str(data_sel)).in_("periodo", aulas_selecionadas).execute()
            reservas_dia = res_r.data
        except: reservas_dia = []

        # Lógica de Ocupação e Inventário
        espacos_ocupados = [r['espaco'] for r in reservas_dia if r.get('espaco') and r['espaco'] != "Nenhum (Só Equipamento)"]
        espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]
        
        d_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Datashow" in r['equipamentos'])
        c_usadas = sum(1 for r in reservas_dia if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
        m_usados = sum(1 for r in reservas_dia if r.get('equipamentos') and "Microfone" in r['equipamentos'])
        
        opcoes_equip = []
        if (TOTAL_DATASHOWS - d_usados) > 0: opcoes_equip.append(f"Datashow ({TOTAL_DATASHOWS - d_usados} disponíveis)")
        if (TOTAL_CAIXAS - c_usadas) > 0: opcoes_equip.append(f"Caixa de Som ({TOTAL_CAIXAS - c_usadas} disponíveis)")
        if (TOTAL_MICROFONES - m_usados) > 0: opcoes_equip.append(f"Microfone ({TOTAL_MICROFONES - m_usados} disponíveis)")

        with st.form("form_reserva"):
            prof_sel = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
            esp_final = st.selectbox("📍 Espaço:", espacos_disponiveis if espacos_disponiveis else ["⚠️ Todos ocupados"])
            equip_sel = st.multiselect("💻 Equipamentos (Opcional):", opcoes_equip if opcoes_equip else ["Nenhum disponível"])
            obs = st.text_area("📝 Observações:")
            
            if st.form_submit_button("Confirmar Reserva", use_container_width=True):
                if prof_sel != "-- Selecione --":
                    e_limpos = [e.split(" (")[0] for e in equip_sel if "disponíve" in e]
                    for aula in aulas_selecionadas:
                        supabase.table("reservas").insert({
                            "data_reserva": str(data_sel), "periodo": aula, "professor": prof_sel,
                            "espaco": esp_final, "equipamentos": ", ".join(e_limpos) if e_limpos else "Nenhum", "observacoes": obs
                        }).execute()
                    st.success("Reserva confirmada!")
                    time.sleep(1)
                    st.rerun()

elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala (Fotograma)")
    try:
        # Busca turmas disponíveis
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        if lista_turmas:
            turma_sel = st.pills("Selecione a Turma:", options=lista_turmas)
            if turma_sel:
                alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
                mapa_fotos = listar_arquivos_bucket()
                
                cols = st.columns(5)
                for idx, aluno in enumerate(alunos):
                    with cols[idx % 5]:
                        with st.container(border=True):
                            chave = limpar_texto(aluno['nome'])
                            foto_arq = mapa_fotos.get(chave)
                            if foto_arq:
                                st.image(get_foto_url(foto_arq), use_container_width=True)
                            else:
                                st.markdown("<div style='height:150px; background:#f0f0f0; display:flex; align-items:center; justify-content:center; border-radius:10px;'>👤</div>", unsafe_allow_html=True)
                            st.caption(f"**{aluno['nome']}**")
        else:
            st.warning("Nenhuma turma encontrada no cadastro.")
    except Exception as e:
        st.error(f"Erro ao carregar fotograma: {e}")

elif menu_escolhido == "Cadastro":
    st.title("👤 Cadastro de Alunos")
    st.info("Funcionalidade em desenvolvimento.")

elif menu_escolhido == "Importação":
    st.title("📤 Importação de Dados")
    st.info("Funcionalidade em desenvolvimento.")
