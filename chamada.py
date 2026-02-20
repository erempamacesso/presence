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

# Estilização CSS para cards e alertas
st.markdown("""
    <style>
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
# 2. FUNÇÕES AUXILIARES (FOTOGRAMA RECUPERADO)
# ==================================================
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto).split(".")[0] # Remove extensões se houver
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        # Busca recursiva para garantir que pegamos todos os arquivos
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 2000})
        return {limpar_texto(arq['name']): arq['name'] for arq in arquivos if arq['name'] != ".emptyFolderPlaceholder"}
    except Exception as e:
        st.error(f"Erro ao carregar fotos: {e}")
        return {}

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

# --- TELA: FREQUÊNCIA ---
if menu_escolhido == "Frequência":
    st.title("📊 Monitor de Frequência")
    hoje = date.today().isoformat()
    
    with st.spinner("Atualizando estatísticas..."):
        res_alunos = supabase.table("alunos").select("id", count="exact").execute()
        total_alunos = res_alunos.count
        
        res_frequencia = supabase.table("frequencia").select("*").eq("data_chamada", hoje).execute()
        df_freq = pd.DataFrame(res_frequencia.data)
        
    if not df_freq.empty:
        presentes = len(df_freq[df_freq['status'] == 'P'])
        ausentes = total_alunos - presentes
        porcentagem = int((ausentes / total_alunos) * 100) if total_alunos > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matriculados", total_alunos)
        c2.metric("Presentes (Hoje)", presentes, delta="Biometria")
        c3.metric("Ausentes", ausentes, delta_color="inverse")
        c4.metric("% Ausência", f"{porcentagem}%")
        
        st.markdown("---")
        df_grafico = df_freq.groupby("turma").size().reset_index(name="Quantidade")
        chart = alt.Chart(df_grafico).mark_bar(color='#ff4b4b', cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
            x=alt.X('turma:N', title="Turmas"),
            y=alt.Y('Quantidade:Q', title="Alunos Presentes"),
            tooltip=['turma', 'Quantidade']
        ).properties(height=350).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info(f"Aguardando os primeiros registros de biometria de hoje ({date.today().strftime('%d/%m/%Y')}).")

# --- TELA: RESERVAS ---
elif menu_escolhido == "Reservas":
    st.title("📅 Reserva de Espaços e Recursos")
    aba_ver, aba_nova = st.tabs(["🔍 Consultar Agenda", "📝 Nova Reserva"])
    
    with aba_ver:
        c1, c2 = st.columns(2)
        dt_con = c1.date_input("Data:", value=date.today(), key="view_dt")
        esp_f = c2.selectbox("Filtrar Espaço:", ["Todos"] + ESPACOS_ESCOLA)
        
        res_db = supabase.table("reservas").select("*").eq("data_reserva", str(dt_con)).execute()
        df_res = pd.DataFrame(res_db.data)
        
        exibir_lista = ESPACOS_ESCOLA if esp_f == "Todos" else [esp_f]
        for e in exibir_lista:
            res_e = df_res[df_res['espaco'] == e] if not df_res.empty else pd.DataFrame()
            if not res_e.empty:
                for prof, dados in res_e.groupby("professor"):
                    aulas = ", ".join(sorted(dados["periodo"].tolist()))
                    st.markdown(f"<div class='espaco-reservado'><b>🔴 {e}</b><br>Prof: {prof} | Aulas: {aulas}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='espaco-livre'><b>🟢 {e}</b> - Livre para todas as aulas</div>", unsafe_allow_html=True)

    with aba_nova:
        # O uso de st.form garante que, ao clicar no botão, os campos voltem ao estado inicial
        with st.form("form_reserva_limpo", clear_on_submit=True):
            st.write("### Criar nova reserva")
            prof_res = st.text_input("Nome do Professor:")
            esp_res = st.selectbox("Recurso:", ESPACOS_ESCOLA)
            data_res = st.date_input("Data:", value=date.today())
            aulas_res = st.pills("Selecione a(s) aula(s):", options=LISTA_AULAS, selection_mode="multi")
            
            submeteu = st.form_submit_button("Confirmar Reserva")
            
            if submeteu:
                if not prof_res or not aulas_res:
                    st.error("Erro: Preencha seu nome e escolha as aulas.")
                else:
                    sucessos = []
                    for aula in aulas_res:
                        # Validação de conflito
                        check = supabase.table("reservas").select("*").eq("espaco", esp_res).eq("data_reserva", str(data_res)).eq("periodo", aula).execute()
                        if not check.data:
                            supabase.table("reservas").insert({
                                "espaco": esp_res, "professor": prof_res.upper().strip(),
                                "data_reserva": str(data_res), "periodo": aula
                            }).execute()
                            sucessos.append(aula)
                    
                    if sucessos:
                        st.success(f"Reservas feitas: {', '.join(sucessos)}")
                        time.sleep(1)
                        st.rerun() # Limpa a tela completamente

# --- TELA: FOTOGRAMA (CORRIGIDO) ---
elif menu_escolhido == "Fotograma":
    st.title("📸 Mapa de Sala")
    res_t = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x.get('turma')])))
    
    if lista_turmas:
        turma_sel = st.pills("Turma:", options=lista_turmas, default=lista_turmas[0])
        alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute().data
        mapa_fotos = listar_arquivos_bucket()
        
        st.divider()
        cols = st.columns(4)
        for idx, a in enumerate(alunos):
            with cols[idx % 4]:
                with st.container(border=True):
                    # Lógica de match corrigida: limpa o nome do banco e compara com o do bucket
                    chave_busca = limpar_texto(a['nome'])
                    arq_final = mapa_fotos.get(chave_busca)
                    
                    if arq_final:
                        st.image(get_foto_url(arq_final), use_container_width=True)
                    else:
                        st.markdown("<div style='height:120px; display:flex; align-items:center; justify-content:center; background:#f0f2f6; border-radius:10px;'>👤</div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div class='nome-card'>{a['nome']}</div>", unsafe_allow_html=True)

# --- TELA: CADASTRO ---
elif menu_escolhido == "Cadastro":
    st.title("👤 Cadastro de Alunos")
    with st.form("cad_aluno", clear_on_submit=True):
        nome_novo = st.text_input("Nome Completo")
        turma_nova = st.text_input("Turma (Ex: 1º A)")
        if st.form_submit_button("Cadastrar"):
            if nome_novo and turma_nova:
                supabase.table("alunos").insert({"nome": nome_novo.upper(), "turma": turma_nova.upper()}).execute()
                st.success("Aluno cadastrado!")
            else:
                st.error("Preencha todos os campos.")

# --- TELA: IMPORTAÇÃO ---
elif menu_escolhido == "Importação":
    st.title("📤 Importação de Dados")
    # Código de upload e limpeza anual aqui
