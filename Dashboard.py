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

# --- 7. BIBLIOTECA DE QUESTÕES (COM EDIÇÃO EM LOTE) ---
elif menu == "📚 Biblioteca de Questões":
    st.title("📚 Biblioteca de Questões")
    
    # Filtros superiores
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
        # Criando abas para separar a visualização da edição em massa
        tab_view, tab_edit = st.tabs(["👀 Visualização Padrão", "✏️ Edição Geral (Planilha)"])
        
        with tab_view:
            st.write(f"Encontradas: {len(data)}")
            for q in data:
                with st.expander(f"[{q['serie']}] {q['assunto']} ({q['dificuldade']})"):
                    st.markdown(q['enunciado'], unsafe_allow_html=True)
                    st.write(f"**Correta:** {q['resposta_correta']}")
                    if st.button("🗑️ Excluir", key=f"del_{q['id']}"):
                        supabase.table("questoes").delete().eq("id", q['id']).execute()
                        st.rerun()
                        
        with tab_edit:
            st.info("💡 Clique diretamente nas células abaixo para editar. Depois, clique em 'Salvar Alterações'.")
            df_edit = pd.DataFrame(data)
            
            # Selecionando apenas as colunas amigáveis para edição (ignorando dicionários complexos)
            colunas_visao = ['id', 'serie', 'assunto', 'dificuldade', 'resposta_correta']
            df_view = df_edit[colunas_visao]
            
            # Componente de Data Grid interativo do Streamlit
            edited_df = st.data_editor(
                df_view,
                disabled=["id"], # Bloqueia a edição do ID
                hide_index=True,
                use_container_width=True,
                column_config={
                    "serie": st.column_config.SelectboxColumn("Série", options=["1º Ano", "2º Ano", "3º Ano"]),
                    "dificuldade": st.column_config.SelectboxColumn("Dificuldade", options=["Fácil", "Média", "Difícil"]),
                    "resposta_correta": st.column_config.SelectboxColumn("Gabarito", options=["A", "B", "C", "D"])
                }
            )
            
            if st.button("💾 Salvar Alterações em Lote"):
                # Compara o DataFrame editado com o original para achar o que mudou
                mudancas = edited_df.compare(df_view)
                if not mudancas.empty:
                    with st.spinner("Salvando no banco de dados..."):
                        for index in mudancas.index:
                            row_id = edited_df.loc[index, 'id']
                            dados_atualizados = {
                                "serie": edited_df.loc[index, 'serie'],
                                "assunto": edited_df.loc[index, 'assunto'],
                                "dificuldade": edited_df.loc[index, 'dificuldade'],
                                "resposta_correta": edited_df.loc[index, 'resposta_correta']
                            }
                            supabase.table("questoes").update(dados_atualizados).eq("id", row_id).execute()
                    st.success("Atualizações salvas com sucesso!")
                    st.rerun()
                else:
                    st.warning("Nenhuma alteração foi feita na tabela.")
    else:
        st.info("Nenhuma questão encontrada com esses filtros.")

# --- 8. GERADOR DE MODELOS (ESTILO CARDS PROFISSIONAIS) ---
elif menu == "📜 Gerar Modelo de Prova":
    st.title("📜 Publicar Prova para Alunos")
    
    # Import para limpar HTML da prévia
    import re

    # Buscamos as questões
    res_q = supabase.table("questoes").select("id, assunto, serie, dificuldade, enunciado, resposta_correta").execute()
    df_q = pd.DataFrame(res_q.data)
    
    if not df_q.empty:
        # Área de Configuração da Prova
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            tit = st.text_input("Título da Prova", placeholder="Ex: 1º Simulado Bimestral")
        with col_t2:
            ser = st.selectbox("Filtrar questões da Série:", ["1º Ano", "2º Ano", "3º Ano"])
        
        st.divider()
        st.subheader("📋 Selecione as Questões para a Prova")
        
        # Filtragem por série selecionada
        qs_disp = df_q[df_q['serie'] == ser]
        
        # Cabeçalho da "Tabela" de Cards
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([0.8, 1.2, 5, 0.5, 0.5])
        h_col1.caption("STATUS")
        h_col2.caption("CLASSIFICAÇÃO")
        h_col3.caption("ENUNCIADO (PRÉVIA)")
        h_col4.caption("GAB.")
        h_col5.caption("SEL.")

        questoes_selecionadas = []

        # Renderização dos Cards conforme o print
        for _, row in qs_disp.iterrows():
            # Limpeza do enunciado para prévia (remove tags HTML do Quill)
            texto_puro = re.sub('<[^<]+>', '', str(row['enunciado']))
            previa = texto_puro[:120] + "..." if len(texto_puro) > 120 else texto_puro
            
            # Container do Card
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([0.8, 1.2, 5, 0.5, 0.5])
                
                # Coluna 1: Status (Estilizado)
                c1.markdown('<span style="color: #28a745; background-color: #d4edda; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">✅ Pronta</span>', unsafe_allow_html=True)
                
                # Coluna 2: Classificação
                c2.markdown(f"**{row['serie']}**\n\n<span style='color: #28a745; font-size: 11px; font-weight: bold;'>{row['assunto'].upper()}</span>", unsafe_allow_html=True)
                
                # Coluna 3: Enunciado
                c3.write(previa)
                with c3.expander("🔍 Ver questão completa"):
                    st.markdown(row['enunciado'], unsafe_allow_html=True)
                
                # Coluna 4: Gabarito
                c4.markdown(f"### {row['resposta_correta']}")
                
                # Coluna 5: Checkbox de Seleção
                # Usamos o ID no key para garantir que seja único
                escolhida = c5.checkbox("", key=f"sel_{row['id']}")
                if escolhida:
                    questoes_selecionadas.append(row['id'])

        # Rodapé fixo para publicar
        st.divider()
        col_fim1, col_fim2 = st.columns([4, 1])
        col_fim1.write(f"📂 **{len(questoes_selecionadas)}** questões selecionadas para esta prova.")
        
        if col_fim2.button("🚀 Publicar Prova", type="primary", use_container_width=True):
            if questoes_selecionadas and tit:
                with st.spinner("Publicando..."):
                    supabase.table("modelos_prova").insert({
                        "titulo": tit, 
                        "serie": ser, 
                        "questoes_ids": questoes_selecionadas, 
                        "ativa": True
                    }).execute()
                st.success(f"Prova '{tit}' publicada com sucesso!")
                st.balloons()
            else:
                st.error("Erro: Defina um título e selecione ao menos uma questão.")
    else:
        st.warning("Nenhuma questão cadastrada para gerar provas.")