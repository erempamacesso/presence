import streamlit as st
import datetime
import time

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
    # PASSO 2: FILTRAR TEMAS E BLOQUEAR OCUPADOS
    # ==========================================
    elif st.session_state.passo_insc == 2:
        evento = st.session_state.evento_selecionado
        st.subheader(f"Temas Disponíveis para o {serie_aluno} Ano")
        
        if st.button("⬅️ Voltar"):
            st.session_state.passo_insc = 1
            st.rerun()

        try:
            # 1. A VERIFICAÇÃO (Consulta Cruzada)
            # Vamos ao db_provas ver se a turma do aluno já escolheu algum tema neste evento
            res_inscricoes = db_provas.table("feira_inscricoes") \
                .select("tema_id") \
                .eq("evento_id", evento['id']) \
                .eq("turma", turma_aluno) \
                .execute()
            
            # Criamos uma lista apenas com os IDs dos temas que já estão ocupados por esta turma
            temas_ocupados_pela_turma = [insc['tema_id'] for insc in res_inscricoes.data]

            # 2. BUSCAR TODOS OS TEMAS (Lê de db_alunos)
            res_temas = db_alunos.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            
            # 3. FILTRO DA SÉRIE (Apenas temas da série do aluno ou Geral)
            temas_filtrados = [
                t for t in res_temas.data 
                if str(t.get('Serie')).strip() == serie_aluno or str(t.get('Serie')) == "Geral"
            ]

            if not temas_filtrados:
                st.error("Desculpe, não há temas para a sua série neste evento.")
            else:
                # 4. DESENHAR NO ECRÃ COM A REGRA DE EXCLUSIVIDADE
                for tema in temas_filtrados:
                    # Verifica se o ID deste tema está na lista de ocupados
                    is_ocupado = tema['id'] in temas_ocupados_pela_turma
                    
                    with st.expander(f"📙 {tema['titulo_trabalho']}"):
                        st.write(f"**Orientador:** {tema.get('professor_nome')}")
                        
                        if is_ocupado:
                            # Se estiver ocupado, mostra o aviso e um botão desativado
                            st.warning("🚫 Este tema já foi escolhido por outro grupo da sua turma.")
                            st.button("TEMA INDISPONÍVEL", key=f"t_{tema['id']}", disabled=True, use_container_width=True)
                        else:
                            # Se estiver livre, mostra o botão normal
                            if st.button("ESCOLHER ESTE TEMA", key=f"t_{tema['id']}", type="primary", use_container_width=True):
                                st.session_state.tema_selecionado = tema
                                st.session_state.passo_insc = 3
                                st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar e filtrar temas: {e}")

    # ==========================================
    # PASSO 3: FINALIZAR (Lê de db_alunos | Escreve em db_provas)
    # ==========================================
    elif st.session_state.passo_insc == 3:
        tema = st.session_state.tema_selecionado
        evento = st.session_state.evento_selecionado
        
        st.success(f"📍 Inscrição: **{tema['titulo_trabalho']}**")
        
        # Busca colegas na mesma turma (em db_alunos)
        colegas_turma = []
        try:
            res_colegas = db_alunos.table("alunos").select("nome").eq("turma", turma_aluno).execute()
            colegas_turma = sorted([c['nome'] for c in res_colegas.data if c['nome'] != aluno.get('nome')])
        except:
            pass

        with st.form("form_final"):
            st.markdown("### 👥 Membros da Equipe")
            st.text_input("Líder", value=aluno.get('nome'), disabled=True)
            
            membros_sel = st.multiselect("Selecione os colegas da sua turma:", options=colegas_turma)
            
            # O BOTÃO FINAL
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
                        
                        # --- A MÁGICA ACONTECE AQUI ---
                        # Salvamos no projeto 'Avaliador-provas'
                        db_provas.table("feira_inscricoes").insert(dados_insc).execute()
                        
                        st.balloons()
                        st.success("✅ Inscrição confirmada no projeto Avaliador-provas!")
                        time.sleep(2)
                        st.session_state.passo_insc = 1
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de provas: {e}")

        if st.button("⬅️ Trocar Tema"):
            st.session_state.passo_insc = 2
            st.rerun()