import streamlit as st
import datetime
import time

def mostrar_inscricao_aluno(db_alunos):
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

    # --- 2. IDENTIFICAÇÃO DA ESTUDANTE E SUA SÉRIE ---
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', ''))
    
    # Lógica de extração da série (1º, 2º ou 3º)
    serie_aluno = "Geral"
    if "1º" in turma_aluno: serie_aluno = "1º"
    elif "2º" in turma_aluno: serie_aluno = "2º"
    elif "3º" in turma_aluno: serie_aluno = "3º"

    st.title("🚀 Central de Inscrições")
    st.info(f"🎓 Estudante: **{aluno.get('nome')}** | Série: **{serie_aluno}**")

    # Controle de Navegação
    if 'passo_insc' not in st.session_state: st.session_state.passo_insc = 1
    
    # Stepper Visual
    p1, p2, p3 = ["step-active" if st.session_state.passo_insc == i else "" for i in range(1, 4)]
    st.markdown(f"""
        <div class="step-container">
            <div class="step {p1}">1. EVENTO</div>
            <div class="step {p2}">2. SELECIONAR TEMA</div>
            <div class="step {p3}">3. FINALIZAR</div>
        </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # PASSO 1: ESCOLHER EVENTO
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
            st.error(f"Erro: {e}")

    # ==========================================
    # PASSO 2: FILTRAR TEMAS PELA SÉRIE (A PARTE "DIFÍCIL")
    # ==========================================
    elif st.session_state.passo_insc == 2:
        evento = st.session_state.evento_selecionado
        st.subheader(f"Temas Disponíveis para o {serie_aluno} Ano")
        
        if st.button("⬅️ Voltar"):
            st.session_state.passo_insc = 1
            st.rerun()

        try:
            # Buscamos os temas do evento
            res_temas = db_alunos.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            
            if not res_temas.data:
                st.warning("Sem temas cadastrados.")
            else:
                # FILTRO MÁGICO CORRIGIDO: Usando 'Serie' com S maiúsculo igualzinho ao banco de dados
                temas_filtrados = [
                    t for t in res_temas.data 
                    if str(t.get('Serie')).strip() == serie_aluno or str(t.get('Serie')) == "Geral"
                ]

                if not temas_filtrados:
                    st.error(f"Desculpe, não encontramos temas específicos para o {serie_aluno} ano neste evento.")
                else:
                    for tema in temas_filtrados:
                        with st.expander(f"📙 {tema['titulo_trabalho']}"):
                            st.write(f"**Orientador:** {tema.get('professor_nome')}")
                            # Exibindo com a coluna correta
                            st.write(f"**Série Destinada:** {tema.get('Serie')} Ano") 
                            if st.button("ESCOLHER ESTE TEMA", key=f"t_{tema['id']}", use_container_width=True):
                                st.session_state.tema_selecionado = tema
                                st.session_state.passo_insc = 3
                                st.rerun()
        except Exception as e:
            st.error(f"Erro ao filtrar temas: {e}")

    # ==========================================
    # PASSO 3: FINALIZAR INSCRIÇÃO
    # ==========================================
    elif st.session_state.passo_insc == 3:
        tema = st.session_state.tema_selecionado
        evento = st.session_state.evento_selecionado
        
        st.success(f"Confirmando inscrição em: {tema['titulo_trabalho']}")
        
        with st.form("form_final"):
            st.markdown("### 👥 Integrantes da Equipe")
            st.text_input("Líder", value=aluno.get('nome'), disabled=True)
            outros = st.text_area("Nomes dos demais membros (um por linha)")
            
            if st.form_submit_button("CONCLUIR INSCRIÇÃO", type="primary", use_container_width=True):
                lista_membros = [m.strip() for m in outros.split('\n') if m.strip()]
                total = len(lista_membros) + 1
                
                if total < int(evento['min_membros']) or total > int(evento['max_membros']):
                    st.error(f"Erro: O grupo deve ter entre {evento['min_membros']} e {evento['max_membros']} alunos.")
                else:
                    try:
                        equipe = f"{aluno.get('nome')} (Líder), " + ", ".join(lista_membros)
                        dados = {
                            "evento_id": evento['id'], "tema_id": tema['id'],
                            "lider_id": id_aluno, "turma": turma_aluno,
                            "nomes_membros": equipe, "data_inscricao": str(datetime.date.today())
                        }
                        db_alunos.table("feira_inscricoes").insert(dados).execute()
                        st.balloons()
                        st.success("✅ Inscrito com sucesso!")
                        time.sleep(2)
                        st.session_state.passo_insc = 1
                        st.session_state.etapa = "ante_sala"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        if st.button("⬅️ Trocar Tema"):
            st.session_state.passo_insc = 2
            st.rerun()