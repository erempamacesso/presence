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

# --- 7. BIBLIOTECA DE QUESTÕES (SISTEMA COM TELA DE EDIÇÃO FOCADA) ---
elif menu == "📚 Biblioteca de Questões":
    
    # 1. Variável de controle de estado (saber se estamos na Lista ou na Edição)
    if 'editando_id' not in st.session_state:
        st.session_state.editando_id = None

    # ==========================================
    # 🟢 MODO 1: TELA DE EDIÇÃO DA QUESTÃO
    # ==========================================
    if st.session_state.editando_id is not None:
        st.title("✏️ Editar Questão")
        
        # Botão para cancelar e voltar
        if st.button("⬅️ Voltar para a Biblioteca", type="secondary"):
            st.session_state.editando_id = None
            st.rerun()
            
        # Buscar a questão selecionada no banco
        res_q = supabase.table("questoes").select("*").eq("id", st.session_state.editando_id).execute()
        
        if res_q.data:
            q = res_q.data[0]
            
            with st.form(key=f"form_edita_{q['id']}"):
                st.markdown("### Configurações Gerais")
                c1, c2, c3, c4 = st.columns(4)
                
                idx_serie = ["1º Ano", "2º Ano", "3º Ano"].index(q.get('serie', "1º Ano")) if q.get('serie') in ["1º Ano", "2º Ano", "3º Ano"] else 0
                idx_gab = ["A", "B", "C", "D"].index(q.get('resposta_correta', "B")) if q.get('resposta_correta') in ["A", "B", "C", "D"] else 1
                idx_diff = ["Fácil", "Média", "Difícil"].index(q.get('dificuldade', "Média")) if q.get('dificuldade') in ["Fácil", "Média", "Difícil"] else 1
                
                with c1: edit_serie = st.selectbox("Série", ["1º Ano", "2º Ano", "3º Ano"], index=idx_serie)
                with c2: edit_assunto = st.text_input("Assunto", value=q.get('assunto', ''))
                with c3: edit_gabarito = st.selectbox("Gabarito", ["A", "B", "C", "D"], index=idx_gab)
                with c4: edit_diff = st.selectbox("Dificuldade", ["Fácil", "Média", "Difícil"], index=idx_diff)
                
                st.markdown("---")
                st.markdown("📝 **Enunciado da Questão** (Cole textos ou imagens aqui)")
                edit_enunciado = st_quill(value=q.get('enunciado', ''), html=True, key=f"q_editor_{q['id']}")
                
                st.markdown("---")
                st.markdown("🧠 **Alternativas e Diagnósticos**")
                alts = q.get('alternativas', {})
                justs = q.get('justificativas', {})
                
                edit_alts = {}
                edit_justs = {}
                for letra in ["A", "B", "C", "D"]:
                    ca, cj = st.columns([1, 2])
                    with ca: edit_alts[letra] = st.text_input(f"Texto {letra}", value=alts.get(letra, ""))
                    with cj: edit_justs[letra] = st.text_input(f"Diagnóstico {letra}", value=justs.get(letra, ""))
                    
                st.markdown("---")
                btn_salvar = st.form_submit_button("💾 Salvar Alterações e Voltar", type="primary", use_container_width=True)
                
                if btn_salvar:
                    dados_upd = {
                        "serie": edit_serie,
                        "assunto": edit_assunto,
                        "resposta_correta": edit_gabarito,
                        "dificuldade": edit_diff,
                        "enunciado": edit_enunciado,
                        "alternativas": edit_alts,
                        "justificativas": edit_justs
                    }
                    supabase.table("questoes").update(dados_upd).eq("id", q['id']).execute()
                    # Zera o estado para voltar à lista
                    st.session_state.editando_id = None
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()

    # ==========================================
    # 🔵 MODO 2: TELA DE LISTAGEM (BIBLIOTECA)
    # ==========================================
    else:
        st.title("📚 Biblioteca de Questões")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1: f_serie = st.multiselect("Série", ["1º Ano", "2º Ano", "3º Ano"])
        with col2:
            res_a = supabase.table("questoes").select("assunto").execute()
            assuntos = sorted(list(set([x['assunto'] for x in res_a.data if x['assunto']])))
            f_assunto = st.multiselect("Assunto", assuntos)
        with col3: f_diff = st.multiselect("Dificuldade", ["Fácil", "Média", "Difícil"])

        query = supabase.table("questoes").select("id, serie, assunto, dificuldade, enunciado, resposta_correta")
        if f_serie: query = query.in_("serie", f_serie)
        if f_assunto: query = query.in_("assunto", f_assunto)
        if f_diff: query = query.in_("dificuldade", f_diff)
        
        data = query.execute().data
        
        if data:
            import re
            st.write(f"🔍 Encontradas: **{len(data)}** questões")
            st.divider()
            
            # Cabeçalho da Lista
            h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([0.6, 0.8, 1.2, 4, 0.5, 0.8])
            h_c1.caption("ID")
            h_c2.caption("STATUS")
            h_c3.caption("CLASSIFICAÇÃO")
            h_c4.caption("ENUNCIADO (PRÉVIA)")
            h_c5.caption("GAB.")
            h_c6.caption("AÇÕES")
            
            for q in data:
                texto_puro = re.sub('<[^<]+>', '', str(q['enunciado']))
                previa = texto_puro[:90] + "..." if len(texto_puro) > 90 else texto_puro
                
                with st.container(border=True):
                    c1, c2, c3, c4, c5, c6 = st.columns([0.6, 0.8, 1.2, 4, 0.5, 0.8], gap="small")
                    
                    # ID curto
                    id_curto = str(q['id']).split('-')[0][:4] 
                    c1.write(f"#{id_curto}")
                    
                    # Status
                    c2.markdown('<span style="color: #28a745; background-color: #d4edda; padding: 4px; border-radius: 4px; font-size: 11px;">✅ Pronta</span>', unsafe_allow_html=True)
                    
                    # Classificação
                    c3.markdown(f"**{q['serie']}**<br><span style='color:#28a745; font-size:11px;'>{q['assunto'].upper()}</span>", unsafe_allow_html=True)
                    
                    # Enunciado
                    c4.write(previa)
                    
                    # Gabarito
                    c5.markdown(f"**{q['resposta_correta']}**")
                    
                    # Botões de Ação
                    bc1, bc2 = c6.columns(2)
                    
                    # Botão Editar
                    if bc1.button("✏️", key=f"edit_{q['id']}", help="Editar questão"):
                        st.session_state.editando_id = q['id']
                        st.rerun()
                        
                    # Botão Excluir
                    if bc2.button("🗑️", key=f"del_{q['id']}", help="Excluir questão"):
                        supabase.table("questoes").delete().eq("id", q['id']).execute()
                        st.rerun()
        else:
            st.info("Nenhuma questão encontrada.")

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