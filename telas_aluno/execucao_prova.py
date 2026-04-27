import streamlit as st
import time
from datetime import datetime

def render_instrucoes(supabase):
    """Tela de orientações antes de começar o cronômetro"""
    prova = st.session_state.get('prova_config')
    
    if not prova:
        st.error("Erro ao carregar configurações da prova.")
        if st.button("Voltar ao Início"):
            st.session_state.etapa = "home"
            st.rerun()
        return

    st.title(f"📝 {prova['titulo']}")
    st.info("Leia com atenção antes de começar!")

    st.markdown(f"""
    ### ⚠️ Regras da Avaliação:
    * **Questões:** Esta prova contém {len(prova['questoes_ids'])} questões.
    * **Pontuação:** Cada questão correta vale {prova.get('valor_questao', 1.0)} ponto(s).
    * **Envio:** Uma vez iniciada, você deve concluir a prova. Não feche o navegador.
    * **Gabarito:** O resultado será processado assim que você clicar em 'Finalizar'.
    """)

    if st.button("🚀 INICIAR PROVA AGORA", type="primary", use_container_width=True):
        st.session_state.etapa = "em_prova"
        st.session_state.inicio_prova = datetime.now().isoformat()
        st.rerun()

def render_prova(supabase):
    """A tela principal onde o aluno marca as respostas"""
    prova = st.session_state.get('prova_config')
    aluno = st.session_state.get('aluno')

    # 1. Busca as questões no banco usando os IDs salvos na prova
    ids = prova['questoes_ids']
    res = supabase.table("questoes").select("*").in_("id", ids).execute()
    questoes = res.data

    st.title(f"✍️ {prova['titulo']}")
    st.caption(f"Aluno: {aluno['nome']} | Turma: {aluno.get('turma', 'N/A')}")
    st.divider()

    # Criamos um dicionário para armazenar as respostas no session_state
    if 'respostas_aluno' not in st.session_state:
        st.session_state.respostas_aluno = {}

    # 2. Exibição das Questões
    for i, q in enumerate(questoes, 1):
        st.subheader(f"Questão {i}")
        st.markdown(q['enunciado'], unsafe_allow_html=True)
        
        # Puxa as alternativas (A, B, C, D, E)
        opcoes = q.get('alternativas') or q.get('opcoes') or {}
        lista_opcoes = []
        for letra in ["A", "B", "C", "D", "E"]:
            if letra in opcoes:
                # Remove tags HTML para exibir no botão de rádio
                texto_limpo = re_sub = __import__('re').sub('<[^>]+>', '', str(opcoes[letra]))
                lista_opcoes.append(f"{letra}) {texto_limpo}")

        # Interface de marcação
        escolha = st.radio(
            f"Selecione a resposta da {i}:",
            options=lista_opcoes,
            index=None,
            key=f"q_{q['id']}"
        )
        
        if escolha:
            letra_escolhida = escolha[0] # Pega apenas o "A", "B", etc.
            st.session_state.respostas_aluno[str(q['id'])] = letra_escolhida
        
        st.divider()

    # 3. Botão de Finalizar
    if st.button("🏁 FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True):
        if len(st.session_state.respostas_aluno) < len(questoes):
            st.warning(f"⚠️ Você respondeu {len(st.session_state.respostas_aluno)} de {len(questoes)} questões. Tem certeza que quer enviar?")
        
        with st.spinner("Processando seu resultado..."):
            # Lógica para salvar o resultado no banco
            dados_resultado = {
                "aluno_id": aluno['id'],
                "prova_id": prova['id'],
                "respostas": st.session_state.respostas_aluno,
                "data_envio": datetime.now().isoformat()
            }
            
            try:
                # Aqui você salva na sua tabela de resultados (ex: 'resultados_alunos')
                supabase.table("resultados_alunos").insert(dados_resultado).execute()
                
                st.session_state.etapa = "resultado_final"
                st.balloons()
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar suas respostas: {e}")