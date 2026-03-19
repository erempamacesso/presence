import streamlit as st
from supabase import create_client
from streamlit_quill import st_quill
import plotly.express as px
import pandas as pd
import json

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão EREMPAM - Provas", layout="wide")

# --- 2. CONEXÃO COM SUPABASE (DUPLA CONEXÃO CORRIGIDA) ---
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
    "📜 Gerar Modelo de Prova",
    "📂 Provas Elaboradas",  
    "🖨️ Lista de Matrículas", 
    "🧹 Limpeza de Testes" 
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

    if st.session_state.editando_id is not None:
        st.title("✏️ Editar Questão")
        
        if st.button("⬅️ Voltar para a Biblioteca", type="secondary"):
            st.session_state.editando_id = None
            st.rerun()
            
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
                st.markdown("📝 **Enunciado da Questão**")
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
                        "serie": edit_serie, "assunto": edit_assunto, "resposta_correta": edit_gabarito,
                        "dificuldade": edit_diff, "enunciado": edit_enunciado,
                        "alternativas": edit_alts, "justificativas": edit_justs
                    }
                    supabase.table("questoes").update(dados_upd).eq("id", q['id']).execute()
                    st.session_state.editando_id = None
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()

    else:
        st.title("📚 Biblioteca de Questões")
        
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
                    id_curto = str(q['id']).split('-')[0][:4] 
                    c1.write(f"#{id_curto}")
                    c2.markdown('<span style="color: #28a745; background-color: #d4edda; padding: 4px; border-radius: 4px; font-size: 11px;">✅ Pronta</span>', unsafe_allow_html=True)
                    c3.markdown(f"**{q['serie']}**<br><span style='color:#28a745; font-size:11px;'>{q['assunto'].upper()}</span>", unsafe_allow_html=True)
                    c4.write(previa)
                    c5.markdown(f"**{q['resposta_correta']}**")
                    
                    bc1, bc2 = c6.columns(2)
                    if bc1.button("✏️", key=f"edit_{q['id']}", help="Editar questão"):
                        st.session_state.editando_id = q['id']
                        st.rerun()
                    if bc2.button("🗑️", key=f"del_{q['id']}", help="Excluir questão"):
                        supabase.table("questoes").delete().eq("id", q['id']).execute()
                        st.rerun()
        else:
            st.info("Nenhuma questão encontrada.")

# --- 8. GERADOR DE MODELOS ---
elif menu == "📜 Gerar Modelo de Prova":
    st.title("📜 Publicar Prova para Alunos")
    
    import re
    from datetime import datetime
    import time

    res_q = supabase.table("questoes").select("id, assunto, serie, dificuldade, enunciado, resposta_correta").execute()
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
    
    res_provas = supabase.table("modelos_prova").select("*").order("id", desc=True).execute()
    
    if res_provas.data:
        st.write(f"🔍 Total de avaliações cadastradas: **{len(res_provas.data)}**")
        st.divider()
        
        for prova in res_provas.data:
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2.5, 1.5, 1.5, 2, 1.5], gap="small")
                
                status_texto = "🟢 ATIVA" if prova.get('ativa') else "🔴 INATIVA"
                dt_limite = prova.get('data_limite', 'Sem limite')
                if dt_limite != 'Sem limite':
                    dt_limite = dt_limite[:16].replace("T", " às ")
                
                c1.markdown(f"### {prova.get('titulo', 'Sem título')}")
                c1.markdown(f"**Série:** {prova.get('serie', 'Geral')} | **Prazo:** {dt_limite}")
                
                c2.markdown(f"**Status:**")
                c2.markdown(f"*{status_texto}*")
                
                q_total = prova.get('qtd_questoes', 0)
                q_sorteio = prova.get('qtd_sorteio', q_total)
                c3.markdown("**Formato:**")
                c3.caption(f"Banco: {q_total} | Sorteio: {q_sorteio}")
                
                # --- CORRIGIDO AQUI: USANDO supabase_alunos para buscar os alunos ---
                serie_atual = prova.get('serie')
                prova_id = prova.get('id')
                
                try:
                    # Usando supabase_alunos para ler do projeto Chamada
                    res_alunos = supabase_alunos.table("alunos").select("id").eq("serie", serie_atual).execute()
                    total_alunos = len(res_alunos.data) if res_alunos.data else 0
                    
                    # Usando supabase para ler do projeto de Provas
                    res_respostas = supabase.table("respostas_alunos").select("aluno_id").eq("prova_id", prova_id).execute()
                    alunos_que_fizeram = len(set([r['aluno_id'] for r in res_respostas.data])) if res_respostas.data else 0
                    
                    if total_alunos > 0:
                        porcentagem = (alunos_que_fizeram / total_alunos) * 100
                    else:
                        porcentagem = 0.0
                        
                    c4.markdown("**Engajamento:**")
                    c4.markdown(f"**{alunos_que_fizeram} / {total_alunos}** alunos")
                    cor_perc = "green" if porcentagem >= 70 else ("orange" if porcentagem >= 40 else "red")
                    c4.markdown(f"<span style='color:{cor_perc}; font-weight:bold;'>{porcentagem:.1f}% concluído</span>", unsafe_allow_html=True)
                    
                except Exception as e:
                    c4.markdown("**Engajamento:**")
                    c4.caption("Dados não encontrados.")
                
                with c5:
                    texto_btn_status = "⏸️ Desativar" if prova.get('ativa') else "▶️ Ativar"
                    if st.button(texto_btn_status, key=f"status_{prova['id']}", use_container_width=True):
                        novo_status = not prova.get('ativa')
                        supabase.table("modelos_prova").update({"ativa": novo_status}).eq("id", prova['id']).execute()
                        st.rerun()
                    
                    if st.button("🗑️ Excluir", key=f"del_{prova['id']}", type="primary", use_container_width=True):
                        supabase.table("modelos_prova").delete().eq("id", prova['id']).execute()
                        st.rerun()
                        
    else:
        st.info("📌 Nenhuma prova foi elaborada ainda.")

# --- 10. LISTA DE MATRÍCULAS PARA IMPRESSÃO ---
elif menu == "🖨️ Lista de Matrículas":
    st.title("🖨️ Impressão de Matrículas por Turma")
    
    if st.button("🔍 Testar Conexão com Tabelas"):
        try:
            res = supabase_alunos.table("alunos").select("count", count="exact").limit(1).execute()
            st.success("✅ O sistema conseguiu encontrar a tabela 'alunos' no projeto da Chamada!")
        except Exception as e:
            st.error(f"❌ Erro Real: {e}")

    try:
        res_turmas = supabase_alunos.table("alunos").select("turma").execute()
        if res_turmas.data:
            lista_turmas = sorted(list(set([t['turma'] for t in res_turmas.data if t['turma']])))
        else:
            lista_turmas = ["3º A", "3º B", "3º C"] 
    except:
        lista_turmas = ["Erro ao carregar turmas"]

    turma_selecionada = st.selectbox("Selecione a Turma:", lista_turmas)

    if st.button("📄 Gerar Lista para Impressão", type="primary"):
        with st.spinner("Gerando lista..."):
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
                    st.divider()
                    st.subheader(f"ALUNOS DO {turma_selecionada.upper()}")
                    st.table(df_lista.set_index("Nº ORDEM"))
                    st.info("🖨️ Pressione `Ctrl + P` para imprimir.")
                else:
                    st.warning(f"Nenhum aluno encontrado na turma {turma_selecionada}.")
            except Exception as e:
                st.error(f"Erro na geração: {e}")

# --- 11. LIMPEZA ---
elif menu == "🧹 Limpeza de Testes":
    st.title("🧹 Limpeza do Banco (Apenas testes)")
    st.warning("Aqui você pode apagar todas as questões do projeto de Provas.")
    if st.button("Apagar TODAS as questões", type="primary"):
        supabase.table("questoes").delete().neq("id", "0").execute()
        st.success("Tudo apagado!")