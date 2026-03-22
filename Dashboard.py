import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json
import pytz  # <--- ADICIONE ESTA LINHA AQUI
from fpdf import FPDF
import base64
import re
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
# Conexão 1: PROVAS (Avaliador-Provas)
URL_P = st.secrets["SUPABASE_URL_PROVAS"]
KEY_P = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL_P, KEY_P)

# Conexão 2: ALUNOS (Chamada Escolar)
URL_A = st.secrets["SUPABASE_URL_ALUNOS"]
KEY_A = st.secrets["SUPABASE_KEY_ALUNOS"]
supabase_alunos = create_client(URL_A, KEY_A)

# --- 3. SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acesso Administrativo - EREMPAM")
    senha = st.text_input("Digite a senha de gestão:", type="password")
    if st.button("Entrar"):
        if senha == "erempam2024": 
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 4. MENU LATERAL ---
st.sidebar.title("🎮 Painel do Professor")
menu = st.sidebar.radio("Navegação", [
    "📊 Análise de Dados", 
    "📝 Cadastrar Questões", 
    "📚 Biblioteca de Questões", 
    "📜 Gerar Modelo de Prova",
    "📂 Provas Elaboradas",  
    "🖨️ Lista de Matrículas"
])

# --- 5. LÓGICA DO DASHBOARD (NOVA ANÁLISE DE DADOS) ---
if menu == "📊 Análise de Dados":
    st.title("📊 Análise de Dados e Diagnóstico")
    st.markdown("Acompanhe o engajamento e o desempenho das turmas em tempo real.")
    
    try:
        # 1. Buscar dados da View para Gráficos e KPIs (Projeto Provas)
        res_view = supabase.table("dashboard_diagnostico").select("*").execute()
        df = pd.DataFrame(res_view.data)
        
        # 2. Buscar dados Brutos para Engajamento (Projeto Provas)
        res_raw = supabase.table("resultados_provas").select("aluno_id").execute()
        
        # 3. NOVO: Buscar alunos para fazer a ponte de Turmas (Projeto Alunos)
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma").execute()
        
        if not df.empty and res_raw.data:
            # --- TRATAMENTO DE DADOS (EXTRAÇÃO DE SÉRIE E TURMA) ---
            df['serie_curta'] = df['serie'].str.extract(r'(1º|2º|3º)')
            df['letra_turma'] = df['serie'].str.extract(r'([A-E])')
            df['serie_curta'] = df['serie_curta'].fillna("N/A")
            df['letra_turma'] = df['letra_turma'].fillna("Geral")

            # --- SEÇÃO 1: KPIs (Visão Geral) ---
            st.markdown("### 🎯 Visão Geral")
            kpi1, kpi2, kpi3 = st.columns(3)
            
            df_raw = pd.DataFrame(res_raw.data)
            total_estudantes_unicos = df_raw['aluno_id'].nunique()
            
            media_geral = df['perc_acerto'].mean()
            melhor_assunto = df.loc[df['perc_acerto'].idxmax()]['assunto'] if not df.empty else "N/A"
            
            with kpi1:
                st.metric(label="Total de Estudantes Únicos", value=int(total_estudantes_unicos))
            with kpi2:
                st.metric(label="Média de Acertos Geral", value=f"{media_geral:.1f}%")
            with kpi3:
                st.metric(label="Assunto com Maior Domínio", value=str(melhor_assunto).upper())
            
            st.divider()
            
            # --- SEÇÃO 2: GRÁFICOS INTERATIVOS ---
            lista_series_filtro = sorted([s for s in df['serie_curta'].unique() if s != "N/A"])
            serie_foco = st.selectbox("🎯 Selecione a Série para detalhar:", ["Todas"] + lista_series_filtro)
            
            df_filtrado = df.copy()
            if serie_foco != "Todas":
                df_filtrado = df_filtrado[df_filtrado['serie_curta'] == serie_foco]

            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"Desempenho por Turma ({serie_foco})")
                fig = px.bar(
                    df_filtrado, 
                    x="assunto", 
                    y="perc_acerto", 
                    color="letra_turma",
                    barmode="group", 
                    text_auto='.1f',
                    labels={'perc_acerto': '% de Acerto', 'assunto': 'Assunto', 'letra_turma': 'Turma'},
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig.update_layout(xaxis_tickangle=-45, yaxis_title="% de Acertos")
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # --- NOVA LÓGICA DO GRÁFICO DE ROSCA (POR TURMA) ---
                st.subheader(f"Engajamento por Turma ({serie_foco})")
                
                df_alunos_join = pd.DataFrame(res_alunos_base.data)
                
                if not df_alunos_join.empty:
                    # Tratamento para cruzar texto com número
                    df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
                    df_alunos_join['id'] = df_alunos_join['id'].astype(str)
                    
                    # A Ponte (Join)
                    df_join = pd.merge(df_raw, df_alunos_join, left_on="aluno_id", right_on="id")
                    
                    # Aplica o filtro da tela (Se escolheu "3º Ano", busca turmas que começam com "3")
                    if serie_foco != "Todas":
                        prefixo_serie = serie_foco[0] # Pega só o número (ex: "3")
                        df_join = df_join[df_join['turma'].astype(str).str.startswith(prefixo_serie)]
                        
                    # Agrupa e Conta
                    df_pizza = df_join.groupby("turma").size().reset_index(name='total_respostas')
                    
                    # Renderiza
                    fig2 = px.pie(
                        df_pizza, 
                        values='total_respostas',
                        names='turma', 
                        hole=.4,
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    # Dá um leve espaçamento entre as fatias pra ficar mais bonito
                    fig2.update_traces(textposition='inside', textinfo='percent+label', pull=[0.02] * len(df_pizza))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Aguardando turmas para gerar o gráfico.")
                
            st.divider()
            
            # --- SEÇÃO 3: TABELA DE DADOS ---
            st.subheader("📋 Tabela de Dados Analíticos (Por Assunto)")
            df_view = df_filtrado.copy()
            if 'perc_acerto' in df_view.columns:
                df_view['perc_acerto'] = df_view['perc_acerto'].apply(lambda x: f"{x:.1f}%")

            st.dataframe(
                df_view[['assunto', 'serie', 'total_respostas', 'total_acertos', 'perc_acerto']], 
                use_container_width=True, 
                hide_index=True
            )
            
        else:
            st.info("📌 Nenhum dado de resposta de turmas encontrado no banco de dados.")

        # --- SEÇÃO 4: DESEMPENHO INDIVIDUAL ---
        st.divider()
        st.subheader("🏆 Notas Individuais por Aluno")
        
        res_provas = supabase.table("modelos_prova").select("id, titulo").order("id", desc=True).execute()
        
        if res_provas.data:
            dic_provas = {p['titulo']: p['id'] for p in res_provas.data}
            prova_escolhida = st.selectbox("Selecione a Avaliação para ver as notas:", list(dic_provas.keys()))
            id_prova_sel = dic_provas[prova_escolhida]
            
            try:
                res_notas = supabase.table("resultados_provas").select("aluno_id, acertou").eq("prova_id", id_prova_sel).execute()
                
                if res_notas.data:
                    df_notas = pd.DataFrame(res_notas.data)
                    df_notas["pontos"] = df_notas["acertou"].astype(int)
                    df_notas_agrupadas = df_notas.groupby("aluno_id")["pontos"].sum().reset_index()
                    
                    lista_ids = [int(i) for i in df_notas_agrupadas["aluno_id"].tolist() if str(i).isdigit()]
                    res_alunos_bd = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", lista_ids).execute()
                    
                    if res_alunos_bd.data:
                        df_alunos = pd.DataFrame(res_alunos_bd.data)
                        df_alunos["id"] = df_alunos["id"].astype(str)
                        df_notas_agrupadas["aluno_id"] = df_notas_agrupadas["aluno_id"].astype(str)
                        
                        df_final = pd.merge(df_alunos, df_notas_agrupadas, left_on="id", right_on="aluno_id")
                        df_final = df_final[["nome", "turma", "pontos"]].sort_values(by="pontos", ascending=False)
                        df_final.columns = ["Nome do Estudante", "Turma", "Total de Acertos"]
                        
                        st.dataframe(df_final, use_container_width=True, hide_index=True)
                    else:
                        st.warning("Alunos não encontrados no banco de dados escolar.")
                else:
                    st.info("Ninguém respondeu esta prova ainda.")
            except Exception as e:
                st.error(f"Erro ao processar notas: {e}")

    except Exception as e:
        st.error(f"Erro geral no Dashboard: {e}")

# --- 6. CADASTRO DE QUESTÕES (MANUAL + IA) ---
elif menu == "📝 Cadastrar Questões":
    st.title("🖊️ Criador de Atv. online do Prof. Lardião")
    
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1: serie_ctx = st.selectbox("Série/Ano", ["1º Ano", "2º Ano", "3º Ano"])
    with col_c2: assunto_ctx = st.text_input("Assunto (ex: Química Orgânica)")
    with col_c3: diff_ctx = st.select_slider("Dificuldade Padrão", options=["Fácil", "Média", "Difícil"])

    with st.expander("🚀 IMPORTADOR FLASH (COLE O JSON DA IA AQUI)", expanded=True):
        st.write("Gere as questões na IA, copie o JSON e cole abaixo:")
        json_input = st.text_area("Área do JSON:", height=250, placeholder='[ { "enunciado": "...", ... } ]')
        
        if st.button("📥 Importar Todas as Questões em Lote"):
            if json_input:
                try:
                    dados_json = json.loads(json_input)
                    if isinstance(dados_json, dict):
                        lista_q = [dados_json]
                    else:
                        lista_q = dados_json
                        
                    for q in lista_q:
                        letra_correta = "B" 
                        for letra, fb in q["justificativas"].items():
                            if any(word in fb.lower() for word in ["parabéns", "correto", "correta", "excelente", "muito bem", "exato", "perfeito"]):
                                letra_correta = letra
                        
                        dados_ia = {
                            "enunciado": q["enunciado"],
                            "alternativas": q["alternativas"],
                            "justificativas": q["justificativas"],
                            "resposta_correta": q.get("resposta_correta", letra_correta),
                            "serie": q.get("serie", serie_ctx),
                            "assunto": q.get("assunto", assunto_ctx if assunto_ctx else "Geral"),
                            "dificuldade": q.get("dificuldade", diff_ctx)
                        }
                        supabase.table("questoes").insert(dados_ia).execute()
                        
                    st.success(f"🔥 {len(lista_q)} questão(ões) importada(s) com sucesso!")
                except Exception as e:
                    st.error(f"Erro no JSON ou na Inserção: {e}")
            else:
                st.warning("Cole o código primeiro!")

    st.divider()

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
                st.success("Questão salva com sucesso!")


# --- 7. BIBLIOTECA DE QUESTÕES ---
elif menu == "📚 Biblioteca de Questões":
    if 'editando_id' not in st.session_state:
        st.session_state.editando_id = None

    # BUSCA ASSUNTOS EXISTENTES PARA PADRONIZAÇÃO
    res_assuntos_db = supabase.table("questoes").select("assunto").execute()
    assuntos_existentes = sorted(list(set([x['assunto'] for x in res_assuntos_db.data if x['assunto']])))

    if st.session_state.editando_id is not None:
        st.title("✏️ Editar e Validar Questão")
        
        if st.button("⬅️ Voltar para a Biblioteca", type="secondary"):
            st.session_state.editando_id = None
            st.rerun()
            
        # Busca a questão incluindo a coluna 'revisada'
        res_q = supabase.table("questoes").select("*").eq("id", st.session_state.editando_id).execute()
        
        if res_q.data:
            q = res_q.data[0]
            
            with st.form(key=f"form_edita_{q['id']}"):
                st.markdown("### ⚙️ Configurações e Validação")
                
                # --- NOVA LÓGICA DE ASSUNTO ---
                st.markdown("🔍 **Classificação do Assunto**")
                c_serie, c_diff = st.columns(2)
                
                with c_serie: 
                    edit_serie = st.selectbox("Série", ["1º Ano", "2º Ano", "3º Ano"], 
                                              index=["1º Ano", "2º Ano", "3º Ano"].index(q.get('serie', "1º Ano")))
                
                with c_diff:
                    edit_diff = st.selectbox("Dificuldade", ["Fácil", "Média", "Difícil"], 
                                             index=["Fácil", "Média", "Difícil"].index(q.get('dificuldade', "Média")))

                st.markdown("<br>", unsafe_allow_html=True)
                c_sel, c_novo = st.columns([1, 1])
                
                with c_sel:
                    # Adicionamos uma opção neutra no topo
                    opcoes_assunto = ["-- SELECIONE UM EXISTENTE --"] + assuntos_existentes
                    
                    # Tenta pré-selecionar o assunto atual da questão se ele já estiver na lista
                    idx_atual = 0
                    if q.get('assunto') in assuntos_existentes:
                        idx_atual = assuntos_existentes.index(q.get('assunto')) + 1
                        
                    assunto_selecionado = st.selectbox(
                        "Assuntos já gravados (Selecione um para padronizar):", 
                        opcoes_assunto, 
                        index=idx_atual
                    )

                with c_novo:
                    # Campo para sobrescrever ou criar um novo
                    assunto_manual = st.text_input(
                        "Ou crie um NOVO nome (Substitui a seleção ao lado):", 
                        value="", 
                        placeholder=f"Atual: {q.get('assunto', '')}"
                    )
                # ------------------------------

                st.divider()
                st.markdown("📝 **Enunciado da Questão**")
                st.caption("Você pode colar imagens diretamente no editor abaixo ou usar o ícone de imagem.")
                edit_enunciado = st_quill(value=q.get('enunciado', ''), html=True, key=f"q_editor_{q['id']}")
                
                st.divider()
                st.markdown("🧠 **Gabarito e Justificativas**")
                
                # --- LÓGICA DE SEGURANÇA PARA O GABARITO ---
                opcoes_gabarito = ["A", "B", "C", "D"]
                # Limpa o dado que vem do banco (remove espaços e põe em maiúsculo)
                resposta_vinda_do_banco = str(q.get('resposta_correta', "A")).strip().upper()

                # Verifica se a resposta é válida, se não for, define o índice como 0 (Alternativa A)
                if resposta_vinda_do_banco in opcoes_gabarito:
                    idx_gabarito = opcoes_gabarito.index(resposta_vinda_do_banco)
                else:
                    idx_gabarito = 0 
                # -------------------------------------------

                edit_gabarito = st.radio("Alternativa Correta:", opcoes_gabarito, 
                                         index=idx_gabarito, horizontal=True)
                
                alts = q.get('alternativas', {})
                justs = q.get('justificativas', {})
                edit_alts = {}
                edit_justs = {}
                
                for letra in ["A", "B", "C", "D"]:
                    ca, cj = st.columns([1, 2])
                    with ca: edit_alts[letra] = st.text_input(f"Texto {letra}", value=alts.get(letra, ""))
                    with cj: edit_justs[letra] = st.text_input(f"Diagnóstico {letra}", value=justs.get(letra, ""))
                
                st.divider()
                # Botão de Salvar que valida a questão
                btn_salvar = st.form_submit_button("✅ SALVAR E MARCAR COMO PRONTA", type="primary", use_container_width=True)
                
                if btn_salvar:
                    # Define a lógica final: prioridade para o que foi digitado manualmente
                    if assunto_manual.strip() != "":
                        assunto_final = assunto_manual.strip()
                    else:
                        # Se não digitou nada, usa o que selecionou no selectbox (se não for a opção neutra)
                        if assunto_selecionado != "-- SELECIONE UM EXISTENTE --":
                            assunto_final = assunto_selecionado
                        else:
                            assunto_final = q.get('assunto', '') # Mantém o original se nada for feito

                    if not assunto_final:
                         st.error("Por favor, defina um assunto para a questão.")
                    else:
                        dados_upd = {
                            "serie": edit_serie, 
                            "assunto": assunto_final, 
                            "resposta_correta": edit_gabarito,
                            "dificuldade": edit_diff, 
                            "enunciado": edit_enunciado,
                            "alternativas": edit_alts, 
                            "justificativas": edit_justs,
                            "revisada": True  # MARCA COMO PRONTA
                        }
                        supabase.table("questoes").update(dados_upd).eq("id", q['id']).execute()
                        st.session_state.editando_id = None
                        st.success("Questão validada e salva na biblioteca!")
                        import time # Garantindo que o time está importado aqui caso não esteja no topo
                        time.sleep(1)
                        st.rerun()

    else:
        st.title("📚 Biblioteca de Questões")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1: f_serie = st.multiselect("Filtrar Série", ["1º Ano", "2º Ano", "3º Ano"])
        with col2: f_assunto = st.multiselect("Filtrar Assunto", assuntos_existentes)
        with col3: f_status = st.multiselect("Status", ["Pronta", "Pendente"], default=["Pendente"])

        query = supabase.table("questoes").select("id, serie, assunto, dificuldade, enunciado, resposta_correta, revisada")
        if f_serie: query = query.in_("serie", f_serie)
        if f_assunto: query = query.in_("assunto", f_assunto)
        
        # Lógica de filtro de status
        data = query.execute().data
        if f_status:
            if "Pronta" in f_status and "Pendente" not in f_status:
                data = [x for x in data if x.get('revisada') == True]
            elif "Pendente" in f_status and "Pronta" not in f_status:
                data = [x for x in data if x.get('revisada') == False or x.get('revisada') is None]

        if data:
            st.write(f"🔍 Encontradas: **{len(data)}** questões")
            st.divider()
            
            import re # Garantindo que o re está importado caso não esteja no topo
            
            # Cabeçalho da Tabela - Adicionada a coluna h_c0 para Seleção
            h_c0, h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([0.3, 0.6, 0.8, 1.2, 4, 0.5, 0.8])
            h_c0.caption("SEL.")
            h_c1.caption("ID")
            h_c2.caption("STATUS")
            h_c3.caption("CLASSIFICAÇÃO")
            h_c4.caption("ENUNCIADO (PRÉVIA)")
            h_c5.caption("GAB.")
            h_c6.caption("AÇÕES")
            
            # Lista para armazenar as questões selecionadas em massa
            questoes_selecionadas = []
            
            for q in data:
                texto_puro = re.sub('<[^<]+>', '', str(q['enunciado']))
                previa = texto_puro[:90] + "..." if len(texto_puro) > 90 else texto_puro
                
                is_revisada = q.get('revisada', False)
                
                with st.container(border=True):
                    # Adicionada a coluna c0 para Seleção
                    c0, c1, c2, c3, c4, c5, c6 = st.columns([0.3, 0.6, 0.8, 1.2, 4, 0.5, 0.8], gap="small")
                    
                    # Checkbox de seleção em massa
                    if c0.checkbox("", key=f"batch_sel_{q['id']}"):
                        questoes_selecionadas.append(q['id'])
                        
                    c1.write(f"#{str(q['id'])[:4]}")
                    
                    # Badge de Status Dinâmico
                    if is_revisada:
                        c2.markdown('<span style="color: #155724; background-color: #d4edda; padding: 4px; border-radius: 4px; font-size: 10px; font-weight: bold;">✅ PRONTA</span>', unsafe_allow_html=True)
                    else:
                        c2.markdown('<span style="color: #856404; background-color: #fff3cd; padding: 4px; border-radius: 4px; font-size: 10px; font-weight: bold;">⚠️ PENDENTE</span>', unsafe_allow_html=True)
                    
                    c3.markdown(f"**{q['serie']}**<br><span style='color:#007bff; font-size:11px;'>{q['assunto'].upper()}</span>", unsafe_allow_html=True)
                    c4.write(previa)
                    c5.markdown(f"**{q['resposta_correta']}**")
                    
                    bc1, bc2 = c6.columns(2)
                    if bc1.button("✏️", key=f"edit_{q['id']}"):
                        st.session_state.editando_id = q['id']
                        st.rerun()
                    if bc2.button("🗑️", key=f"del_{q['id']}"):
                        supabase.table("questoes").delete().eq("id", q['id']).execute()
                        st.rerun()

            # --- LÓGICA DE APROVAÇÃO EM MASSA ---
            if len(questoes_selecionadas) > 0:
                st.divider()
                if st.button(f"✅ Marcar {len(questoes_selecionadas)} questões selecionadas como PRONTAS", type="primary"):
                    with st.spinner("Atualizando questões..."):
                        for q_id in questoes_selecionadas:
                            supabase.table("questoes").update({"revisada": True}).eq("id", q_id).execute()
                    st.success(f"{len(questoes_selecionadas)} questões validadas com sucesso!")
                    import time
                    time.sleep(1)
                    st.rerun()

        else:
            st.info("Nenhuma questão encontrada.")
            
# --- 8. GERADOR DE MODELOS ---
elif menu == "📜 Gerar Modelo de Prova":
    st.title("📜 Publicar Prova para Alunos")
    
    res_q = supabase.table("questoes").select("id, assunto, serie, dificuldade, enunciado, resposta_correta").eq("revisada", True).execute()
    df_q = pd.DataFrame(res_q.data)
    
    if not df_q.empty:
        st.subheader("⚙️ Configurações Gerais")
        with st.container(border=True):
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                tit = st.text_input("Título da Prova", placeholder="Ex: 1º Simulado Bimestral de Química")
            with col_t2:
                ser = st.selectbox("Filtrar questões da Série:", ["1º Ano", "2º Ano", "3º Ano"])
            
            st.write("---")
            st.write("**Regras de Acesso e Tempo**")
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1: data_limite = st.date_input("📅 Data Limite")
            with col_c2: hora_limite = st.time_input("⏰ Hora Limite (Brasília)")
            with col_c3: tempo_duracao = st.number_input("⏳ Duração (Minutos)", min_value=10, max_value=300, value=60, step=10)

            st.write("---")
            st.write("**Pontuação e Sorteio**")
            col_p1, col_p2 = st.columns(2)
            with col_p1: qtd_questoes = st.number_input("🔢 Banco de Questões (Total)", min_value=1, max_value=100, value=10)
            with col_p2:
                valor_questao = st.number_input("⭐ Valor de cada Questão", min_value=0.1, max_value=10.0, value=1.0, step=0.5)
                qtd_sorteio = st.number_input("🎲 Sorteio: Questões por Aluno", min_value=1, max_value=int(qtd_questoes), value=int(qtd_questoes))
        
        st.divider()
        st.subheader("📋 Selecione as Questões")
        
        qs_disp = df_q[df_q['serie'] == ser]
        
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([0.8, 1.2, 5, 0.5, 0.5])
        h_col1.caption("STATUS")
        h_col2.caption("CLASSIFICAÇÃO")
        h_col3.caption("ENUNCIADO (PRÉVIA)")
        h_col4.caption("GAB.")
        h_col5.caption("SEL.")

        questoes_selecionadas = []

        for _, row in qs_disp.iterrows():
            texto_puro = re.sub('<[^<]+>', '', str(row['enunciado']))
            previa = texto_puro[:120] + "..." if len(texto_puro) > 120 else texto_puro
            
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([0.8, 1.2, 5, 0.5, 0.5])
                c1.markdown('<span style="color: #28a745; font-size: 12px; font-weight: bold;">✅ Pronta</span>', unsafe_allow_html=True)
                c2.markdown(f"**{row['serie']}**\n\n<span style='color: #28a745; font-size: 11px; font-weight: bold;'>{row['assunto'].upper()}</span>", unsafe_allow_html=True)
                c3.write(previa)
                with c3.expander("🔍 Ver questão completa"):
                    st.markdown(row['enunciado'], unsafe_allow_html=True)
                c4.markdown(f"### {row['resposta_correta']}")
                escolhida = c5.checkbox("", key=f"sel_{row['id']}")
                if escolhida:
                    questoes_selecionadas.append(row['id'])

        st.divider()
        col_fim1, col_fim2 = st.columns([4, 1])
        
        qtd_selecionada = len(questoes_selecionadas)
        if qtd_selecionada == qtd_questoes:
            col_fim1.success(f"📂 Perfeito! Você selecionou {qtd_selecionada} de {qtd_questoes} questões para o banco da prova.")
        else:
            col_fim1.warning(f"📂 Atenção: Você selecionou {qtd_selecionada} questões. O banco exige {qtd_questoes}.")
        
        if col_fim2.button("🚀 Publicar Prova", type="primary", use_container_width=True):
            if not tit:
                st.error("Erro: Defina um título para a prova.")
            elif qtd_selecionada != qtd_questoes:
                st.error(f"Erro: Selecione exatamente {qtd_questoes} questões.")
            else:
                with st.spinner("Publicando..."):
                    data_hora_combinada = datetime.combine(data_limite, hora_limite)
                    data_hora_iso = data_hora_combinada.isoformat()

                    supabase.table("modelos_prova").insert({
                        "titulo": tit, "serie": ser, "questoes_ids": questoes_selecionadas, 
                        "ativa": True, "data_limite": data_hora_iso, "tempo_duracao": tempo_duracao,
                        "qtd_questoes": qtd_questoes, "qtd_sorteio": qtd_sorteio, "valor_questao": valor_questao
                    }).execute()
                
                st.success(f"Prova '{tit}' publicada com sucesso!")
                st.balloons()
                time.sleep(2)
                st.rerun()
    else:
        st.warning("Nenhuma questão cadastrada.")


# --- 9. GERENCIAMENTO DE PROVAS ELABORADAS ---
elif menu == "📂 Provas Elaboradas":
    st.title("📂 Gerenciar Provas Elaboradas")
    
    # Configuração de fuso horário para comparação de prazos
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    
    res_provas = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_provas.data:
        st.write(f"🔍 Total de avaliações cadastradas: **{len(res_provas.data)}**")
        st.divider()
        
        for prova in res_provas.data:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 1.5, 2, 1.8], gap="small")
                
                # --- Tratamento de Datas ---
                status_texto = "🟢 ATIVA" if prova.get('ativa') else "🔴 INATIVA"
                dt_limite_raw = prova.get('data_limite')
                dt_limite_formatada = "Sem limite"
                prazo_encerrado = False

                if dt_limite_raw:
                    # Converte a data do banco para objeto datetime com fuso horário
                    dt_obj = datetime.fromisoformat(dt_limite_raw.replace("Z", "+00:00")).astimezone(fuso)
                    dt_limite_formatada = dt_obj.strftime('%d/%m/%Y às %H:%M')
                    prazo_encerrado = agora > dt_obj

                c1.markdown(f"### {prova.get('titulo', 'Sem título')}")
                c1.markdown(f"**Série:** {prova.get('serie', 'Geral')} | **Prazo:** {dt_limite_formatada}")
                
                c2.markdown(f"**Status:**")
                c2.markdown(f"*{status_texto}*")
                
                # Formato da Prova
                q_total = prova.get('qtd_questoes', 0)
                q_sorteio = prova.get('qtd_sorteio', q_total)
                c3.markdown("**Formato:**")
                c3.caption(f"Banco: {q_total} | Sorteio: {q_sorteio}")
                
                serie_atual = prova.get('serie')
                prova_id = prova.get('id')
                
                # --- Cálculo de Engajamento ---
                try:
                    prefixo_turma = str(serie_atual).replace(" Ano", "").strip()
                    res_alunos = supabase_alunos.table("alunos").select("id").ilike("turma", f"{prefixo_turma}%").execute()
                    total_alunos = len(res_alunos.data) if res_alunos.data else 0
                    
                    res_respostas = supabase.table("resultados_provas").select("aluno_id").eq("prova_id", prova_id).execute()
                    alunos_que_fizeram = len(set([r['aluno_id'] for r in res_respostas.data])) if res_respostas.data else 0
                    
                    porcentagem = (alunos_que_fizeram / total_alunos * 100) if total_alunos > 0 else 0.0
                    
                    c4.markdown("**Engajamento:**")
                    c4.markdown(f"**{alunos_que_fizeram} / {total_alunos}** alunos")
                    cor_perc = "green" if porcentagem >= 70 else ("orange" if porcentagem >= 40 else "red")
                    c4.markdown(f"<span style='color:{cor_perc}; font-weight:bold;'>{porcentagem:.1f}% concluído</span>", unsafe_allow_html=True)
                except:
                    c4.markdown("**Engajamento:**")
                    c4.caption("Erro ao carregar dados.")
                
                # --- COLUNA 5: AÇÕES ---
                with c5:
                    # Botão 1: Alternar Status
                    texto_btn_status = "⏸️ Desativar" if prova.get('ativa') else "▶️ Ativar"
                    if st.button(texto_btn_status, key=f"status_{prova_id}", use_container_width=True):
                        novo_status = not prova.get('ativa')
                        supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova_id).execute()
                        st.rerun()
                    
                    # Botão 2: LIBERAR NOTAS (Novo!)
                    # Só aparece se a prova ainda não expirou
                    if not prazo_encerrado and dt_limite_raw:
                        if st.button("🔓 Liberar Notas", key=f"liberar_{prova_id}", use_container_width=True, help="Encerra o prazo agora para mostrar as notas aos alunos"):
                            # Define o prazo para "agora", o que libera a visualização no app do aluno
                            supabase.table("modelos_prova").update({"data_limite": agora.isoformat()}).eq("id", prova_id).execute()
                            st.toast("Notas liberadas para os alunos!")
                            time.sleep(1)
                            st.rerun()

                    # Botão 3: Excluir (Corrigido para evitar erro de FK)
                    if st.button("🗑️ Excluir", key=f"del_{prova_id}", type="primary", use_container_width=True):
                        try:
                            # 1. Apaga primeiro as referências (filhos)
                            supabase.table("resultados_provas").delete().eq("prova_id", prova_id).execute()
                            # 2. Apaga o modelo (pai)
                            supabase.table("modelos_prova").delete().eq("id", prova_id).execute()
                            st.success("Prova excluída!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")
                            
    else:
        st.info("📌 Nenhuma prova foi elaborada ainda.")


# --- 10. LISTA DE MATRÍCULAS PARA IMPRESSÃO (COM PDF) ---
elif menu == "🖨️ Lista de Matrículas":
    st.title("🖨️ Impressão de Matrículas por Turma")
    
    try:
        res_turmas = supabase_alunos.table("alunos").select("turma").execute()
        if res_turmas.data:
            lista_turmas = sorted(list(set([t['turma'] for t in res_turmas.data if t['turma']])))
        else:
            lista_turmas = ["3º A", "3º B", "3º C"] 
    except:
        lista_turmas = ["Erro ao carregar turmas"]

    turma_selecionada = st.selectbox("Selecione a Turma:", lista_turmas)

    if st.button("📄 Gerar Lista", type="primary"):
        with st.spinner("Buscando alunos..."):
            try:
                res_alunos = supabase_alunos.from_("alunos").select("nome, numero_matricula").eq("turma", turma_selecionada).order("nome").execute()
                
                if res_alunos.data:
                    dados_tabela = []
                    for index, aluno in enumerate(res_alunos.data, start=1):
                        dados_tabela.append({
                            "Nº ORDEM": f"{index:02d}", 
                            "Nº MATRÍCULA": str(aluno.get('numero_matricula', 'S/N')),
                            "NOME DO ESTUDANTE": str(aluno.get('nome', '')).upper()
                        })
                    
                    df_lista = pd.DataFrame(dados_tabela)
                    
                    pdf = FPDF()
                    pdf.add_page()
                    
                    pdf.set_font("Arial", 'B', 14)
                    pdf.cell(0, 10, f"ESCOLA EREMPAM - LISTA DE FREQUENCIA", ln=True, align='C')
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"Turma: {turma_selecionada.upper()}", ln=True, align='C')
                    pdf.ln(5)
                    
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(15, 8, "N", border=1, align='C')
                    pdf.cell(35, 8, "MATRICULA", border=1, align='C')
                    pdf.cell(140, 8, "NOME DO ESTUDANTE", border=1, align='C')
                    pdf.ln()
                    
                    pdf.set_font("Arial", '', 10)
                    for _, row in df_lista.iterrows():
                        pdf.cell(15, 8, str(row["Nº ORDEM"]), border=1, align='C')
                        pdf.cell(35, 8, str(row["Nº MATRÍCULA"]), border=1, align='C')
                        
                        nome_aluno = str(row["NOME DO ESTUDANTE"])
                        nome_seguro = nome_aluno.encode('latin-1', 'replace').decode('latin-1')
                        
                        pdf.cell(140, 8, f" {nome_seguro}", border=1, align='L')
                        pdf.ln()
                    
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    
                    st.success(f"✅ Lista da turma {turma_selecionada} gerada com {len(df_lista)} alunos!")
                    
                    st.download_button(
                        label="📥 Baixar Documento em PDF",
                        data=pdf_bytes,
                        file_name=f"Frequencia_{turma_selecionada}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    with st.expander("👀 Ver prévia na tela"):
                        st.table(df_lista.set_index("Nº ORDEM"))
                        
                else:
                    st.warning(f"Nenhum aluno encontrado na turma {turma_selecionada}.")
            except Exception as e:
                st.error(f"Erro na geração: {e}")