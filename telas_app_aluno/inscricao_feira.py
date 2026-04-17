import streamlit as st
import datetime
import time

def mostrar_tela_inscricao_feira(supabase_conn):
    # CSS para deixar a cara de "App Premium"
    st.markdown("""
        <style>
        .main { background-color: #f0f2f6; }
        .stButton>button { border-radius: 8px; height: 3em; transition: 0.3s; }
        .stButton>button:hover { transform: scale(1.02); }
        .event-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #00d4ff;
            margin-bottom: 20px;
        }
        .step-container {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        .step { color: #888; font-weight: bold; border-bottom: 2px solid #ddd; width: 30%; text-align: center; padding-bottom: 5px; }
        .step-active { color: #00d4ff; border-bottom: 2px solid #00d4ff; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Portal de Eventos EREMPAM")
    
    # --- Lógica de Navegação de Passos ---
    if 'passo' not in st.session_state:
        st.session_state.passo = 1
    
    # Indicador de progresso visual
    p1, p2, p3 = "step-active" if st.session_state.passo == 1 else "", \
                 "step-active" if st.session_state.passo == 2 else "", \
                 "step-active" if st.session_state.passo == 3 else ""
    
    st.markdown(f"""
        <div class="step-container">
            <div class="step {p1}">1. Escolher Evento</div>
            <div class="step {p2}">2. Selecionar Tema</div>
            <div class="step {p3}">3. Finalizar Equipe</div>
        </div>
    """, unsafe_allow_html=True)

    # Pegar dados do aluno
    aluno = st.session_state.get('aluno', {})
    turma = aluno.get('turma', 'Sem Turma')

    # ==========================================
    # PASSO 1: VITRINE DE EVENTOS
    # ==========================================
    if st.session_state.passo == 1:
        st.subheader("Eventos Disponíveis")
        try:
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
            if not res.data:
                st.info("Nenhum evento aberto no momento.")
            else:
                for ev in res.data:
                    with st.container():
                        st.markdown(f"""
                            <div class="event-card">
                                <h2 style='margin-top:0;'>{ev['nome']}</h2>
                                <p>🗓️ <b>Data:</b> {ev['data_inicio']} até {ev['data_fim']}</p>
                                <p>👥 <b>Equipes:</b> {ev['min_membros']} a {ev['max_membros']} integrantes</p>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Ver Temas de {ev['nome']}", key=ev['id'], use_container_width=True, type="primary"):
                            st.session_state.evento_sel = ev
                            st.session_state.passo = 2
                            st.rerun()
        except Exception as e:
            st.error(f"Erro na conexão: {e}")

    # ==========================================
    # PASSO 2: TEMAS
    # ==========================================
    elif st.session_state.passo == 2:
        ev = st.session_state.evento_sel
        st.subheader(f"Temas para: {ev['nome']}")
        
        if st.button("⬅️ Voltar"):
            st.session_state.passo = 1
            st.rerun()

        try:
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", ev['id']).execute()
            if not res_temas.data:
                st.warning("Aguardando cadastro de temas pelo professor.")
            else:
                for t in res_temas.data:
                    with st.expander(f"📙 {t['titulo_trabalho']}"):
                        st.write(f"**Professor:** {t['professor_nome']}")
                        st.write(f"**Disciplina:** {t['disciplina']}")
                        if st.button("Escolher este tema", key=f"t_{t['id']}", use_container_width=True):
                            st.session_state.tema_sel = t
                            st.session_state.passo = 3
                            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    # ==========================================
    # PASSO 3: GRUPO
    # ==========================================
    elif st.session_state.passo == 3:
        t = st.session_state.tema_sel
        st.success(f"Você escolheu: **{t['titulo_trabalho']}**")
        
        with st.form("form_final"):
            st.write("### 👥 Quem são os membros?")
            membros = st.text_area("Digite os nomes completos (um por linha)", placeholder="Ex:\nJoão Silva\nMaria Oliveira")
            
            if st.form_submit_button("CONCLUIR INSCRIÇÃO", use_container_width=True):
                # Aqui você insere no Supabase conforme sua lógica anterior
                st.balloons()
                st.success("Inscrição realizada com sucesso!")
                time.sleep(2)
                st.session_state.passo = 1
                st.rerun()
        
        if st.button("⬅️ Mudar Tema"):
            st.session_state.passo = 2
            st.rerun()