import streamlit as st
import datetime
import time

def mostrar_inscricao_aluno(db_alunos):
    # --- 1. ESTILO CSS PROFISSIONAL ---
    st.markdown("""
        <style>
        .main { background-color: #f8f9fa; }
        .event-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-left: 6px solid #00d4ff;
            margin-bottom: 20px;
        }
        .step-container {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
            background: white;
            padding: 15px;
            border-radius: 10px;
        }
        .step { color: #bdc3c7; font-weight: bold; width: 30%; text-align: center; font-size: 0.9rem; }
        .step-active { color: #00d4ff; border-bottom: 3px solid #00d4ff; }
        .stButton>button { border-radius: 8px; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Central de Inscrições")
    
    # --- 2. CONTROLE DE NAVEGAÇÃO INTERNA ---
    if 'passo_insc' not in st.session_state:
        st.session_state.passo_insc = 1
    
    # Indicador de Progresso
    p1 = "step-active" if st.session_state.passo_insc == 1 else ""
    p2 = "step-active" if st.session_state.passo_insc == 2 else ""
    p3 = "step-active" if st.session_state.passo_insc == 3 else ""
    
    st.markdown(f"""
        <div class="step-container">
            <div class="step {p1}">1. ESCOLHER EVENTO</div>
            <div class="step {p2}">2. SELECIONAR TEMA</div>
            <div class="step {p3}">3. FINALIZAR EQUIPE</div>
        </div>
    """, unsafe_allow_html=True)

    # Dados do Aluno Logado
    aluno = st.session_state.get('aluno', {})
    id_aluno = str(aluno.get('id', ''))
    turma_aluno = aluno.get('turma', 'Sem Turma')

    # ==========================================
    # PASSO 1: VITRINE DE EVENTOS
    # ==========================================
    if st.session_state.passo_insc == 1:
        st.subheader("Eventos com Inscrições Abertas")
        try:
            res = db_alunos.table("feira_eventos").select("*").eq("ativo", True).execute()
            if not res.data:
                st.info("💡 No momento não há eventos disponíveis.")
            else:
                for ev in res.data:
                    with st.container():
                        st.markdown(f"""
                            <div class="event-card">
                                <h2 style='margin:0; color: #2c3e50;'>{ev['nome']}</h2>
                                <p style='color: #7f8c8d; margin: 10px 0;'>
                                    📍 Local: Escola | 📅 {ev['data_inicio']} até {ev['data_fim']}
                                </p>
                                <span style='background: #e1f5fe; color: #01579b; padding: 5px 10px; border-radius: 20px; font-size: 0.8rem;'>
                                    👥 Equipes: {ev['min_membros']} a {ev['max_membros']} alunos
                                </span>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"INSCREVER-SE EM: {ev['nome']}", key=f"btn_ev_{ev['id']}", use_container_width=True, type="primary"):
                            st.session_state.evento_selecionado = ev
                            st.session_state.passo_insc = 2
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")

    # ==========================================
    # PASSO 2: SELEÇÃO DE TEMAS
    # ==========================================
    elif st.session_state.passo_insc == 2:
        evento = st.session_state.evento_selecionado
        st.subheader(f"Temas Disponíveis para {evento['nome']}")
        
        if st.button("⬅️ Voltar para Eventos"):
            st.session_state.passo_insc = 1
            st.rerun()

        try:
            res_temas = db_alunos.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            if not res_temas.data:
                st.warning("Nenhum tema cadastrado para este evento.")
            else:
                for tema in res_temas.data:
                    with st.expander(f"📙 {tema['titulo_trabalho']}"):
                        st.write(f"**Professor(a):** {tema.get('professor_nome', 'A definir')}")
                        st.write(f"**Disciplina:** {tema.get('disciplina', 'Diversas')}")
                        if st.button("ESCOLHER ESTE TEMA", key=f"tema_{tema['id']}", use_container_width=True):
                            st.session_state.tema_selecionado = tema
                            st.session_state.passo_insc = 3
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar temas: {e}")

    # ==========================================
    # PASSO 3: COMPOSIÇÃO DO GRUPO
    # ==========================================
    elif st.session_state.passo_insc == 3:
        evento = st.session_state.evento_selecionado
        tema = st.session_state.tema_selecionado
        
        st.success(f"📍 **Inscrição iniciada:** {tema['titulo_trabalho']}")
        
        with st.form("form_final"):
            st.markdown("### 👥 Membros da Equipe")
            st.info(f"Regra: Mínimo {evento['min_membros']} e máximo {evento['max_membros']} alunos.")
            
            st.text_input("Líder (Você)", value=aluno.get('nome', ''), disabled=True)
            
            outros_membros = st.text_area(
                "Nomes dos demais integrantes", 
                placeholder="João Silva\nMaria Oliveira",
                help="Escreva um nome por linha."
            )
            
            # O BOTÃO DE INSCRIÇÃO QUE FALTAVA:
            submit = st.form_submit_button("CONCLUIR MINHA INSCRIÇÃO", type="primary", use_container_width=True)
            
            if submit:
                # Processar nomes
                lista_extra = [m.strip() for m in outros_membros.split('\n') if m.strip()]
                total_membros = len(lista_extra) + 1 # +1 do líder
                
                if total_membros < int(evento['min_membros']) or total_membros > int(evento['max_membros']):
                    st.error(f"❌ Quantidade de membros inválida! O evento exige entre {evento['min_membros']} e {evento['max_membros']} pessoas.")
                else:
                    with st.spinner("Gravando no banco de dados..."):
                        try:
                            # Montando o texto da equipe
                            equipe_completa = f"{aluno.get('nome')} (Líder)"
                            if lista_extra:
                                equipe_completa += ", " + ", ".join(lista_extra)
                            
                            dados_insc = {
                                "evento_id": evento['id'],
                                "tema_id": tema['id'],
                                "lider_id": id_aluno,
                                "turma": turma_aluno,
                                "nomes_membros": equipe_completa,
                                "data_inscricao": str(datetime.date.today())
                            }
                            
                            db_alunos.table("feira_inscricoes").insert(dados_insc).execute()
                            
                            st.balloons()
                            st.success("✅ Inscrição realizada com sucesso!")
                            time.sleep(3)
                            # Resetar e voltar ao menu
                            st.session_state.passo_insc = 1
                            st.session_state.etapa = "ante_sala"
                            st.rerun()
                        except Exception as e:
                            st.error(f"🚨 Erro ao salvar no Supabase: {e}")

        if st.button("⬅️ Mudar Tema"):
            st.session_state.passo_insc = 2
            st.rerun()

    # Sidebar para saída rápida
    st.sidebar.divider()
    if st.sidebar.button("🏠 Cancelar e Sair"):
        st.session_state.passo_insc = 1
        st.session_state.etapa = "ante_sala"
        st.rerun()