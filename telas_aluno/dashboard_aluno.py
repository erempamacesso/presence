import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # --- HEADER ---
    st.markdown(f'<div class="header-nome">Olá, {aluno["nome"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-turma">{aluno.get("turma", "Estudante")} • EREMPAM</div>', unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state.menu_ativo = "home"

    # ---------------------------------------------------------
    # TELA 1: MENU PRINCIPAL
    # ---------------------------------------------------------
    if st.session_state.menu_ativo == "home":
        if st.button("📝 Simulados Disponíveis", use_container_width=True):
            st.session_state.menu_ativo = "provas"; st.rerun()
            
        if st.button("✅ Atividades Concluídas", use_container_width=True):
            st.session_state.menu_ativo = "historico"; st.rerun()
            
        if st.button("📊 Meu Desempenho", use_container_width=True):
            st.session_state.menu_ativo = "notas"; st.rerun()
            
        st.write("") # Espaço
        
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.aluno = None; st.session_state.etapa = "login"; st.rerun()

    # ---------------------------------------------------------
    # TELA 2: PROVAS DISPONÍVEIS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "provas":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"; st.rerun()
            
        st.markdown('<div class="header-nome" style="font-size: 20px !important;">Simulados</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-turma">Provas disponíveis para você</div>', unsafe_allow_html=True)
        
        turma_aluno = str(aluno.get('turma', ''))
        serie_aluno = turma_aluno[:2] + " Ano" if len(turma_aluno) >= 2 else "1º Ano"

        try:
            res = db_provas.table("modelos_prova").select("*").eq("serie", serie_aluno).eq("ativa", True).execute()
            if res.data:
                for prova in res.data:
                    with st.container(border=True):
                        st.markdown(f"**{prova.get('titulo')}**")
                        if st.button(f"Iniciar Prova", key=f"start_{prova['id']}", type="primary", use_container_width=True):
                            st.session_state.prova_config = prova
                            st.session_state.etapa = "instrucoes"
                            st.rerun()
            else:
                st.info("Nenhuma prova disponível no momento.")
        except Exception as e:
            st.error(f"Erro ao buscar provas: {e}")

    # ---------------------------------------------------------
    # TELA 3: ATIVIDADES CONCLUÍDAS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "historico":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"; st.rerun()
            
        st.markdown('<div class="header-nome" style="font-size: 20px !important;">Conquistas</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-turma">Seu histórico de provas</div>', unsafe_allow_html=True)
        
        try:
            # Buscando usando o ID original do aluno (sem forçar string caso seja inteiro)
            res_c = db_provas.table("resultados_provas").select("*").eq("aluno_id", aluno['id']).execute()
            
            if res_c.data:
                provas_concluidas = {}
                for reg in res_c.data:
                    p_id = reg.get('prova_id')
                    if p_id and p_id not in provas_concluidas:
                        provas_concluidas[p_id] = reg

                ids_lista = list(provas_concluidas.keys())
                res_titulos = db_provas.table("modelos_prova").select("id, titulo").in_("id", ids_lista).execute()
                mapa_titulos = {p['id']: p['titulo'] for p in res_titulos.data} if res_titulos.data else {}

                for p_id, dados in provas_concluidas.items():
                    nome_atividade = mapa_titulos.get(p_id, f"Atividade {str(p_id)[:8]}")
                    
                    with st.container(border=True):
                        st.markdown(f"**✅ {nome_atividade}**")
                        data_r = str(dados.get('data_resposta', ''))[:10]
                        st.caption(f"Concluída em: {data_r}")
                        st.write(f"Acertos: `{dados.get('acertos', 0)}`")
                        
                        if st.button("Ver Diagnóstico Pedagógico", key=f"btn_feedback_{p_id}", use_container_width=True):
                            with st.status("Buscando análise da IA...", expanded=True):
                                res_f = db_provas.table("feedback_ia_alunos").select("diagnostico_pedagogico").eq("aluno_id", aluno['id']).eq("prova_id", p_id).execute()
                                if res_f.data:
                                    st.info(f"💡 {res_f.data[0].get('diagnostico_pedagogico', 'Sem detalhes.')}")
                                else:
                                    st.warning("Diagnóstico em processamento.")
            else:
                st.info("Você ainda não completou nenhuma atividade.")
        except Exception as e:
            st.error(f"Erro ao carregar histórico: {e}")

    # ---------------------------------------------------------
    # TELA 4: DESEMPENHO
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "notas":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"; st.rerun()
            
        mostrar_tela_desempenho(db_alunos, db_provas)