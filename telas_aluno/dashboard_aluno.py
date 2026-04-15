import streamlit as st
from telas_aluno.desempenho import mostrar_tela_desempenho

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno

    # --- HEADER ULTRA MINIMALISTA ---
    st.markdown(f'<div class="header-nome">Olá, {aluno["nome"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-turma">{aluno.get("turma", "Estudante")} • EREMPAM</div>', unsafe_allow_html=True)

    if "menu_ativo" not in st.session_state:
        st.session_state.menu_ativo = "home"

    # ---------------------------------------------------------
    # TELA 1: MENU PRINCIPAL (Lista Fina)
    # ---------------------------------------------------------
    if st.session_state.menu_ativo == "home":
        
        # Botões empilhados verticalmente (Estilo lista de configurações)
        if st.button("📝 Simulados Disponíveis", use_container_width=True):
            st.session_state.menu_ativo = "provas"; st.rerun()
            
        if st.button("✅ Atividades Concluídas", use_container_width=True):
            st.session_state.menu_ativo = "historico"; st.rerun()
            
        if st.button("📊 Meu Desempenho", use_container_width=True):
            st.session_state.menu_ativo = "notas"; st.rerun()
            
        st.write("") # Dá um pequeno espaço antes de sair
        
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.aluno = None; st.session_state.etapa = "login"; st.rerun()

    # ---------------------------------------------------------
    # TELA 2: PROVAS DISPONÍVEIS
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "provas":
        # Botão de voltar super discreto
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"; st.rerun()
            
        st.markdown('<div class="header-nome">Simulados</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-turma">Provas disponíveis para você</div>', unsafe_allow_html=True)
        
        # ... COLE AQUI A LÓGICA DE BUSCAR PROVAS ...
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
            
        st.markdown('<div class="header-nome">Conquistas</div>', unsafe_allow_html=True)
        st.markdown('<div class="header-turma">Seu histórico de provas</div>', unsafe_allow_html=True)
        
        # ... COLE AQUI A LÓGICA DE BUSCAR O HISTÓRICO QUE FIZEMOS ANTES ...
        # (Lembrando de usar a tabela resultados_provas e o loop das provas concluídas)

    # ---------------------------------------------------------
    # TELA 4: DESEMPENHO
    # ---------------------------------------------------------
    elif st.session_state.menu_ativo == "notas":
        if st.button("← Voltar ao Menu", use_container_width=True): 
            st.session_state.menu_ativo = "home"; st.rerun()
            
        mostrar_tela_desempenho(db_alunos, db_provas)