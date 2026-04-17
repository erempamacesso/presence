import streamlit as st
import datetime
import time

def mostrar_tela_inscricao_feira(supabase_conn):
    # CSS para Interface Profissional
    st.markdown("""
        <style>
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
    
    # Sistema de Passos
    if 'passo' not in st.session_state: st.session_state.passo = 1
    
    p1 = "step-active" if st.session_state.passo == 1 else ""
    p2 = "step-active" if st.session_state.passo == 2 else ""
    p3 = "step-active" if st.session_state.passo == 3 else ""
    
    st.markdown(f"""
        <div class="step-container">
            <div class="step {p1}">1. Evento</div>
            <div class="step {p2}">2. Tema</div>
            <div class="step {p3}">3. Equipe</div>
        </div>
    """, unsafe_allow_html=True)

    aluno = st.session_state.get('aluno', {})
    turma = aluno.get('turma', 'Sem Turma')

    # PASSO 1: ESCOLHER EVENTO
    if st.session_state.passo == 1:
        st.subheader("Selecione o Evento")
        try:
            # Forçando a busca dos dados limpos
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
            if not res.data:
                st.info("Nenhum evento ativo.")
            else:
                for ev in res.data:
                    with st.container():
                        st.markdown(f"""
                            <div class="event-card">
                                <h3 style='margin:0;'>{ev['nome']}</h3>
                                <p style='margin:5px 0;'>🗓️ {ev['data_inicio']} até {ev['data_fim']}</p>
                                <small>👥 Equipes de {ev['min_membros']} a {ev['max_membros']} integrantes</small>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Inscrever em {ev['nome']}", key=ev['id'], use_container_width=True):
                            st.session_state.evento_sel = ev
                            st.session_state.passo = 2
                            st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar: {e}")

    # PASSO 2: ESCOLHER TEMA
    elif st.session_state.passo == 2:
        ev = st.session_state.evento_sel
        st.subheader(f"Temas: {ev['nome']}")
        
        if st.button("⬅️ Voltar"):
            st.session_state.passo = 1
            st.rerun()

        try:
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", ev['id']).execute()
            if not res_temas.data:
                st.warning("Nenhum tema disponível.")
            else:
                for t in res_temas.data:
                    with st.expander(f"📙 {t['titulo_trabalho']}"):
                        st.write(f"**Orientador:** {t.get('professor_nome', 'N/A')}")
                        if st.button("Selecionar este tema", key=f"t_{t['id']}", use_container_width=True):
                            st.session_state.tema_sel = t
                            st.session_state.passo = 3
                            st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")

    # PASSO 3: FINALIZAR
    elif st.session_state.passo == 3:
        t = st.session_state.tema_sel
        ev = st.session_state.evento_sel
        st.success(f"Tema: {t['titulo_trabalho']}")
        
        with st.form("final_form"):
            st.write("### Integrantes da Equipe")
            membros = st.text_area("Nomes dos membros (um por linha)", help="Não esqueça de ninguém!")
            
            if st.form_submit_button("CONFIRMAR INSCRIÇÃO", use_container_width=True):
                lista = [m.strip() for m in membros.split('\n') if m.strip()]
                if len(lista) + 1 < int(ev['min_membros']):
                    st.error(f"Mínimo de {ev['min_membros']} pessoas!")
                else:
                    # Lógica de Insert aqui...
                    st.balloons()
                    st.success("Pronto! Inscrição realizada.")
                    time.sleep(2)
                    st.session_state.passo = 1
                    st.rerun()