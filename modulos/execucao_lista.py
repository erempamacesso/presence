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
    Se o aluno errou, seja encorajador e dê uma dica memorável.
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
# 📝 TELA DE EXECUÇÃO INTERATIVA (QUIZ)
# ==========================================
def exibir_execucao_lista(supabase):
    # Puxa a lista selecionada pelo aluno no dashboard
    lista = st.session_state.get("lista_config")

    if not lista:
        st.warning("⚠️ Nenhuma lista de exercícios foi selecionada no painel.")
        if st.button("Voltar ao Menu"):
            st.session_state.etapa = "ante_sala"
            st.rerun()
        return

    st.title(f"🏋️ Exercício de Treino: {lista.get('titulo', 'Lista Sem Título')}")
    st.caption(
        "Aqui você pode treinar livremente. Erros não geram notas ou penalidades!"
    )

    # Inicializa os estados da sessão do estudante
    if "respostas_treino" not in st.session_state:
        st.session_state.respostas_treino = {}
    if "corrigido" not in st.session_state:
        st.session_state.corrigido = False

    # Busca as questões no Supabase com base nos IDs salvos na lista
    ids_questoes = lista.get("questoes_ids", [])
    if not ids_questoes:
        st.error("Esta lista não possui questões cadastradas.")
        return

    # Garante que as questões fiquem salvas na sessão para não mudarem de ordem a cada clique
    if "questoes_treino_carregadas" not in st.session_state:
        with st.spinner("Carregando banco de questões..."):
            res = (
                supabase.table("questoes").select("*").in_("id", ids_questoes).execute()
            )
            st.session_state.questoes_treino_carregadas = res.data

    questoes = st.session_state.questoes_treino_carregadas

    # RENDERIZAÇÃO DAS PERGUNTAS
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

            # Monta a lista de opções para o st.radio
            opcoes = []
            mapeamento_letras = {}
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in alts:
                    texto_limpo = extrair_texto_alternativa(alts[letra])
                    label = f"({letra}) {texto_limpo}"
                    opcoes.append(label)
                    mapeamento_letras[label] = letra

            # Descobre se o aluno já tinha marcado algo antes
            idx_selecionado = None
            resposta_previa = st.session_state.respostas_treino.get(id_q)
            if resposta_previa:
                for i_opt, opt_txt in enumerate(opcoes):
                    if opt_txt.startswith(f"({resposta_previa})"):
                        idx_selecionado = i_opt

            # Componente de escolha do aluno (Bloqueia se já clicou em corrigir)
            escolha_label = st.radio(
                f"Escolha sua resposta para a questão {idx+1}:",
                options=opcoes,
                index=idx_selecionado,
                key=f"treino_q_{id_q}",
                disabled=st.session_state.corrigido,
                label_visibility="collapsed",
            )

            # Grava o voto no estado da sessão
            if escolha_label:
                st.session_state.respostas_treino[id_q] = mapeamento_letras[
                    escolha_label
                ]

            # 🟢 🔴 LOGICA DE EXIBIÇÃO DO GABARITO (APÓS A CORREÇÃO)
            if st.session_state.corrigido:
                gabarito_oficial = (
                    str(q.get("resposta_correta") or q.get("gabarito")).strip().upper()
                )
                voto_aluno = (
                    st.session_state.respostas_treino.get(id_q, "").strip().upper()
                )

                if voto_aluno == gabarito_oficial:
                    st.success(
                        f"🎯 **Você Acertou!** Parabéns, a alternativa correta é mesmo a **({gabarito_oficial})**."
                    )
                else:
                    st.error(
                        f"❌ **Resposta Incorreta.** Você marcou a alternativa **({voto_aluno})**, mas o gabarito correto é a **({gabarito_oficial})**."
                    )

                # BOTÃO DO TUTOR INTELIGENTE
                if st.button(f"✨ Explicar com Tutor MarIO", key=f"btn_ai_{id_q}"):
                    with st.spinner("O Tutor MarIO está analisando seu treino..."):
                        txt_voto = (
                            f"Alternativa {voto_aluno}" if voto_aluno else "Nenhuma"
                        )
                        explicacao = explicar_com_ia(
                            enunciado_puro, txt_voto, gabarito_oficial
                        )
                        st.info(f"🤖 **Tutor MarIO:** {explicacao}")

    st.divider()

    # ==========================================
    # 🔘 BARRA DE BOTÕES DE CONTROLE GERAL
    # ==========================================
    col1, col2 = st.columns(2)

    if not st.session_state.corrigido:
        # Modo Resolução
        if col1.button(
            "🔍 CORRIGIR EXERCÍCIOS E VER GABARITO",
            type="primary",
            use_container_width=True,
        ):
            if len(st.session_state.respostas_treino) < len(questoes):
                st.warning(
                    "⚠️ Atenção: Responda todas as perguntas antes de solicitar a correção!"
                )
            else:
                st.session_state.corrigido = True
                st.rerun()
    else:
        # Modo Correção Ativo
        if col1.button("🔄 Refazer Treino (Resetar)", use_container_width=True):
            st.session_state.corrigido = False
            st.session_state.respostas_treino = {}
            st.rerun()

    if col2.button("⬅️ Sair do Treino", type="secondary", use_container_width=True):
        # Limpa caches temporários de treino e volta para a tela inicial
        keys_para_limpar = [
            "questoes_treino_carregadas",
            "respostas_treino",
            "corrigido",
            "lista_config",
        ]
        for k in keys_para_limpar:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.etapa = "ante_sala"
        st.rerun()
