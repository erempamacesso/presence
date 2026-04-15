import streamlit as st

# Tenta importar a tela de desempenho que fizemos anteriormente
try:
    from telas_aluno.desempenho import mostrar_tela_desempenho
except ImportError:
    pass

def mostrar_tela_dashboard(db_alunos, db_provas):
    aluno = st.session_state.aluno
    nome = aluno.get('nome', 'Aluno(a)')

    # Cria um controle interno para saber qual "aba" do dashboard mostrar
    if 'aba_atual' not in st.session_state:
        st.session_state.aba_atual = 'menu_principal'

    # -------------------------------------------------------------
    # 1. TELA PRINCIPAL (OS BOTÕES GRANDES)
    # -------------------------------------------------------------
    if st.session_state.aba_atual == 'menu_principal':
        st.markdown(f"### Olá, **{nome}**! 👋")
        st.write("O que você deseja fazer hoje?")

        # Criando o grid 2x2 igual ao Print 2
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝 Simulados Disponíveis", use_container_width=True):
                st.session_state.aba_atual = 'simulados'
                st.rerun()
            
            if st.button("📊 Meu Desempenho", use_container_width=True):
                st.session_state.aba_atual = 'desempenho'
                st.rerun()
                
        with col2:
            if st.button("✅ Atividades Concluídas", use_container_width=True):
                st.session_state.aba_atual = 'atividades'
                st.rerun()
                
            # O botão de Logout agora vive aqui dentro!
            if st.button("🚪 Sair do Portal", use_container_width=True):
                st.session_state.aluno = None
                st.session_state.etapa = "login"
                st.session_state.aba_atual = 'menu_principal'
                st.rerun()

    # -------------------------------------------------------------
    # 2. SUB-TELAS (O QUE ACONTECE QUANDO CLICA NOS BOTÕES)
    # -------------------------------------------------------------
    elif st.session_state.aba_atual == 'simulados':
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            st.session_state.aba_atual = 'menu_principal'
            st.rerun()
        st.divider()
        st.subheader("📝 Simulados Disponíveis")
        
        # COLE AQUI O SEU CÓDIGO ANTIGO DE LISTAR AS PROVAS
        st.info("Aqui vai aparecer a lista de provas disponíveis para o aluno.")

    elif st.session_state.aba_atual == 'atividades':
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            st.session_state.aba_atual = 'menu_principal'
            st.rerun()
        st.divider()
        st.subheader("✅ Atividades Concluídas")
        
        # COLE AQUI O SEU CÓDIGO ANTIGO DE ATIVIDADES
        st.info("Aqui você lista as provas já feitas.")

    elif st.session_state.aba_atual == 'desempenho':
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            st.session_state.aba_atual = 'menu_principal'
            st.rerun()
        st.divider()
        
        # Renderiza a tela de desempenho sensacional que fizemos hoje
        try:
            mostrar_tela_desempenho(db_alunos, db_provas)
        except Exception as e:
            st.error(f"Erro ao carregar notas: {e}")