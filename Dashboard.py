import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
URL = st.secrets["SUPABASE_URL_PROVAS"]
KEY = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL, KEY)

# --- 3. SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Administrativo - EREMPAM")
    senha = st.text_input("Digite a senha de gestão:", type="password")
    if st.button("Entrar"):
        if senha == "erempam2024": # Sua senha
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 4. MENU LATERAL ---
st.sidebar.title("🎮 Painel do Professor")
menu = st.sidebar.radio("Navegação", [
    "📊 Dashboard Diagnóstico", 
    "📝 Cadastrar Questões", 
    "📚 Biblioteca de Questões", 
    "📜 Gerar Modelo de Prova"
])

# --- 5. LOGICA DO DASHBOARD DIAGNÓSTICO ---
if menu == "📊 Dashboard Diagnóstico":
    st.title("📊 Diagnóstico em Tempo Real")
    try:
        res = supabase.table("dashboard_diagnostico").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Acertos por Assunto")
                fig = px.bar(df, x="assunto", y="perc_acerto", color="serie", barmode="group", text_auto='.1f')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("Engajamento por Turma")
                fig2 = px.pie(df, values='total_respostas', names='serie', hole=.4)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum dado de resposta encontrado ainda.")
    except:
        st.warning("Aguardando dados ou View SQL...")

# --- 6. CADASTRO DE QUESTÕES (MANUAL + IA) ---
elif menu == "📝 Cadastrar Questões":
    st.title("🖊️ Criador de Atv. online do Prof. Lardião")
    
    # SELETOR DE CONTEXTO (Serve para o manual e para o Importador)
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: serie_ctx = st.selectbox("Série/Ano", ["1º Ano", "2º Ano", "3º Ano"])
    with col_c2: assunto_ctx = st.text_input("Assunto (ex: Química Orgânica)")
    with col_c3: diff_ctx = st.select_slider("Dificuldade Padrão", options=["Fácil", "Média", "Difícil"])

    # --- SUB-ABA: IMPORTADOR IA ---
    with st.expander("🚀 IMPORTADOR FLASH (COLE O JSON DA IA AQUI)", expanded=True):
        st.write("Gere as questões na IA, copie o JSON e cole abaixo:")
        json_input = st.text_area("Área do JSON:", height=250, placeholder='[ { "enunciado": "...", ... } ]')
        
        if st.button("📥 Importar Todas as Questões em Lote"):
            if json_input:
                try:
                    lista_q = json.loads(json_input)
                    for q in lista_q:
                        # Lógica para achar a correta baseada no feedback positivo
                        letra_correta = "B" # Padrão
                        for letra, fb in q["justificativas"].items():
                            if any(word in fb.lower() for word in ["parabéns", "correto", "excelente", "muito bem"]):
                                letra_correta = letra
                        
                        dados_ia = {
                            "enunciado": q["enunciado"],
                            "alternativas": q["alternativas"],
                            "justificativas": q["justificativas"],
                            "resposta_correta": q.get("resposta_correta", letra_correta),
                            "serie": serie_ctx,
                            "assunto": assunto_ctx if assunto_ctx else "Geral",
                            "dificuldade": q.get("nivel_dificuldade", diff_ctx)
                        }
                        supabase.table("questoes").insert(dados_ia).execute()
                    st.success(f"🔥 {len(lista_q)} questões importadas com sucesso!")
                except Exception as e:
                    st.error(f"Erro no JSON: {e}")
            else:
                st.warning("Cole o código primeiro!")

    st.divider()

    # --- SUB-ABA: CADASTRO MANUAL ---
    with st.expander("📝 Cadastro Manual Individual"):
        with st.form("manual_q", clear_on_submit=True):
            st.write("### Enunciado")
            enun_html = st_quill(html=True, key="manual_quill")
            
            alt_txt = {}
            just_txt = {}
            for l in ["A", "B", "C", "D"]:
                c1, c2 = st.columns([1, 2])
                with c1: alt_txt[l] = st.text_input(f"Texto {l}", key=f"t{l}")
                with c2: just_txt[l] = st.text_input(f"Diagnóstico {l}", key=f"j{l}")
            
            correta_m = st.selectbox("Correta", ["A", "B", "C", "D"])
            
            if st.form_submit_button("💾 Salvar Questão Única"):
                dados_m = {
                    "enunciado": enun_html, "alternativas": alt_txt, "justificativas": just_txt,
                    "resposta_correta": correta_m, "serie": serie_ctx, 
                    "assunto": assunto_ctx, "dificuldade": diff_ctx
                }
                supabase.table("questoes").insert(dados_m).execute()
                st.success("Questão salva!")

# --- 7. BIBLIOTECA DE QUESTÕES ---
elif menu == "📚 Biblioteca de Questões":
    st.title("📚 Biblioteca de Questões")
    
    col1, col2, col3 = st.columns(3)
    with col1: f_serie = st.multiselect("Série", ["1º Ano", "2º Ano", "3º Ano"])
    with col2:
        res_a = supabase.table("questoes").select("assunto").execute()
        assuntos = sorted(list(set([x['assunto'] for x in res_a.data if x['assunto']])))
        f_assunto = st.multiselect("Assunto", assuntos)
    with col3: f_diff = st.multiselect("Dificuldade", ["Fácil", "Média", "Difícil"])

    query = supabase.table("questoes").select("*")
    if f_serie: query = query.in_("serie", f_serie)
    if f_assunto: query = query.in_("assunto", f_assunto)
    if f_diff: query = query.in_("dificuldade", f_diff)
    
    data = query.execute().data
    if data:
        st.write(f"Encontradas: {len(data)}")
        for q in data:
            with st.expander(f"[{q['serie']}] {q['assunto']} ({q['dificuldade']})"):
                st.markdown(q['enunciado'], unsafe_allow_html=True)
                st.write(f"**Correta:** {q['resposta_correta']}")
                if st.button("🗑️ Excluir", key=f"del_{q['id']}"):
                    supabase.table("questoes").delete().eq("id", q['id']).execute()
                    st.rerun()
    else:
        st.info("Nada encontrado.")

# --- 8. GERADOR DE MODELOS ---
elif menu == "📜 Gerar Modelo de Prova":
    st.title("📜 Publicar Prova para Alunos")
    res_q = supabase.table("questoes").select("id, assunto, serie").execute()
    df_q = pd.DataFrame(res_q.data)
    
    if not df_q.empty:
        tit = st.text_input("Título da Prova")
        ser = st.selectbox("Série alvo", ["1º Ano", "2º Ano", "3º Ano"])
        qs_disp = df_q[df_q['serie'] == ser]
        selec = st.multiselect("Selecione as questões:", options=qs_disp['id'].tolist(),
                               format_func=lambda x: f"ID:{x} - {qs_disp[qs_disp['id']==x]['assunto'].values[0]}")
        
        if st.button("🚀 Colocar Prova Online"):
            if selec and tit:
                supabase.table("modelos_prova").insert({"titulo": tit, "serie": ser, "questoes_ids": selec, "ativa": True}).execute()
                st.success(f"Prova '{tit}' publicada!")