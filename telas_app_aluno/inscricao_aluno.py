import streamlit as st
import datetime
import time
from collections import defaultdict

def mostrar_inscricao_aluno(db_alunos, db_provas):
    # --- 1. ESTILO CSS ---
    st.markdown("""
        <style>
        .event-card {
            background-color: white; padding: 20px; border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid #00d4ff;
            margin-bottom: 20px;
        }
        .step-container {
            display: flex; justify-content: space-between; margin-bottom: 30px;
            background: white; padding: 15px; border-radius: 10px;
        }
        .step { color: #bdc3c7; font-weight: bold; width: 30%; text-align: center; font-size: 0.9rem; }
        .step-active { color: #00d4ff; border-bottom: 3px solid #00d4ff; }
        
        .tema-card {
            background: #f8f9fa; padding: 15px; border-radius: 8px;
            margin: 10px 0; border-left: 4px solid #00d4ff;
        }
        .tema-card-bloqueado {
            background: #ffe6e6; border-left-color: #d32f2f;
            opacity: 0.7;
        }
        .tema-card-disciplina-bloqueada {
            background: #fff3e0; border-left-color: #f57c00;
            opacity: 0.7;
        }
        .disciplina-titulo {
            font-weight: bold; font-size: 1.1rem; color: #333;
            padding: 10px; background: #e3f2fd; border-radius: 5px;
            margin-top: 15px; margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Identificação da estudante
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', ''))
    
    # Lógica de extração da série
    serie_aluno = "Geral"
    if "1º" in turma_aluno: serie_aluno = "1º"
    elif "2º" in turma_aluno: serie_aluno = "2º"
    elif "3º" in turma_aluno: serie_aluno = "3º"

    st.title("🚀 Central de Inscrições")
    st.info(f"🎓 **{aluno.get('nome')}** | Série: **{serie_aluno}** | Turma: **{turma_aluno}**")

    if 'passo_insc' not in st.session_state: st.session_state.passo_insc = 1
    
    # Stepper Visual
    p1, p2, p3 = ["step-active" if st.session_state.passo_insc == i else "" for i in range(1, 4)]
    st.markdown(f"""
        <div class="step-container">
            <div class="step {p1}">1. EVENTO</div>
            <div class="step {p2}">2. TEMA</div>
            <div class="step {p3}">3. EQUIPE E FINALIZAR</div>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # PASSO 1: ESCOLHER EVENTO (Lê de db_alunos)
    # ==========================================
    if st.session_state.passo_insc == 1:
        try:
            res = db_alunos.table("feira_eventos").select("*").eq("ativo", True).execute()
            if not res.data:
                st.info("Nenhum evento disponível no momento.")
            else:
                for ev in res.data:
                    with st.container():
                        st.markdown(f"""<div class="event-card"><h2>{ev['nome']}</h2><p>📅 {ev['data_inicio']} até {ev['data_fim']}</p></div>""", unsafe_allow_html=True)
                        if st.button(f"INSCREVER-SE EM: {ev['nome']}", key=ev['id'], type="primary"):
                            st.session_state.evento_selecionado = ev
                            st.session_state.passo_insc = 2
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

    # ==========================================
    # PASSO 2: FILTRAR TEMAS E APLICAR TRAVA DUPLA
    # ==========================================
    elif st.session_state.passo_insc == 2:
        evento = st.session_state.evento_selecionado
        st.subheader(f"Temas Disponíveis para o {serie_aluno} Ano")
        
        if st.button("⬅️ Voltar"):
            st.session_state.passo_insc = 1
            st.rerun()

        try:
            # ===== ETAPA 1: BUSCAR TODAS AS INSCRIÇÕES DESTE EVENTO =====
            res_inscricoes = db_provas.table("feira_inscricoes") \
                .select("tema_id, turma") \
                .eq("evento_id", evento['id']) \
                .execute()
            
            inscricoes_feitas = res_inscricoes.data

            # ===== ETAPA 2: CALCULAR BLOQUEIOS =====
            # Temas específicos que JÁ FORAM ESCOLHIDOS (bloqueio global)
            temas_escolhidos_global = [insc['tema_id'] for insc in inscricoes_feitas]
            
            # Disciplinas que JÁ FORAM ESCOLHIDAS PELA MINHA TURMA (bloqueio por turma)
            temas_da_minha_turma = [insc['tema_id'] for insc in inscricoes_feitas if insc['turma'] == turma_aluno]
            
            # Buscar todos os temas para extrair disciplinas
            res_todos_temas_temp = db_alunos.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            todos_temas_dict = {t['id']: t for t in res_todos_temas_temp.data}
            
            # Disciplinas bloqueadas para minha turma
            disciplinas_bloqueadas_turma = set()
            for tema_id in temas_da_minha_turma:
                if tema_id in todos_temas_dict:
                    disciplinas_bloqueadas_turma.add(todos_temas_dict[tema_id].get('disciplina', ''))

            # ===== ETAPA 3: BUSCAR TODOS OS TEMAS DO EVENTO =====
            res_temas = db_alunos.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            todos_temas = res_temas.data
            
            # ===== ETAPA 4: FILTRAR PELA SÉRIE E APLICAR REGRAS =====
            temas_filtrados = [
                t for t in todos_temas 
                if str(t.get('Serie')).strip() == serie_aluno or str(t.get('Serie')) == "Geral"
            ]

            if not temas_filtrados:
                st.error("Desculpe, não há temas para a sua série neste evento.")
            else:
                # ===== ETAPA 5: AGRUPAR POR DISCIPLINA =====
                temas_por_disciplina = defaultdict(list)
                for tema in temas_filtrados:
                    disciplina = tema.get('disciplina', 'Sem Disciplina')
                    temas_por_disciplina[disciplina].append(tema)
                
                # ===== ETAPA 6: RENDERIZAR COM ACORDEON =====
                for disciplina in sorted(temas_por_disciplina.keys()):
                    temas_da_disciplina = temas_por_disciplina[disciplina]
                    
                    # Verificar se esta disciplina está bloqueada para a minha turma
                    disciplina_bloqueada = disciplina in disciplinas_bloqueadas_turma
                    
                    # Label do acordeon com status
                    if disciplina_bloqueada:
                        label = f"📛 {disciplina} (Sua turma já escolheu) - BLOQUEADA"
                    else:
                        label = f"📚 {disciplina}"
                    
                    with st.expander(label, expanded=False):
                        # Se a disciplina está bloqueada, mostrar mensagem
                        if disciplina_bloqueada:
                            st.warning(f"⚠️ A sua turma ({turma_aluno}) já escolheu um trabalho de {disciplina}. Nenhum outro tema desta disciplina está disponível.")
                        else:
                            # Renderizar os temas da disciplina
                            for tema in temas_da_disciplina:
                                tema_escolhido_global = tema['id'] in temas_escolhidos_global
                                
                                # Container visual para o tema
                                if tema_escolhido_global:
                                    container_class = "tema-card tema-card-bloqueado"
                                    status = "🚫 INDISPONÍVEL"
                                else:
                                    container_class = "tema-card"
                                    status = "✅ DISPONÍVEL"
                                
                                st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
                                
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"**{tema['titulo_trabalho']}**")
                                    st.caption(f"👨‍🏫 {tema.get('professor_nome', 'Sem professor')}")
                                    if tema.get('descricao'):
                                        st.caption(f"📝 {tema.get('descricao')}")
                                
                                with col2:
                                    st.caption(status)
                                
                                # Botão de seleção
                                if tema_escolhido_global:
                                    st.button(
                                        "TEMA JÁ ESCOLHIDO",
                                        key=f"t_{tema['id']}",
                                        disabled=True,
                                        use_container_width=True
                                    )
                                else:
                                    if st.button(
                                        "ESCOLHER ESTE TEMA",
                                        key=f"t_{tema['id']}",
                                        type="primary",
                                        use_container_width=True
                                    ):
                                        st.session_state.tema_selecionado = tema
                                        st.session_state.passo_insc = 3
                                        st.rerun()
                                
                                st.markdown('</div>', unsafe_allow_html=True)
                                st.divider()
                
        except Exception as e:
            st.error(f"Erro ao carregar e filtrar temas: {e}")
            import traceback
            st.error(traceback.format_exc())
            
    # ==========================================
    # PASSO 3: FINALIZAR (Lê de db_alunos | Escreve em db_provas)
    # ==========================================
    elif st.session_state.passo_insc == 3:
        tema = st.session_state.tema_selecionado
        evento = st.session_state.evento_selecionado
        
        st.success(f"📍 Inscrição: **{tema['titulo_trabalho']}**")
        
        # 1. BUSCAR TODOS OS COLEGAS DA TURMA (db_alunos)
        colegas_turma = []
        try:
            res_colegas = db_alunos.table("alunos").select("nome").eq("turma", turma_aluno).execute()
            # Lista inicial com todos (exceto o próprio líder logado)
            todos_da_turma = [c['nome'] for c in res_colegas.data if c['nome'] != aluno.get('nome')]
            
            # 2. BUSCAR QUEM JÁ ESTÁ INSCRITO NESTE EVENTO (db_provas)
            res_ocupados = db_provas.table("feira_inscricoes") \
                .select("nomes_membros") \
                .eq("evento_id", evento['id']) \
                .eq("turma", turma_aluno) \
                .execute()
            
            # 3. EXTRAIR OS NOMES QUE JÁ ESTÃO EM EQUIPES
            nomes_ja_ocupados = set()
            for insc in res_ocupados.data:
                texto_equipe = insc.get('nomes_membros', '')
                # Como salvamos como "Nome (Líder), Membro 1, Membro 2"
                # Vamos quebrar pela vírgula e limpar os espaços e o sufixo "(Líder)"
                membros_extraidos = [
                    m.replace(" (Líder)", "").strip() 
                    for m in texto_equipe.split(",")
                ]
                for m in membros_extraidos:
                    nomes_ja_ocupados.add(m)
            
            # 4. FILTRAR: Só sobram os que NÃO estão na lista de ocupados
            colegas_disponiveis = [nome for nome in todos_da_turma if nome not in nomes_ja_ocupados]
            colegas_turma = sorted(colegas_disponiveis)
            
        except Exception as e:
            st.error(f"Erro ao filtrar disponibilidade de alunos: {e}")

        with st.form("form_final"):
            st.markdown("### 👥 Membros da Equipe")
            st.info(f"Olá {aluno.get('nome')}, selecione apenas os colegas que ainda não estão em outros grupos.")
            
            st.text_input("Líder", value=aluno.get('nome'), disabled=True)
            
            # Exibe apenas os colegas disponíveis
            membros_sel = st.multiselect(
                "Selecione os colegas disponíveis:", 
                options=colegas_turma,
                help="Se um colega não aparece aqui, é porque ele já faz parte de outra equipe."
            )
            
            if st.form_submit_button("CONCLUIR INSCRIÇÃO", type="primary", use_container_width=True):
                total = len(membros_sel) + 1
                
                if total < int(evento['min_membros']) or total > int(evento['max_membros']):
                    st.error(f"O grupo deve ter entre {evento['min_membros']} e {evento['max_membros']} integrantes.")
                else:
                    try:
                        equipe_str = f"{aluno.get('nome')} (Líder), " + ", ".join(membros_sel)
                        
                        dados_insc = {
                            "evento_id": evento['id'],
                            "tema_id": tema['id'],
                            "lider_id": id_aluno,
                            "turma": turma_aluno,
                            "nomes_membros": equipe_str,
                            "data_inscricao": str(datetime.date.today())
                        }
                        
                        db_provas.table("feira_inscricoes").insert(dados_insc).execute()
                        
                        st.balloons()
                        st.success("✅ Inscrição confirmada com sucesso!")
                        time.sleep(2)
                        st.session_state.passo_insc = 1
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        if st.button("⬅️ Trocar Tema"):
            st.session_state.passo_insc = 2
            st.rerun()