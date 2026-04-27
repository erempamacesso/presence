import streamlit as st
import time
from datetime import datetime
import re
import random
import ast

def limpar_html(html):
    """Remove tags HTML e limpa o texto para exibição pura."""
    if not html:
        return ""
    # Remove as tags, mas mantém o conteúdo entre elas
    texto_limpo = re.sub(r'<[^>]+>', '', str(html))
    return texto_limpo.strip()

def extrair_texto_alternativa(conteudo):
    """Descasca o dicionário do banco para pegar só o texto limpo da alternativa"""
    # 1. Se o banco já entregou como um dicionário Python real
    if isinstance(conteudo, dict):
        return str(conteudo.get('texto', conteudo))
    
    # 2. Se o banco entregou como um texto com "cara" de dicionário
    if isinstance(conteudo, str):
        conteudo = conteudo.strip()
        if conteudo.startswith("{") and "'texto'" in conteudo:
            try:
                # Converte o texto no formato de código de volta para dicionário
                dict_convertido = ast.literal_eval(conteudo)
                if isinstance(dict_convertido, dict):
                    return str(dict_convertido.get('texto', ''))
            except Exception:
                pass
                
    # 3. Se for apenas um texto normal (sem dicionário)
    return str(conteudo)

def render_instrucoes(supabase):
    """Tela de orientações antes de começar o cronômetro"""
    prova = st.session_state.get('prova_config')
    
    if not prova:
        st.error("Erro ao carregar configurações da prova.")
        return

    st.title(f"📝 {prova['titulo']}")
    st.info("Leia com atenção antes de começar!")

    st.markdown(f"""
    ### ⚠️ Regras da Avaliação:
    * **Questões:** Esta prova contém {len(prova['questoes_ids'])} questões.
    * **Randomização:** As alternativas aparecem em ordem aleatória para cada tentativa.
    * **Envio:** Uma vez iniciada, você deve concluir a prova.
    """)

    if st.button("🚀 INICIAR PROVA AGORA", type="primary", use_container_width=True):
        st.session_state.etapa = "em_prova"
        st.session_state.inicio_prova = datetime.now().isoformat()
        st.rerun()

def render_prova(supabase):
    """A tela principal onde o aluno faz a prova"""
    prova = st.session_state.get('prova_config')
    aluno = st.session_state.get('aluno')

    # 1. Busca as questões no banco
    ids = prova['questoes_ids']
    res = supabase.table("questoes").select("*").in_("id", ids).execute()
    questoes = res.data

    st.title(f"✍️ {prova['titulo']}")
    st.caption(f"Aluno: {aluno['nome']} | Turma: {aluno.get('turma', 'N/A')}")
    st.divider()

    if 'respostas_aluno' not in st.session_state:
        st.session_state.respostas_aluno = {}

    # 2. Exibição das Questões
    for i, q in enumerate(questoes, 1):
        st.subheader(f"Questão {i}")
        
        # EXIBIÇÃO DO ENUNCIADO (Mantendo as imagens)
        st.markdown(q['enunciado'], unsafe_allow_html=True)
        
        # 3. TRATAMENTO DAS ALTERNATIVAS
        opcoes_originais = q.get('alternativas') or q.get('opcoes') or {}
        
        mapeamento_alternativas = {}
        lista_para_exibir = []

        for letra, conteudo in opcoes_originais.items():
            # PASSO A: Retira o texto de dentro de {'texto': '...', 'imagem': ''}
            texto_extraido = extrair_texto_alternativa(conteudo)
            
            # PASSO B: Limpa qualquer HTML (<p>, <b>, etc) que tenha sobrado
            texto_puro = limpar_html(texto_extraido)
            
            # Evita adicionar opções totalmente em branco
            if texto_puro:
                lista_para_exibir.append(texto_puro)
                mapeamento_alternativas[texto_puro] = letra

        # RANDOMIZAÇÃO: Embaralha as alternativas para o aluno
        chave_random = f"random_{q['id']}"
        if chave_random not in st.session_state:
            random.shuffle(lista_para_exibir)
            st.session_state[chave_random] = lista_para_exibir
        
        opcoes_embaralhadas = st.session_state[chave_random]

        # Interface de marcação
        escolha_texto = st.radio(
            "Escolha a alternativa correta:",
            options=opcoes_embaralhadas,
            index=None,
            key=f"radio_{q['id']}"
        )
        
        if escolha_texto:
            # Salva a letra original (A, B, C...) baseada no texto que ele escolheu
            letra_real = mapeamento_alternativas[escolha_texto]
            st.session_state.respostas_aluno[str(q['id'])] = letra_real
        
        st.divider()

    # 4. Botão de Finalizar
    if st.button("🏁 FINALIZAR E ENVIAR PROVA", type="primary", use_container_width=True):
        if len(st.session_state.respostas_aluno) < len(questoes):
            st.warning(f"⚠️ Você respondeu apenas {len(st.session_state.respostas_aluno)} de {len(questoes)} questões. Tem certeza que quer enviar?")
            
        with st.spinner("Enviando respostas..."):
            dados_resultado = {
                "aluno_id": aluno['id'],
                "prova_id": prova['id'],
                "respostas": st.session_state.respostas_aluno,
                "data_envio": datetime.now().isoformat()
            }
            
            try:
                supabase.table("resultados_alunos").insert(dados_resultado).execute()
                st.session_state.etapa = "resultado_final"
                st.balloons()
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")