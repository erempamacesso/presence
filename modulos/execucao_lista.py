import streamlit as st
import google.generativeai as genai
import re
import ast


# ==========================================
# 🤖 CONFIGURAÇÃO DO TUTOR IA (CACHED)
# ==========================================
@st.cache_resource
def configurar_tutor_ia():
    """Configura o modelo Gemini via Secrets de forma otimizada para não cair."""
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Chave GEMINI_API_KEY não configurada nos Secrets do Streamlit.")
        return None
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")


def explicar_com_ia(enunciado, resposta_aluno, resposta_correta):
    model = configurar_tutor_ia()
    if not model:
        return "Erro na configuração da IA."

    prompt = f"""
    Você é o Tutor MarIO, um professor empático, motivador e focado em aprendizado ativo. 
    O aluno está treinando e quer entender uma questão.
    ENUNCIADO: {enunciado}
    RESPOSTA DO ALUNO: {resposta_aluno}
    GABARITO CORRETO: {resposta_correta}

    Explique de forma curta (3 a 4 linhas no máximo) o raciocínio correto. 
    Se o aluno errou, seja encorajador e dê uma dica memorável para ele fixar o conteúdo.
    """
    try:
        config = genai.types.GenerationConfig(max_output_tokens=200, temperature=0.7)
        resposta = model.generate_content(prompt, generation_config=config)
        return resposta.text
    except Exception as e:
        return f"O Tutor MarIO está um pouco ocupado agora, mas a resposta certa é a alternativa {resposta_correta}!"


# ==========================================
# 🛠️ HELPERS DE LIMPEZA E TRATAMENTO
# ==========================================
def limpar_html(html):
    if not html:
        return ""
    return re.sub(r"<[^>]+>", "", str(html)).strip()


def extrair_texto_alternativa(conteudo):
    if isinstance(conteudo, dict):
        return str(conteudo.get("texto", conteudo))
    if isinstance(conteudo, str):
        conteudo = conteudo.strip()
        if conteudo.startswith("{") and "'texto'" in conteudo:
            try:
                dict_convertido = ast.literal_eval(conteudo)
                if isinstance(dict_convertido, dict):
                    return str(dict_convertido.get("texto", ""))
            except:
                pass
    return str(conteudo)


# ==========================================
# 📝 TELA DE EXECUÇÃO COM FILTROS DINÂMICOS
# ==========================================
def exibir_execucao_lista(supabase):
    st.title("🏋️ Centro de Treino Livre")
    st.caption(
        "Escolha os filtros, responda as questões e use o Tutor MarIO para tirar dúvidas!"
    )

    # 1. Recupera dados do aluno logado para definir os filtros padrões
    aluno_logado = st.session_state.get("aluno", {})
    serie_padrao = aluno_logado.get("serie", "1º ANO")
    turma_padrao = aluno_logado.get("turma", "A")

    # 2. Inicialização dos estados de controle da sessão
    if "respostas_treino" not in st.session_state:
        st.session_state.respostas_treino = {}
    if "corrigido" not in st.session_state:
        st.session_state.corrigido = False
    if "treino_carregado" not in st.session_state:
        st.session_state.treino_carregado = False
    if "questoes_treino_filtradas" not in st.session_state:
        st.session_state.questoes_treino_filtradas = []

    # ==========================================
    # 🔍 PAINEL DE FILTROS (SÉRIE E TURMA)
    # ==========================================
    # Só exibe as caixas de seleção se o aluno ainda não começou o treino ou resetou
    if not st.session_state.treino_carregado:
        with st.form("painel_filtros_treino"):
            st.subheader("Configurar Filtros de Exercícios")
            col1, col2 = st.columns(2)

            # Listas de opções (ajuste conforme a realidade da sua escola)
            lista_series = ["1º ANO", "2º ANO", "3º ANO", "9º ANO", "EJA"]
            lista_turmas = ["A", "B", "C", "D", "ÚNICA"]

            # Define o index padrão baseado no cadastro do aluno
            idx_s = (
                lista_series.index(serie_padrao) if serie_padrao in lista_series else 0
            )
            idx_t = (
                lista_turmas.index(turma_padrao) if turma_padrao in lista_turmas else 0
            )

            serie_selecionada = col1.selectbox(
                "Selecione a Série:", lista_series, index=idx_s
            )
            turma_selecionada = col2.selectbox(
                "Selecione a Turma:", lista_turmas, index=idx_t
            )

            limite_questoes = st.slider(
                "Quantidade máxima de questões:", min_value=2, max_value=20, value=5
            )

            botao_buscar = st.form_submit_button(
                "🎲 GERAR LISTA DE EXERCÍCIOS", type="primary", use_container_width=True
            )

            if botao_buscar:
                with st.spinner("Buscando questões correspondentes no Supabase..."):
                    try:
                        # Roda a consulta filtrando por serie e turma direto na tabela 'questoes'
                        # NOTA: Certifique-se de que a coluna 'turma' exista na sua tabela 'questoes'.
                        # Se a sua tabela 'questoes' possuir apenas a coluna 'serie', remova o .eq("turma", ...) abaixo.
                        res = (
                            supabase.table("questoes")
                            .select("*")
                            .eq("serie", serie_selecionada)
                            .eq("turma", turma_selecionada)
                            .limit(limite_questoes)
                            .execute()
                        )

                        if res.data:
                            st.session_state.questoes_treino_filtradas = res.data
                            st.session_state.treino_carregado = True
                            st.session_state.respostas_treino = {}
                            st.session_state.corrigido = False
                            st.rerun()
                        else:
                            st.warning(
                                f"Não encontramos questões cadastradas para o {serie_selecionada} - Turma {turma_selecionada}."
                            )
                    except Exception as e:
                        st.error(f"Erro ao consultar tabela de questões: {e}")
        return

    # ==========================================
    # 📝 EXIBIÇÃO E RESOLUÇÃO DOS EXERCÍCIOS
    # ==========================================
    questoes = st.session_state.questoes_treino_filtradas
    st.info(f"📋 Treinando com **{len(questoes)}** questões selecionadas do banco.")

    for idx, q in enumerate(questoes):
        id_q = str(q["id"])

        with st.container(border=True):
            st.markdown(f"### Questão {idx + 1}")
            enunciado_puro = limpar_html(q.get("enunciado", ""))
            st.write(enunciado_puro)

            # Processamento das alternativas (JSON do Banco para Dicionário)
            alts = q.get("alternativas", {})
            if isinstance(alts, str):
                try:
                    alts = ast.literal_eval(alts)
                except:
                    alts = {}

            # Monta as opções textuais do st.radio
            opcoes = []
            mapeamento_letras = {}
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in alts:
                    texto_limpo = extrair_texto_alternativa(alts[letra])
                    label = f"({letra}) {texto_limpo}"
                    opcoes.append(label)
                    mapeamento_letras[label] = letra

            # Preserva o estado caso o aluno já tenha clicado em alguma alternativa
            idx_selecionado = None
            resposta_previa = st.session_state.respostas_treino.get(id_q)
            if resposta_previa:
                for i_opt, opt_txt in enumerate(opcoes):
                    if opt_txt.startswith(f"({resposta_previa})"):
                        idx_selecionado = i_opt

            # Renderiza as alternativas. Fica desabilitado após a correção.
            escolha_label = st.radio(
                f"Alternativas para a questão {idx+1}:",
                options=opcoes,
                index=idx_selecionado,
                key=f"dinamico_q_{id_q}",
                disabled=st.session_state.corrigido,
                label_visibility="collapsed",
            )

            if escolha_label:
                st.session_state.respostas_treino[id_q] = mapeamento_letras[
                    escolha_label
                ]

            # 🟢 🔴 APRESENTAÇÃO DO GABARITO (PÓS-CORREÇÃO)
            if st.session_state.corrigido:
                gabarito_oficial = (
                    str(q.get("resposta_correta") or q.get("gabarito")).strip().upper()
                )
                voto_aluno = (
                    st.session_state.respostas_treino.get(id_q, "").strip().upper()
                )

                if voto_aluno == gabarito_oficial:
                    st.success(
                        f"🎯 **Você Acertou!** A alternativa correta é a **({gabarito_oficial})**."
                    )
                else:
                    st.error(
                        f"❌ **Resposta Incorreta.** Você marcou a alternativa **({voto_aluno})**, mas o gabarito correto é a **({gabarito_oficial})**."
                    )

                # BOTÃO INDIVIDUAL DO TUTOR IA
                if st.button(
                    f"✨ Pedir explicação ao Tutor MarIO", key=f"btn_ai_dinamico_{id_q}"
                ):
                    with st.spinner("O Tutor MarIO está analisando a questão..."):
                        txt_voto = (
                            f"Alternativa {voto_aluno}"
                            if voto_aluno
                            else "Não respondeu"
                        )
                        explicacao = explicar_com_ia(
                            enunciado_puro, txt_voto, gabarito_oficial
                        )
                        st.info(f"🤖 **Tutor MarIO:** {explicacao}")

    st.divider()

    # ==========================================
    # 🔘 BOTÕES DE CONTROLE INFERIOR
    # ==========================================
    col_b1, col_b2 = st.columns(2)

    if not st.session_state.corrigido:
        if col_b1.button(
            "🔍 CORRIGIR EXERCÍCIOS E VER GABARITO",
            type="primary",
            use_container_width=True,
        ):
            if len(st.session_state.respostas_treino) < len(questoes):
                st.warning(
                    "⚠️ Responda todas as perguntas antes de solicitar a correção!"
                )
            else:
                st.session_state.corrigido = True
                st.rerun()
    else:
        if col_b1.button(
            "🔄 Escolher Outros Filtros / Novo Treino", use_container_width=True
        ):
            # Reseta todos os estados para voltar à tela de seleção de Série/Turma
            st.session_state.treino_carregado = False
            st.session_state.corrigido = False
            st.session_state.respostas_treino = {}
            st.session_state.questoes_treino_filtradas = []
            st.rerun()

    if col_b2.button(
        "⬅️ Sair do Centro de Treino", type="secondary", use_container_width=True
    ):
        # Limpa a memória e volta para a tela inicial do aluno
        keys_limpeza = [
            "questoes_treino_filtradas",
            "respostas_treino",
            "corrigido",
            "treino_carregado",
        ]
        for k in keys_limpeza:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.etapa = "ante_sala"
        st.rerun()
