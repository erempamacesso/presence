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
            
        with st.spinner("Corrigindo e enviando respostas..."):
            
            # Cria uma lista para salvar cada resposta separadamente, como o banco exige
            dados_insercao = []
            
            for q in questoes:
                id_questao = str(q['id'])
                letra_marcada = st.session_state.respostas_aluno.get(id_questao)
                
                # Descobre qual era a resposta certa para avaliar se o aluno acertou
                gabarito = q.get('resposta_correta') or q.get('gabarito') or q.get('resposta')
                acertou = False
                
                # Compara a resposta do aluno com o gabarito
                if letra_marcada and gabarito:
                    if str(letra_marcada).strip().upper() == str(gabarito).strip().upper():
                        acertou = True
                
                # Monta a "linha" exata de dados que a tabela resultados_provas espera
                linha = {
                    "aluno_id": str(aluno['id']),
                    "prova_id": str(prova['id']),
                    "questao_id": id_questao,
                    "resposta_aluno": letra_marcada if letra_marcada else None,
                    "acertou": acertou
                }
                dados_insercao.append(linha)
            
            try:
                # Salva todas as respostas de uma vez na tabela correta
                supabase.table("resultados_provas").insert(dados_insercao).execute()
                
                st.session_state.etapa = "resultado_final"
                st.balloons()
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no banco de dados: {e}")