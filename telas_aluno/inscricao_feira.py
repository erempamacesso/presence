import streamlit as st

def mostrar_tela_inscricao_feira(supabase_conn):
    st.title("🎪 Inscrição - Feira de Ciências")
    
    # 1. Pega os dados do aluno que já fez login (guardados no App_Aluno.py)
    aluno = st.session_state.get('aluno', {})
    nome_aluno = aluno.get('nome', 'Aluno')
    # ATENÇÃO: Ajuste a chave 'turma' conforme o nome da coluna no seu banco de dados de alunos
    turma_do_aluno = aluno.get('turma', 'Turma Desconhecida') 
    
    st.write(f"Bem-vindo(a) Líder, **{nome_aluno}**!")
    st.info(f"📍 Sua turma atual: **{turma_do_aluno}**")
    
    # 2. FUTURO: Aqui faremos a consulta real no Supabase para ver o que a turma já pegou
    # Por enquanto, uma lista vazia para simular que tudo está disponível
    segmentos_ja_escolhidos_pela_turma = [] 
    
    st.markdown("### Escolha o Segmento do seu Grupo")
    
    segmentos = ["🧪 Química", "⚛️ Física", "🧬 Biologia", "📐 Matemática"]
    
    # 3. Lógica do Expander (Sanfona)
    for segmento in segmentos:
        nome_puro = segmento.split(" ")[1] # Corta o emoji e pega só a palavra (Química, Física...)
        
        # Se a turma já pegou esse segmento, mostra bloqueado
        if nome_puro in segmentos_ja_escolhidos_pela_turma:
            with st.expander(f"🔒 {segmento} (Indisponível para o {turma_do_aluno})"):
                st.error(f"⚠️ Um grupo da sua turma ({turma_do_aluno}) já garantiu um tema de {nome_puro}.")
                st.info("Por favor, escolha uma disciplina diferente.")
                
        # Se estiver livre, mostra os temas
        else:
            with st.expander(f"📂 {segmento} (Disponível)"):
                st.write(f"**Temas disponíveis para {nome_puro}:**")
                
                # FUTURO: Aqui faremos um SELECT no Supabase para listar só os temas de {nome_puro}
                tema_escolhido = st.radio(
                    "Selecione o tema para o seu grupo:",
                    ["Tema Exemplo A", "Tema Exemplo B", "Tema Exemplo C"],
                    key=f"radio_{nome_puro}"
                )
                
                st.write("") # Espaçador
                if st.button(f"✅ Prosseguir com {nome_puro}", key=f"btn_{nome_puro}", type="primary"):
                    # Aqui vamos guardar o tema escolhido e ir para a tela de adicionar os colegas
                    st.session_state.tema_selecionado = tema_escolhido
                    st.success(f"Boa escolha! Em breve, tela para selecionar os membros do grupo...")
                    # st.session_state.etapa = "adicionar_membros_feira"
                    # st.rerun()

    # 4. Botão de voltar ao painel principal
    st.divider()
    if st.button("⬅️ Voltar ao Painel"):
        st.session_state.etapa = "ante_sala" # O nome da etapa do dashboard no seu App_Aluno
        st.rerun()