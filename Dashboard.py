import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json
import pytz 
from fpdf import FPDF
import base64
import re
from datetime import datetime
import time
import unicodedata
import io

# --- PROTEÇÃO PARA O WHATSAPP ---
try:
    import pywhatkit as kit
    WHATSAPP_LOCAL = True
except ImportError:
    WHATSAPP_LOCAL = False
              
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE ---
URL_P = st.secrets["SUPABASE_URL_PROVAS"]
KEY_P = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL_P, KEY_P)

URL_A = st.secrets["SUPABASE_URL_ALUNOS"]
KEY_A = st.secrets["SUPABASE_KEY_ALUNOS"]
supabase_alunos = create_client(URL_A, KEY_A)

# --- 3. SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = True

# --- 4. MENU LATERAL ---
from streamlit_option_menu import option_menu

# --- 4. MENU LATERAL ---
with st.sidebar:
    st.title("🎮 Painel do Professor")
    
    menu = option_menu(
        menu_title="Navegação",  
        options=[
            "Análise de Dados", 
            "Cadastrar Questões", 
            "Biblioteca de Questões", 
            "Gerar Modelo de Prova",
            "Provas Elaboradas",
            "Lista de Matrículas",
            "Central de Avisos",
            "Diagnósticos IA",
            "Boletim Final SIEPE"
        ],
        icons=[
            "bar-chart-fill",    # Análise de Dados
            "pencil-square",     # Cadastrar Questões
            "book",              # Biblioteca de Questões
            "file-earmark-text", # Gerar Modelo de Prova
            "folder-check",      # Provas Elaboradas
            "people-fill",       # Lista de Matrículas
            "bell-fill",         # Central de Avisos
            "robot",             # Diagnósticos IA
            "bank"               # Boletim Final SIEPE
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#ff9800", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#333333"},
            "nav-link-selected": {"background-color": "#4CAF50"}, 
        }
    )

st.sidebar.divider()
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state.autenticado = False
    st.rerun()

# --- 5. LÓGICA DO DASHBOARD (NOTAS E RELATÓRIO EXCEL) ---
if menu == "📊 Análise de Dados":
    st.title("📊 Análise de Dados e Notas")
    
    # --- PARTE 1: GRÁFICOS GERAIS ---
    try:
        res_raw = supabase.table("resultados_provas").select("aluno_id, questao_id, acertou").execute()
        res_q_base = supabase.table("questoes").select("id, assunto").execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()
        
        if res_raw.data and res_alunos_base.data:
            df_raw = pd.DataFrame(res_raw.data)
            df_q = pd.DataFrame(res_q_base.data)
            df_alunos_base = pd.DataFrame(res_alunos_base.data)
            
            df_raw['aluno_id'] = df_raw['aluno_id'].astype(str)
            df_alunos_base['id'] = df_alunos_base['id'].astype(str)
            
            df_master = pd.merge(df_raw, df_alunos_base, left_on="aluno_id", right_on="id")
            
            st.subheader("🎯 Visão Geral de Engajamento")
            col_k1, col_k2 = st.columns(2)
            col_k1.metric("Total de Respostas", len(df_raw))
            col_k2.metric("Alunos Participantes", df_raw['aluno_id'].nunique())
    except:
        st.info("Aguardando dados de respostas...")

    st.divider()

    # --- PARTE 2: NOTAS INDIVIDUAIS E EXCEL (O QUE VOCÊ PEDIU) ---
    st.subheader("🏆 Desempenho por Aluno e Relatórios")
    
    res_p_modelos = supabase.table("modelos_prova").select("id, titulo, valor_questao, questoes_ids").order("id", desc=True).execute()
    
    if res_p_modelos.data:
        provas_dict = {p['titulo']: p for p in res_p_modelos.data}
        prova_nome = st.selectbox("Selecione a Prova para detalhar:", list(provas_dict.keys()))
        
        prova_obj = provas_dict[prova_nome]
        id_prova = prova_obj['id']
        valor_q = float(prova_obj.get('valor_questao', 1.0))
        ids_questoes_prova = prova_obj.get('questoes_ids', []) # Lista de IDs das questões desta prova

        # Buscar resultados desta prova
        res_res = supabase.table("resultados_provas").select("*").eq("prova_id", id_prova).execute()
        
        if res_res.data:
            df_res = pd.DataFrame(res_res.data)
            df_res['aluno_id'] = df_res['aluno_id'].astype(str)
            
            # Cálculo de acertos
            df_res['pontos'] = df_res['acertou'].apply(lambda x: 1 if x is True else 0)
            
            # Agrupar por aluno
            df_notas = df_res.groupby('aluno_id').agg(
                total_acertos=('pontos', 'sum')
            ).reset_index()
            
            # CÁLCULO DA NOTA (Acertos * Valor da Questão)
            df_notas['nota_final'] = df_notas['total_acertos'] * valor_q
            
            # Buscar Nomes dos Alunos
            ids_alunos = df_notas['aluno_id'].tolist()
            res_al = supabase_alunos.table("alunos").select("id, nome, turma").in_("id", ids_alunos).execute()
            df_alunos_nomes = pd.DataFrame(res_al.data)
            df_alunos_nomes['id'] = df_alunos_nomes['id'].astype(str)
            
            # Merge Final para a Tabela da Tela
            df_tela = pd.merge(df_alunos_nomes, df_notas, left_on="id", right_on="aluno_id")
            df_tela = df_tela[["nome", "turma", "total_acertos", "nota_final"]].sort_values(by="nome")
            
            # Exibição na Tela (Conforme seu Print 2)
            st.dataframe(
                df_tela.rename(columns={
                    "nome": "Nome do Estudante",
                    "turma": "Turma",
                    "total_acertos": "Total de Acertos",
                    "nota_final": "Nota Alcançada"
                }), 
                use_container_width=True, 
                hide_index=True
            )

            # --- BOTÃO GERAR RELATÓRIO XLSX (ALTO NÍVEL) ---
            st.write("### 📂 Exportação Avançada")
            if st.button("📊 Gerar Relatório .XLSX (Por Turma + Pares C/M)"):
                with st.spinner("Construindo matriz de respostas..."):
                    # 1. Buscar gabaritos das questões
                    res_gab = supabase.table("questoes").select("id, resposta_correta").in_("id", ids_questoes_prova).execute()
                    dict_gabarito = {str(q['id']): q['resposta_correta'] for q in res_gab.data}

                    output = io.BytesIO()
                    # Usando XlsxWriter como engine para múltiplas abas
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        turmas = sorted(df_tela['turma'].unique())
                        
                        for turma in turmas:
                            df_turma = df_tela[df_tela['turma'] == turma].copy()
                            alunos_turma_ids = df_alunos_nomes[df_alunos_nomes['turma'] == turma]['id'].tolist()
                            
                            rows_relatorio = []
                            for _, row_aluno in df_turma.iterrows():
                                nome_al = row_aluno['nome']
                                al_id = df_alunos_nomes[df_alunos_nomes['nome'] == nome_al]['id'].values[0]
                                
                                # Início da linha: Nome, Turma, Acertos, Nota
                                dados_linha = {
                                    "Nome": nome_al,
                                    "Total Acertos": row_aluno['total_acertos'],
                                    "Nota Final": round(row_aluno['nota_final'], 2)
                                }
                                
                                # Adicionar pares (C) e (M) para cada questão da prova
                                for i, q_id in enumerate(ids_questoes_prova, 1):
                                    gab = dict_gabarito.get(str(q_id), "?")
                                    # O que o aluno marcou nessa questão específica
                                    resp_al_row = df_res[(df_res['aluno_id'] == str(al_id)) & (df_res['questao_id'] == q_id)]
                                    marcou = resp_al_row['resposta_aluno'].values[0] if not resp_al_row.empty else "-"
                                    
                                    dados_linha[f"Q{i} (C)"] = gab
                                    dados_linha[f"Q{i} (M)"] = marcou
                                
                                rows_relatorio.append(dados_linha)
                            
                            df_excel_final = pd.DataFrame(rows_relatorio).sort_values(by="Nome")
                            df_excel_final.to_excel(writer, sheet_name=f"Turma {turma}", index=False)
                    
                    st.download_button(
                        label="📥 Baixar Relatório Excel Completo",
                        data=output.getvalue(),
                        file_name=f"Relatorio_{prova_nome}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Relatório gerado com sucesso!")

        else:
            st.info("Ainda não há respostas para esta avaliação.")

# --- 6. CADASTRO DE QUESTÕES (MANUAL + IA) ---
elif menu == "Cadastrar Questões":
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
elif menu == "Biblioteca de Questões":
    if 'editando_id' not in st.session_state:
        st.session_state.editando_id = None

    # BUSCA ASSUNTOS EXISTENTES PARA PADRONIZAÇÃO
    res_assuntos_db = supabase.table("questoes").select("assunto").execute()
    assuntos_existentes = sorted(list(set([x['assunto'] for x in res_assuntos_db.data if x.get('assunto')])))

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
                
                # --- LÓGICA DE ASSUNTO ---
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
                    opcoes_assunto = ["-- SELECIONE UM EXISTENTE --"] + assuntos_existentes
                    idx_atual = 0
                    if q.get('assunto') in assuntos_existentes:
                        idx_atual = assuntos_existentes.index(q.get('assunto')) + 1
                        
                    assunto_selecionado = st.selectbox(
                        "Assuntos já gravados (Selecione um para padronizar):", 
                        opcoes_assunto, 
                        index=idx_atual
                    )

                with c_novo:
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
                resposta_vinda_do_banco = str(q.get('resposta_correta', "A")).strip().upper()

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
                
                # --- LÓGICA CORRIGIDA: SALVAR EDIÇÕES DA QUESTÃO ---
                btn_salvar = st.form_submit_button("✅ SALVAR E MARCAR COMO PRONTA", type="primary", use_container_width=True)
                
                if btn_salvar:
                    # Verifica se usou o campo manual ou a caixa de seleção para o assunto
                    assunto_final = assunto_manual.strip() if assunto_manual.strip() != "" else assunto_selecionado
                    if assunto_final == "-- SELECIONE UM EXISTENTE --":
                        assunto_final = q.get('assunto', 'Geral')

                    with st.spinner("Atualizando questão..."):
                        dados_upd_questao = {
                            "serie": edit_serie,
                            "dificuldade": edit_diff,
                            "assunto": assunto_final,
                            "enunciado": edit_enunciado,
                            "resposta_correta": edit_gabarito,
                            "alternativas": edit_alts,
                            "justificativas": edit_justs,
                            "revisada": True
                        }
                        try:
                            supabase.table("questoes").update(dados_upd_questao).eq("id", q['id']).execute()
                            st.session_state.editando_id = None
                            st.success("✅ Questão atualizada e validada com sucesso!")
                            time.sleep(1) 
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao salvar questão: {e}")

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
            
            # Cabeçalho da Tabela
            h_c0, h_c1, h_c2, h_c3, h_c4, h_c5, h_c6 = st.columns([0.3, 0.6, 0.8, 1.2, 4, 0.5, 0.8])
            h_c0.caption("SEL.")
            h_c1.caption("ID")
            h_c2.caption("STATUS")
            h_c3.caption("CLASSIFICAÇÃO")
            h_c4.caption("ENUNCIADO (PRÉVIA)")
            h_c5.caption("GAB.")
            h_c6.caption("AÇÕES")
            
            questoes_selecionadas_bib = []
            
            for q in data:
                texto_puro = re.sub('<[^<]+>', '', str(q['enunciado']))
                previa = texto_puro[:90] + "..." if len(texto_puro) > 90 else texto_puro
                is_revisada = q.get('revisada', False)
                
                with st.container(border=True):
                    c0, c1, c2, c3, c4, c5, c6 = st.columns([0.3, 0.6, 0.8, 1.2, 4, 0.5, 0.8], gap="small")
                    
                    if c0.checkbox("", key=f"batch_sel_{q['id']}"):
                        questoes_selecionadas_bib.append(q['id'])
                        
                    c1.write(f"#{str(q['id'])[:4]}")
                    
                    if is_revisada:
                        c2.markdown('<span style="color: #155724; background-color: #d4edda; padding: 4px; border-radius: 4px; font-size: 10px; font-weight: bold;">✅ PRONTA</span>', unsafe_allow_html=True)
                    else:
                        c2.markdown('<span style="color: #856404; background-color: #fff3cd; padding: 4px; border-radius: 4px; font-size: 10px; font-weight: bold;">⚠️ PENDENTE</span>', unsafe_allow_html=True)
                    
                    c3.markdown(f"**{q['serie']}**<br><span style='color:#007bff; font-size:11px;'>{str(q.get('assunto', 'Geral')).upper()}</span>", unsafe_allow_html=True)
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
            if len(questoes_selecionadas_bib) > 0:
                st.divider()
                if st.button(f"✅ Marcar {len(questoes_selecionadas_bib)} questões selecionadas como PRONTAS", type="primary"):
                    with st.spinner("Atualizando questões..."):
                        for q_id in questoes_selecionadas_bib:
                            supabase.table("questoes").update({"revisada": True}).eq("id", q_id).execute()
                    st.success(f"{len(questoes_selecionadas_bib)} questões validadas com sucesso!")
                    time.sleep(1)
                    st.rerun()

        else:
            st.info("Nenhuma questão encontrada.")
            
# --- 8. GERADOR DE MODELOS ---
elif menu == "Gerar Modelo de Prova":
    st.title("📜 Publicar Prova para Alunos")
    fuso = pytz.timezone('America/Recife')
    
    res_q = supabase.table("questoes").select("id, assunto, serie, dificuldade, enunciado, resposta_correta").eq("revisada", True).execute()
    df_q = pd.DataFrame(res_q.data)
    
    if not df_q.empty:
        st.subheader("⚙️ Configurações Gerais")
        with st.container(border=True):
            col_t1, col_t2 = st.columns([2, 1])
            with col_t1:
                tit = st.text_input("Título da Prova", placeholder="Ex: 1º Simulado")
            with col_t2:
                ser = st.selectbox("Série:", ["1º Ano", "2º Ano", "3º Ano"])
            
            st.write("---")
            c_dat, c_hor, c_dur = st.columns([1.5, 1.5, 1])
            with c_dat: 
                d_ini_raw = st.date_input("🟢 Data Início", key="di_8")
                d_fim_raw = st.date_input("🔴 Data Limite", key="df_8")
                
                # Proteção garantida contra tuplas/listas no date_input
                data_inicio = d_ini_raw[0] if isinstance(d_ini_raw, (list, tuple)) and len(d_ini_raw) > 0 else (d_ini_raw if not isinstance(d_ini_raw, (list, tuple)) else datetime.today().date())
                data_limite = d_fim_raw[0] if isinstance(d_fim_raw, (list, tuple)) and len(d_fim_raw) > 0 else (d_fim_raw if not isinstance(d_fim_raw, (list, tuple)) else datetime.today().date())

            with c_hor: 
                hora_inicio = st.time_input("🟢 Hora Início", key="hi_8")
                hora_limite = st.time_input("🔴 Hora Limite", key="hf_8")
            with c_dur: 
                tempo_duracao = st.number_input("⏳ Duração (Min)", min_value=10, value=60)

            st.write("---")
            col_p1, col_p2 = st.columns(2)
            with col_p1: qtd_questoes = st.number_input("🔢 Banco de Questões", min_value=1, value=10)
            with col_p2:
                valor_questao = st.number_input("⭐ Valor/Questão", min_value=0.1, value=1.0)
                qtd_sorteio = st.number_input("🎲 Sorteio", min_value=1, max_value=int(qtd_questoes), value=int(qtd_questoes))
        
        # Seleção de Questões
        questoes_selecionadas_prova = []
        qs_disp = df_q[df_q['serie'] == ser]
        
        if qs_disp.empty:
            st.warning(f"Nenhuma questão REVISADA e PRONTA encontrada para o {ser}.")
        else:
            for _, row in qs_disp.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([0.8, 1.2, 5, 0.5, 0.5])
                    texto_q = re.sub('<[^<]+>', '', str(row['enunciado']))
                    c3.write(texto_q[:100] + ("..." if len(texto_q) > 100 else ""))
                    
                    if c5.checkbox("", key=f"sel_prova_{row['id']}"):
                        questoes_selecionadas_prova.append(row['id'])

            if st.button("🚀 Publicar Prova", type="primary"):
                if len(questoes_selecionadas_prova) != qtd_questoes:
                    st.error(f"Você escolheu {len(questoes_selecionadas_prova)} questões, mas o Banco de Questões exige {qtd_questoes}. Ajuste o número ou a seleção.")
                elif not tit:
                    st.error("O Título da prova não pode ficar em branco.")
                else:
                    with st.spinner("Publicando prova..."):
                        aware_inicio = fuso.localize(datetime.combine(data_inicio, hora_inicio))
                        aware_limite = fuso.localize(datetime.combine(data_limite, hora_limite))
                        
                        try:
                            supabase.table("modelos_prova").insert({
                                "titulo": tit, 
                                "serie": ser, 
                                "questoes_ids": questoes_selecionadas_prova, 
                                "ativa": True, 
                                "data_inicio": aware_inicio.isoformat(), 
                                "data_limite": aware_limite.isoformat(), 
                                "tempo_duracao": tempo_duracao,
                                "qtd_questoes": qtd_questoes, 
                                "qtd_sorteio": qtd_sorteio, 
                                "valor_questao": valor_questao
                            }).execute()
                            st.success("🎉 Prova publicada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao publicar a prova: {e}")
    else:
        st.info("⚠️ Nenhuma questão cadastrada ou revisada na biblioteca. Vá em 'Biblioteca de Questões' e valide algumas antes de gerar a prova.")

# --- 9. GERENCIAMENTO DE PROVAS ELABORADAS ---
elif menu == "Provas Elaboradas":
    if 'editando_prova_id' not in st.session_state:
        st.session_state.editando_prova_id = None

    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)

    # --- TELA DE EDIÇÃO DE PROVA (COM A TRAVA DE SEGURANÇA) ---
    if st.session_state.editando_prova_id is not None:
        st.title("✏️ Editar Configurações da Prova")
        
        if st.button("⬅️ Voltar para Gerenciamento", type="secondary"):
            st.session_state.editando_prova_id = None
            st.rerun()
            
        res_p = supabase.table("modelos_prova").select("*").eq("id", st.session_state.editando_prova_id).execute()
        
        if res_p.data:
            p = res_p.data[0]
            
            # --- Tratamento Data LIMITE ---
            dt_limite_raw = p.get('data_limite')
            if dt_limite_raw:
                dt_limite_obj = datetime.fromisoformat(dt_limite_raw.replace("Z", "+00:00")).astimezone(fuso)
                data_limite_atual = dt_limite_obj.date()
                hora_limite_atual = dt_limite_obj.time()
            else:
                data_limite_atual = datetime.today().date()
                hora_limite_atual = datetime.now().time()

            # --- Tratamento Data INÍCIO ---
            dt_inicio_raw = p.get('data_inicio')
            if dt_inicio_raw:
                dt_inicio_obj = datetime.fromisoformat(dt_inicio_raw.replace("Z", "+00:00")).astimezone(fuso)
                data_inicio_atual = dt_inicio_obj.date()
                hora_inicio_atual = dt_inicio_obj.time()
            else:
                data_inicio_atual = datetime.today().date()
                hora_inicio_atual = datetime.now().time()
            
            with st.form(key=f"form_edita_prova_{p['id']}"):
                st.subheader("⚙️ Configurações Gerais")
                with st.container(border=True):
                    col_t1, col_t2 = st.columns([2, 1])
                    with col_t1:
                        tit = st.text_input("Título da Prova", value=p.get('titulo', ''))
                    with col_t2:
                        idx_serie = ["1º Ano", "2º Ano", "3º Ano"].index(p.get('serie', "1º Ano")) if p.get('serie') in ["1º Ano", "2º Ano", "3º Ano"] else 0
                        ser = st.selectbox("Filtrar questões da Série:", ["1º Ano", "2º Ano", "3º Ano"], index=idx_serie)
                    
                    st.write("---")
                    st.write("**Regras de Acesso e Tempo**")
                    c_dat, c_hor, c_dur = st.columns([1.5, 1.5, 1])
                    
                    with c_dat: 
                        # Captura os valores brutos do calendário com a CHAVE ÚNICA para evitar cache de alertas
                        raw_inicio = st.date_input("🟢 Data Início", value=data_inicio_atual, key=f"di_edit_{p['id']}")
                        raw_limite = st.date_input("🔴 Data Limite", value=data_limite_atual, key=f"df_edit_{p['id']}")
                        
                        # TRAVA CONTRA ALERTAS AMARELOS (Extrai a data se vier como lista/tupla)
                        data_inicio = raw_inicio[0] if isinstance(raw_inicio, (list, tuple)) else raw_inicio
                        data_limite = raw_limite[0] if isinstance(raw_limite, (list, tuple)) else raw_limite

                    with c_hor: 
                        hora_inicio = st.time_input("🟢 Hora Início", value=hora_inicio_atual, key=f"hi_edit_{p['id']}")
                        hora_limite = st.time_input("🔴 Hora Limite", value=hora_limite_atual, key=f"hf_edit_{p['id']}")
                    with c_dur: 
                        tempo_duracao = st.number_input("⏳ Duração (Minutos)", min_value=10, max_value=300, value=p.get('tempo_duracao', 60), step=10)

                    st.write("---")
                    st.write("**Pontuação e Sorteio**")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1: qtd_questoes = st.number_input("🔢 Banco de Questões (Total)", min_value=1, max_value=100, value=p.get('qtd_questoes', 10))
                    with col_p2:
                        valor_questao = st.number_input("⭐ Valor de cada Questão", min_value=0.1, max_value=10.0, value=float(p.get('valor_questao', 1.0)), step=0.5)
                        qtd_sorteio = st.number_input("🎲 Sorteio: Questões por Aluno", min_value=1, max_value=int(qtd_questoes), value=p.get('qtd_sorteio', 10))
                
                st.info("💡 Nota: Alterar a Série ou o Total do Banco exigirá que você re-selecione as questões no banco no futuro.")
                
                btn_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True)
                
                if btn_salvar:
                    if not tit:
                        st.error("Erro: Defina um título para a prova.")
                    else:
                        with st.spinner("Atualizando prova..."):
                            naive_inicio = datetime.combine(data_inicio, hora_inicio)
                            naive_limite = datetime.combine(data_limite, hora_limite)

                            aware_inicio = fuso.localize(naive_inicio)
                            aware_limite = fuso.localize(naive_limite)

                            dados_upd = {
                                "titulo": tit, 
                                "serie": ser, 
                                "data_inicio": aware_inicio.isoformat(), 
                                "data_limite": aware_limite.isoformat(), 
                                "tempo_duracao": tempo_duracao,
                                "qtd_questoes": qtd_questoes, 
                                "qtd_sorteio": qtd_sorteio, 
                                "valor_questao": valor_questao
                            }
                            supabase.table("modelos_prova").update(dados_upd).eq("id", p['id']).execute()
                        
                        st.session_state.editando_prova_id = None
                        st.success("Configurações da prova atualizadas!")
                        time.sleep(1)
                        st.rerun()

    # --- TELA DE LISTAGEM DE PROVAS (COM O DESIGN COMPLETO RESTAURADO) ---
    else:
        st.title("📂 Gerenciar Provas Elaboradas")
        
        res_provas = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
        
        if res_provas.data:
            st.write(f"🔍 Total de avaliações cadastradas: **{len(res_provas.data)}**")
            st.divider()
            
            for prova in res_provas.data:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 1.5, 2, 1.8], gap="small")
                    
                    # --- Tratamento de Datas e Status Inteligente ---
                    dt_inicio_raw = prova.get('data_inicio')
                    dt_limite_raw = prova.get('data_limite')
                    
                    dt_inicio_formatada = "Imediato"
                    dt_limite_formatada = "Sem limite"
                    prazo_encerrado = False
                    
                    dt_ini_obj = None
                    dt_fim_obj = None

                    if dt_inicio_raw:
                        dt_ini_obj = datetime.fromisoformat(dt_inicio_raw.replace("Z", "+00:00")).astimezone(fuso)
                        dt_inicio_formatada = dt_ini_obj.strftime('%d/%m às %H:%M')
                        
                    if dt_limite_raw:
                        dt_fim_obj = datetime.fromisoformat(dt_limite_raw.replace("Z", "+00:00")).astimezone(fuso)
                        dt_limite_formatada = dt_fim_obj.strftime('%d/%m às %H:%M')
                        prazo_encerrado = agora > dt_fim_obj

                    # Define a cor e o texto do status dinamicamente
                    if not prova.get('ativa'):
                        status_texto = "🔴 INATIVA"
                        cor_status = "#dc3545" # Vermelho
                    elif dt_ini_obj and agora < dt_ini_obj:
                        status_texto = "🟡 AGENDADA"
                        cor_status = "#d39e00" # Amarelo
                    elif dt_fim_obj and agora > dt_fim_obj:
                        status_texto = "🔴 ENCERRADA"
                        cor_status = "#dc3545" # Vermelho
                    else:
                        status_texto = "🟢 ATIVA"
                        cor_status = "#28a745" # Verde

                    c1.markdown(f"### {prova.get('titulo', 'Sem título')}")
                    c1.markdown(f"**De:** {dt_inicio_formatada} | **Até:** {dt_limite_formatada}")
                    
                    c2.markdown(f"**Status:**")
                    c2.markdown(f"<span style='color:{cor_status}; font-weight:bold;'>{status_texto}</span>", unsafe_allow_html=True)
                    
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
                    
            # --- COLUNA 5: AÇÕES (VERSÃO ATUALIZADA) ---
                    with c5:
                        # 1. Botão Editar
                        if st.button("✏️ Editar", key=f"edit_prova_{prova_id}", use_container_width=True):
                            st.session_state.editando_prova_id = prova_id
                            st.rerun()

                        # 2. Botão Ativar/Desativar Prova
                        texto_btn_status = "⏸️ Desativar" if prova.get('ativa') else "▶️ Ativar"
                        if st.button(texto_btn_status, key=f"status_{prova_id}", use_container_width=True):
                            novo_status = not prova.get('ativa')
                            supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova_id).execute()
                            st.rerun()
                        
                        # 3. NOVO: Controle de Visibilidade das Notas (O Cadeado)
                        notas_liberadas = prova.get('notas_liberadas', False)
                        label_notas = "🔒 Esconder Notas" if notas_liberadas else "🔓 Liberar Notas"
                        
                        if st.button(label_notas, key=f"lib_btn_{prova_id}", use_container_width=True):
                            nova_visibilidade = not notas_liberadas
                            supabase.table("modelos_prova").update({"notas_liberadas": nova_visibilidade}).eq("id", prova_id).execute()
                            
                            msg = "Notas LIBERADAS para os alunos!" if nova_visibilidade else "Notas ESCONDIDAS dos alunos!"
                            st.toast(msg)
                            time.sleep(1)
                            st.rerun()

                        # 4. Botão Excluir
                        if st.button("🗑️ Excluir", key=f"del_{prova_id}", type="primary", use_container_width=True):
                            try:
                                supabase.table("resultados_provas").delete().eq("prova_id", prova_id).execute()
                                supabase.table("modelos_prova").delete().eq("id", prova_id).execute()
                                st.success("Prova excluída!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")      

# --- 10. LISTA DE MATRÍCULAS PARA IMPRESSÃO (COM PDF CORRI
    if 'editando_prova_id' not in st.session_state:
        st.session_state.editando_prova_id = None

    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)

    # --- TELA DE EDIÇÃO DE PROVA (COM A TRAVA DE SEGURANÇA) ---
    if st.session_state.editando_prova_id is not None:
        st.title("✏️ Editar Configurações da Prova")
        
        if st.button("⬅️ Voltar para Gerenciamento", type="secondary"):
            st.session_state.editando_prova_id = None
            st.rerun()
            
        res_p = supabase.table("modelos_prova").select("*").eq("id", st.session_state.editando_prova_id).execute()
        
        if res_p.data:
            p = res_p.data[0]
            
            # --- Tratamento Data LIMITE ---
            dt_limite_raw = p.get('data_limite')
            if dt_limite_raw:
                dt_limite_obj = datetime.fromisoformat(dt_limite_raw.replace("Z", "+00:00")).astimezone(fuso)
                data_limite_atual = dt_limite_obj.date()
                hora_limite_atual = dt_limite_obj.time()
            else:
                data_limite_atual = datetime.today().date()
                hora_limite_atual = datetime.now().time()

            # --- Tratamento Data INÍCIO ---
            dt_inicio_raw = p.get('data_inicio')
            if dt_inicio_raw:
                dt_inicio_obj = datetime.fromisoformat(dt_inicio_raw.replace("Z", "+00:00")).astimezone(fuso)
                data_inicio_atual = dt_inicio_obj.date()
                hora_inicio_atual = dt_inicio_obj.time()
            else:
                data_inicio_atual = datetime.today().date()
                hora_inicio_atual = datetime.now().time()
            
            with st.form(key=f"form_edita_prova_{p['id']}"):
                st.subheader("⚙️ Configurações Gerais")
                with st.container(border=True):
                    col_t1, col_t2 = st.columns([2, 1])
                    with col_t1:
                        tit = st.text_input("Título da Prova", value=p.get('titulo', ''))
                    with col_t2:
                        idx_serie = ["1º Ano", "2º Ano", "3º Ano"].index(p.get('serie', "1º Ano")) if p.get('serie') in ["1º Ano", "2º Ano", "3º Ano"] else 0
                        ser = st.selectbox("Filtrar questões da Série:", ["1º Ano", "2º Ano", "3º Ano"], index=idx_serie)
                    
                    st.write("---")
                    st.write("**Regras de Acesso e Tempo**")
                    c_dat, c_hor, c_dur = st.columns([1.5, 1.5, 1])
                    
                    with c_dat: 
                        # Captura os valores brutos do calendário com a CHAVE ÚNICA para evitar cache de alertas
                        raw_inicio = st.date_input("🟢 Data Início", value=data_inicio_atual, key=f"di_edit_{p['id']}")
                        raw_limite = st.date_input("🔴 Data Limite", value=data_limite_atual, key=f"df_edit_{p['id']}")
                        
                        # TRAVA CONTRA ALERTAS AMARELOS (Extrai a data se vier como lista/tupla)
                        data_inicio = raw_inicio[0] if isinstance(raw_inicio, (list, tuple)) else raw_inicio
                        data_limite = raw_limite[0] if isinstance(raw_limite, (list, tuple)) else raw_limite

                    with c_hor: 
                        hora_inicio = st.time_input("🟢 Hora Início", value=hora_inicio_atual, key=f"hi_edit_{p['id']}")
                        hora_limite = st.time_input("🔴 Hora Limite", value=hora_limite_atual, key=f"hf_edit_{p['id']}")
                    with c_dur: 
                        tempo_duracao = st.number_input("⏳ Duração (Minutos)", min_value=10, max_value=300, value=p.get('tempo_duracao', 60), step=10)

                    st.write("---")
                    st.write("**Pontuação e Sorteio**")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1: qtd_questoes = st.number_input("🔢 Banco de Questões (Total)", min_value=1, max_value=100, value=p.get('qtd_questoes', 10))
                    with col_p2:
                        valor_questao = st.number_input("⭐ Valor de cada Questão", min_value=0.1, max_value=10.0, value=float(p.get('valor_questao', 1.0)), step=0.5)
                        qtd_sorteio = st.number_input("🎲 Sorteio: Questões por Aluno", min_value=1, max_value=int(qtd_questoes), value=p.get('qtd_sorteio', 10))
                
                st.info("💡 Nota: Alterar a Série ou o Total do Banco exigirá que você re-selecione as questões no banco no futuro.")
                
                btn_salvar = st.form_submit_button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True)
                
                if btn_salvar:
                    if not tit:
                        st.error("Erro: Defina um título para a prova.")
                    else:
                        with st.spinner("Atualizando prova..."):
                            naive_inicio = datetime.combine(data_inicio, hora_inicio)
                            naive_limite = datetime.combine(data_limite, hora_limite)

                            aware_inicio = fuso.localize(naive_inicio)
                            aware_limite = fuso.localize(naive_limite)

                            dados_upd = {
                                "titulo": tit, 
                                "serie": ser, 
                                "data_inicio": aware_inicio.isoformat(), 
                                "data_limite": aware_limite.isoformat(), 
                                "tempo_duracao": tempo_duracao,
                                "qtd_questoes": qtd_questoes, 
                                "qtd_sorteio": qtd_sorteio, 
                                "valor_questao": valor_questao
                            }
                            supabase.table("modelos_prova").update(dados_upd).eq("id", p['id']).execute()
                        
                        st.session_state.editando_prova_id = None
                        st.success("Configurações da prova atualizadas!")
                        time.sleep(1)
                        st.rerun()

    # --- TELA DE LISTAGEM DE PROVAS (COM O DESIGN COMPLETO RESTAURADO) ---
    else:
        st.title("📂 Gerenciar Provas Elaboradas")
        
        res_provas = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
        
        if res_provas.data:
            st.write(f"🔍 Total de avaliações cadastradas: **{len(res_provas.data)}**")
            st.divider()
            
            for prova in res_provas.data:
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 1.5, 2, 1.8], gap="small")
                    
                    # --- Tratamento de Datas e Status Inteligente ---
                    dt_inicio_raw = prova.get('data_inicio')
                    dt_limite_raw = prova.get('data_limite')
                    
                    dt_inicio_formatada = "Imediato"
                    dt_limite_formatada = "Sem limite"
                    prazo_encerrado = False
                    
                    dt_ini_obj = None
                    dt_fim_obj = None

                    if dt_inicio_raw:
                        dt_ini_obj = datetime.fromisoformat(dt_inicio_raw.replace("Z", "+00:00")).astimezone(fuso)
                        dt_inicio_formatada = dt_ini_obj.strftime('%d/%m às %H:%M')
                        
                    if dt_limite_raw:
                        dt_fim_obj = datetime.fromisoformat(dt_limite_raw.replace("Z", "+00:00")).astimezone(fuso)
                        dt_limite_formatada = dt_fim_obj.strftime('%d/%m às %H:%M')
                        prazo_encerrado = agora > dt_fim_obj

                    # Define a cor e o texto do status dinamicamente
                    if not prova.get('ativa'):
                        status_texto = "🔴 INATIVA"
                        cor_status = "#dc3545" # Vermelho
                    elif dt_ini_obj and agora < dt_ini_obj:
                        status_texto = "🟡 AGENDADA"
                        cor_status = "#d39e00" # Amarelo
                    elif dt_fim_obj and agora > dt_fim_obj:
                        status_texto = "🔴 ENCERRADA"
                        cor_status = "#dc3545" # Vermelho
                    else:
                        status_texto = "🟢 ATIVA"
                        cor_status = "#28a745" # Verde

                    c1.markdown(f"### {prova.get('titulo', 'Sem título')}")
                    c1.markdown(f"**De:** {dt_inicio_formatada} | **Até:** {dt_limite_formatada}")
                    
                    c2.markdown(f"**Status:**")
                    c2.markdown(f"<span style='color:{cor_status}; font-weight:bold;'>{status_texto}</span>", unsafe_allow_html=True)
                    
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
                    
            # --- COLUNA 5: AÇÕES (VERSÃO ATUALIZADA) ---
                    with c5:
                        # 1. Botão Editar
                        if st.button("✏️ Editar", key=f"edit_prova_{prova_id}", use_container_width=True):
                            st.session_state.editando_prova_id = prova_id
                            st.rerun()

                        # 2. Botão Ativar/Desativar Prova
                        texto_btn_status = "⏸️ Desativar" if prova.get('ativa') else "▶️ Ativar"
                        if st.button(texto_btn_status, key=f"status_{prova_id}", use_container_width=True):
                            novo_status = not prova.get('ativa')
                            supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova_id).execute()
                            st.rerun()
                        
                        # 3. NOVO: Controle de Visibilidade das Notas (O Cadeado)
                        notas_liberadas = prova.get('notas_liberadas', False)
                        label_notas = "🔒 Esconder Notas" if notas_liberadas else "🔓 Liberar Notas"
                        
                        if st.button(label_notas, key=f"lib_btn_{prova_id}", use_container_width=True):
                            nova_visibilidade = not notas_liberadas
                            supabase.table("modelos_prova").update({"notas_liberadas": nova_visibilidade}).eq("id", prova_id).execute()
                            
                            msg = "Notas LIBERADAS para os alunos!" if nova_visibilidade else "Notas ESCONDIDAS dos alunos!"
                            st.toast(msg)
                            time.sleep(1)
                            st.rerun()

                        # 4. Botão Excluir
                        if st.button("🗑️ Excluir", key=f"del_{prova_id}", type="primary", use_container_width=True):
                            try:
                                supabase.table("resultados_provas").delete().eq("prova_id", prova_id).execute()
                                supabase.table("modelos_prova").delete().eq("id", prova_id).execute()
                                st.success("Prova excluída!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")      

# --- 10. LISTA DE MATRÍCULAS PARA IMPRESSÃO (COM PDF CORRIGIDO) ---
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
                    
                    pdf.set_font("Helvetica", 'B', 14)
                    pdf.cell(0, 10, f"ESCOLA EREMPAM - LISTA DE FREQUENCIA", ln=True, align='C')
                    pdf.set_font("Helvetica", 'B', 12)
                    pdf.cell(0, 10, f"Turma: {turma_selecionada.upper()}", ln=True, align='C')
                    pdf.ln(5)
                    
                    pdf.set_font("Helvetica", 'B', 10)
                    pdf.cell(15, 8, "N", border=1, align='C')
                    pdf.cell(35, 8, "MATRICULA", border=1, align='C')
                    pdf.cell(140, 8, "NOME DO ESTUDANTE", border=1, align='C')
                    pdf.ln()
                    
                    pdf.set_font("Helvetica", '', 10)
                    for _, row in df_lista.iterrows():
                        pdf.cell(15, 8, str(row["Nº ORDEM"]), border=1, align='C')
                        pdf.cell(35, 8, str(row["Nº MATRÍCULA"]), border=1, align='C')
                        
                        nome_aluno = str(row["NOME DO ESTUDANTE"])
                        nfkd = unicodedata.normalize('NFKD', nome_aluno)
                        nome_seguro = "".join([c for c in nfkd if not unicodedata.combining(c)])
                        
                        pdf.cell(140, 8, f" {nome_seguro}", border=1, align='L')
                        pdf.ln()
                    
                    # --- CORREÇÃO DEFINITIVA PARA O PDF ---
                    try:
                        # Tenta o padrão da versão nova (FPDF2)
                        pdf_bytes = bytes(pdf.output())
                    except TypeError:
                        # Se der erro, usa a versão antiga (FPDF 1.x)
                        pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    except Exception:
                        pdf_bytes = str(pdf.output()).encode('latin-1')
                    # --------------------------------------
                    
                    # O botão de download voltou pra cá!
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
                import traceback
                st.error(f"Erro na geração do PDF. Detalhes:")
                st.code(traceback.format_exc())

# --- 11. CENTRAL DE AVISOS WHATSAPP ---
elif menu == "📲 Central de Avisos":
    st.title("📲 Disparador de Avisos - AVALARDIAO")
    
    # Verifica se a variável existe e se é verdadeira
    if 'WHATSAPP_LOCAL' not in globals() or not WHATSAPP_LOCAL:
        st.error("🚨 Ambiente em Nuvem Detectado!")
        st.warning("O disparo automático de mensagens funciona apenas rodando o sistema localmente no seu computador (via VS Code).")
    else:
        st.info("💡 Lembre-se: O WhatsApp Web deve estar logado no seu navegador padrão.")

        # 1. Buscar Provas (Conexão 1)
        res_p = supabase.table("modelos_prova").select("id, titulo, serie").execute()
        df_p = pd.DataFrame(res_p.data)

        if not df_p.empty:
            col1, col2 = st.columns(2)
            with col1:
                prova_sel = st.selectbox("Escolha a Atividade:", df_p['titulo'].tolist())
                dados_p = df_p[df_p['titulo'] == prova_sel].iloc[0]
            
            with col2:
                tipo_msg = st.selectbox("Tipo de Aviso:", [
                    "🚀 1. Alerta de Abertura",
                    "⚠️ 2. Aviso de Prazo Final",
                    "📊 3. Resultado Disponível (IA)",
                    "📝 4. Comunicado Personalizado"
                ])

            # 2. Buscar Alunos (Usando a série da prova para filtrar a turma)
            res_a = supabase_alunos.table("alunos").select("nome, whatsapp").eq("turma", dados_p['serie']).execute()
            df_alunos = pd.DataFrame(res_a.data)

            if not df_alunos.empty:
                st.success(f"📍 {len(df_alunos)} alunos encontrados na turma {dados_p['serie']}")
                
                msg_custom = ""
                if "4." in tipo_msg:
                    msg_custom = st.text_area("Digite a mensagem:")

                if st.button("▶️ INICIAR DISPARO EM MASSA", type="primary"):
                    st.warning("🚀 Disparo iniciado! Mantenha a aba do WhatsApp visível e não mexa no mouse.")
                    
                    for index, aluno in df_alunos.iterrows():
                        nome_completo = str(aluno.get('nome', 'Estudante'))
                        primeiro_nome = nome_completo.split()[0]
                        fone = str(aluno.get('whatsapp', ''))
                        
                        if fone and fone != 'None' and fone.strip() != "":
                            # Limpa o número
                            apenas_numeros = re.sub(r'\D', '', fone)
                            num_limpo = f"+55{apenas_numeros}"
                            
                            # Define o texto
                            if "1." in tipo_msg:
                                texto = f"Olá {primeiro_nome}! 📢 A atividade *{prova_sel}* já está aberta no portal da EREMPAM. Boa sorte!"
                            elif "2." in tipo_msg:
                                texto = f"Atenção {primeiro_nome}! ⏳ O prazo para a atividade *{prova_sel}* está terminando. Não deixe de fazer!"
                            elif "3." in tipo_msg:
                                texto = f"Olá {primeiro_nome}! 📊 Seu diagnóstico e nota da atividade *{prova_sel}* já foram gerados. Confira no sistema!"
                            else:
                                texto = f"Olá {primeiro_nome}! 🔔 {msg_custom}"

                            try:
                                # Faz o envio
                                kit.sendwhatmsg_instantly(num_limpo, texto, 15, True, 3)
                                st.write(f"✅ Mensagem enviada para: **{nome_completo}**")
                                time.sleep(2) 
                            except Exception as e:
                                st.error(f"❌ Falha ao enviar para {primeiro_nome}: {e}")
                        else:
                            st.warning(f"⚠️ Aluno(a) **{nome_completo}** está sem número de WhatsApp cadastrado.")

                    st.success("🏁 Processo de disparo em massa finalizado!")
            else:
                st.warning(f"Nenhum aluno cadastrado na turma {dados_p['serie']}.")
        else:
            st.warning("Nenhuma atividade cadastrada ainda.")

# --- 11. BOLETIM FINAL SIEPE (REGISTRO COMPARTILHÁVEL) ---
elif menu == "🏫 Boletim Final SIEPE":
    st.title("🏫 Boletim Consolidado (Padrão SIEPE)")
    st.markdown("Gerencie as notas das atividades (**AT1 a AT5**) e da Prova (**N2**). A **N1** (soma das ATs) e a **Média** final são calculadas e salvas automaticamente.")

    # Filtros principais
    col_t, col_b = st.columns(2)
    with col_t:
        # Puxa turmas dinamicamente do banco de alunos
        try:
            res_turmas = supabase_alunos.table("alunos").select("turma").execute()
            lista_turmas = sorted(list(set([t['turma'] for t in res_turmas.data if t['turma']]))) if res_turmas.data else ["1º Ano A"]
        except:
            lista_turmas = ["1º Ano A"]
        turma_sel = st.selectbox("Selecione a Turma:", lista_turmas)
    
    with col_b:
        bim_sel = st.selectbox("Bimestre:", ["1º Bimestre", "2º Bimestre", "3º Bimestre", "4º Bimestre"])
    
    st.divider()

    # Cabeçalho da Tabela e Botão de Automação
    st.write("### 📝 Planilha de Lançamento de Notas")
    col_sync1, col_sync2 = st.columns([3, 1])
    with col_sync1:
        st.info("💡 Digite as notas na tabela abaixo como se fosse no Excel. O cálculo da N1 e da Média ocorrerá ao salvar.")
    with col_sync2:
        if st.button("🔄 Sincronizar Atividades Online", use_container_width=True):
            st.toast("Automação engatilhada! Na próxima fase, este botão vai puxar os acertos direto das provas online.", icon="🚀")
    
    # 1. Puxar alunos da turma selecionada
    res_alunos = supabase_alunos.table("alunos").select("id, nome").eq("turma", turma_sel).order("nome").execute()
    
    if res_alunos.data:
        df_alunos = pd.DataFrame(res_alunos.data)
        
        # 2. Puxar notas já salvas no Boletim para esta turma e bimestre
        try:
            res_notas = supabase_alunos.table("boletim_notas").select("*").eq("turma", turma_sel).eq("bimestre", bim_sel).execute()
            df_notas = pd.DataFrame(res_notas.data)
        except Exception as e:
            df_notas = pd.DataFrame() # Tabela ainda não existe ou vazia

        # 3. Mesclar dados (Se já tem nota, puxa. Senão, cria linha a zeros)
        dados_tabela = []
        for _, aluno in df_alunos.iterrows():
            linha = {
                "aluno_id": aluno["id"],
                "Nome do Aluno": aluno["nome"],
                "AT1": 0.0, "AT2": 0.0, "AT3": 0.0, "AT4": 0.0, "AT5": 0.0,
                "N2 (Prova)": 0.0
            }
            if not df_notas.empty:
                nota_existente = df_notas[df_notas["aluno_id"] == aluno["id"]]
                if not nota_existente.empty:
                    linha["AT1"] = float(nota_existente.iloc[0].get("at1", 0.0))
                    linha["AT2"] = float(nota_existente.iloc[0].get("at2", 0.0))
                    linha["AT3"] = float(nota_existente.iloc[0].get("at3", 0.0))
                    linha["AT4"] = float(nota_existente.iloc[0].get("at4", 0.0))
                    linha["AT5"] = float(nota_existente.iloc[0].get("at5", 0.0))
                    linha["N2 (Prova)"] = float(nota_existente.iloc[0].get("n2", 0.0))
            
            dados_tabela.append(linha)
        
        df_edicao = pd.DataFrame(dados_tabela)
        
        # 4. Exibir o Editor de Dados (Tabela Interativa do Streamlit)
        colunas_config = {
            "aluno_id": st.column_config.TextColumn("ID", disabled=True),
            "Nome do Aluno": st.column_config.TextColumn("Estudante", disabled=True, width="medium"),
            "AT1": st.column_config.NumberColumn("AT1", min_value=0.0, max_value=10.0, step=0.1, format="%.1f"),
            "AT2": st.column_config.NumberColumn("AT2", min_value=0.0, max_value=10.0, step=0.1, format="%.1f"),
            "AT3": st.column_config.NumberColumn("AT3", min_value=0.0, max_value=10.0, step=0.1, format="%.1f"),
            "AT4": st.column_config.NumberColumn("AT4", min_value=0.0, max_value=10.0, step=0.1, format="%.1f"),
            "AT5": st.column_config.NumberColumn("AT5", min_value=0.0, max_value=10.0, step=0.1, format="%.1f"),
            "N2 (Prova)": st.column_config.NumberColumn("N2 (Prova)", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
        }

        # A tabela onde a magia acontece
        df_editado = st.data_editor(
            df_edicao, 
            column_config=colunas_config,
            hide_index=True,
            use_container_width=True,
            key=f"editor_notas_{turma_sel}_{bim_sel}"
        )

        # 5. Salvar e Calcular
        if st.button("💾 Salvar Planilha e Calcular SIEPE", type="primary"):
            with st.spinner("A consolidar N1 e Médias..."):
                dados_para_salvar = []
                for _, row in df_editado.iterrows():
                    # Lógica SIEPE: N1 = Soma das Atividades
                    n1 = round(row["AT1"] + row["AT2"] + row["AT3"] + row["AT4"] + row["AT5"], 1)
                    n2 = round(row["N2 (Prova)"], 1)
                    # Média Final
                    media = round((n1 + n2) / 2, 1)

                    dados_para_salvar.append({
                        "aluno_id": row["aluno_id"],
                        "aluno_nome": row["Nome do Aluno"],
                        "turma": turma_sel,
                        "bimestre": bim_sel,
                        "at1": row["AT1"],
                        "at2": row["AT2"],
                        "at3": row["AT3"],
                        "at4": row["AT4"],
                        "at5": row["AT5"],
                        "n1": n1,
                        "n2": n2,
                        "media": media
                    })
                
                try:
                    # Apagamos o registo anterior da turma neste bimestre para não duplicar, e inserimos as novas notas
                    supabase_alunos.table("boletim_notas").delete().eq("turma", turma_sel).eq("bimestre", bim_sel).execute()
                    supabase_alunos.table("boletim_notas").insert(dados_para_salvar).execute()
                    
                    st.success("✅ Notas salvas! Os alunos já podem visualizar estas médias nos seus portais.")
                    st.balloons()
                    
                    # Mostra um mini-relatório do cálculo final
                    st.write("📊 **Resumo Final Consolidado:**")
                    df_final = pd.DataFrame(dados_para_salvar)
                    df_view = df_final[["aluno_nome", "n1", "n2", "media"]].rename(
                        columns={"aluno_nome":"Estudante", "n1":"N1 (Soma ATs)", "n2":"N2 (Prova)", "media":"Média Final"}
                    )
                    st.dataframe(df_view.style.highlight_between(left=0, right=5.9, subset=['Média Final'], color='#ffcccc'), use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {e}. ATENÇÃO: Verifique se criou a tabela 'boletim_notas' no Supabase.")
    else:
        st.warning(f"Nenhum aluno encontrado matriculado na turma {turma_sel}.")

# =================================================================
# 12. MESTRE LARDIÃO - DIAGNÓSTICOS EM LOTE 
# =================================================================
elif menu == "🧠 Diagnósticos IA":
    st.title("👨‍🏫 Central do Mestre Lardião (IA em Lote)")
    st.markdown("Nesta área, você extrai os erros dos alunos para processar no Gemini Web e depois salva no banco.")

    # 1. Selecionar a Prova
    res_p = supabase.table("modelos_prova").select("id, titulo").order("id", desc=True).execute()
    
    if not res_p.data:
        st.warning("Nenhuma prova encontrada.")
    else:
        dict_provas = {p['titulo']: p['id'] for p in res_p.data}
        prova_sel = st.selectbox("Selecione a Prova:", options=list(dict_provas.keys()))
        prova_id = dict_provas[prova_sel]

        st.divider()
        c1, c2 = st.columns(2)

        # ==========================================
        # LADO ESQUERDO: GERAR PROMPT
        # ==========================================
        with c1:
            st.subheader("1️⃣ Extrair Erros")
            if st.button("🔍 Gerar Texto para IA", use_container_width=True):
                
                with st.spinner("Puxando dados da tabela resultados_provas..."):
                    try:
                        res = supabase.table("resultados_provas")\
                            .select("aluno_id, questao_id, resposta_aluno, acertou")\
                            .eq("prova_id", prova_id)\
                            .execute()

                        erros_data = [r for r in res.data if str(r.get('acertou')).lower() == 'false']

                        st.write(f"📊 Total de registros baixados: {len(res.data)} | Erros encontrados: {len(erros_data)}")

                        if not erros_data:
                            st.warning("Nenhum erro encontrado para esta prova.")
                        else:
                            ids_q = list(set([e['questao_id'] for e in erros_data]))
                            q_db = supabase.table("questoes").select("id, assunto, justificativas").in_("id", ids_q).execute()
                            dict_q = {q['id']: q for q in q_db.data}

                            mapa = {}
                            for e in erros_data:
                                # GARANTIA CONTRA ERRO DE UUID (Transforma em String)
                                aid = str(e['aluno_id']) 
                                
                                letra = str(e.get('resposta_aluno') or e.get('resposta', '')).strip().upper()
                                dados_q = dict_q.get(e['questao_id'], {})
                                assunto = dados_q.get('assunto', 'Geral')
                                justs = dados_q.get('justificativas') or {}
                                
                                txt_erro = justs.get(letra, f"Errou a questão (marcou {letra})")
                                info_final = f"[Assunto: {assunto}] {txt_erro}"
                                
                                if aid not in mapa: mapa[aid] = []
                                mapa[aid].append(info_final)

                            prompt_txt = "Aja como o Mestre Lardião, professor de Química de PE (use sotaque: visse, oxente, arretado).\n"
                            prompt_txt += "Crie um feedback curto (máx 3 linhas) e motivador para cada aluno com base nos erros técnicos abaixo.\n"
                            prompt_txt += "ME DEVOLVA APENAS UM ARQUIVO JSON no formato exato: {\"ID_DO_ALUNO\": \"TEXTO_DO_FEEDBACK\"}.\n\n"
                            
                            for aid, lista_erros in mapa.items():
                                prompt_txt += f"Aluno ID: {aid}\n"
                                for erro in lista_erros:
                                    prompt_txt += f"- {erro}\n"
                                prompt_txt += "\n"
                            
                            st.text_area("Copie tudo abaixo e cole no Gemini Web:", value=prompt_txt, height=300)
                            st.success("✅ Prompt gerado! Agora é só levar pro Gemini e trazer o JSON de volta.")

                    except Exception as e:
                        st.error(f"Erro ao acessar tabelas: {e}")

        # ==========================================
        # LADO DIREITO: SALVAR NO BANCO
        # ==========================================
        with c2:
            st.subheader("2️⃣ Importar Diagnósticos")
            json_input = st.text_area("Cole o JSON da IA aqui:", height=200, placeholder='{"123": "Oxe, melhore!"}')
            
            if st.button("💾 Salvar Feedbacks no Banco", type="primary", use_container_width=True):
                if json_input:
                    try:
                        dados_ia = json.loads(json_input)
                        count = 0
                        for al_id, txt in dados_ia.items():
                            supabase.table("feedback_ia_alunos").insert({
                                "aluno_id": str(al_id), # CORREÇÃO CRÍTICA: Aceitar letras e números
                                "prova_id": str(prova_id),
                                "diagnostico_pedagogico": txt,
                                "revisado_professor": True
                            }).execute()
                            count += 1
                        st.success(f"✅ {count} feedbacks salvos na tabela 'feedback_ia_alunos'!")
                        st.balloons()
                    except json.JSONDecodeError:
                        st.error("Erro: O texto colado não é um JSON válido.")
                    except Exception as e:
                        st.error("❌ Erro ao salvar no banco. Mensagem:")
                        st.code(str(e))