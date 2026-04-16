import streamlit as st

def mostrar_ante_sala():
    # Puxa o nome do aluno que logou
    aluno = st.session_state.get('aluno', {})
    nome = aluno.get('nome', 'Estudante').split()[0] # Pega só o primeiro nome
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center;'>Olá, {nome}! 👋</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #666;'>Bem-vindo ao Ecossistema EREMPAM. Onde você deseja ir hoje?</p>", unsafe_allow_html=True)
    
    st.divider()
    
    # Centralizando os cartões
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # CARTÃO 1: EVENTOS E FEIRAS (Fica dentro desse mesmo App)
        with st.container(border=True):
            st.markdown("### 🎪 Eventos e Feiras")
            st.write("Inscreva seu grupo em feiras de ciências, olimpíadas e mostra de conhecimentos.")
            if st.button("Acessar Inscrições", type="primary", use_container_width=True):
                st.session_state.etapa = "inscricao_feira"
                st.rerun()
        
        st.write("") # Espaço
        
        # CARTÃO 2: PORTAL DE ATIVIDADES (Manda para o OUTRO App)
        with st.container(border=True):
            st.markdown("### 📝 Portal de Atividades")
            st.write("Acesse seus simulados, gabaritos e diagnósticos gerados por Inteligência Artificial.")
            
            # ATENÇÃO: Substitua o link abaixo pelo link real do seu app principal de notas!
            link_app_provas = "https://seu-app-de-provas.streamlit.app" 
            st.link_button("Ir para Atividades ↗", link_app_provas, use_container_width=True)
            
        st.divider()
        if st.button("🚪 Sair da Conta", use_container_width=True):
            st.session_state.clear()
            st.rerun()