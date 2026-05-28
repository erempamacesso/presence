import streamlit as st
import google.generativeai as genai
import re
import ast


# ==========================================
# 🤖 CONFIGURAÇÃO DO TUTOR IA (CACHED)
# ==========================================
@st.cache_resource
def configurar_tutor_ia():
    """Configura o modelo Gemini via Secrets de forma otimizada."""
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
    Você é o Tutor MarIO, um professor especialista em resolução de questões.
    O aluno está estudando por questões e precisa de um comentário sobre esta:
    
    ENUNCIADO: {enunciado}
    O ALUNO MARCOU: {resposta_aluno}
    GABARITO OFICIAL: {resposta_correta}

    Explique de forma pedagógica, direta e curta (máximo 4 linhas) por que o gabarito é a {resposta_correta}. 
    Se o aluno marcou errado, explique sutilmente o erro da alternativa dele.
    """
    try:
        config = genai.types.GenerationConfig(max_output_tokens=250, temperature=0.7)
        resposta = model.generate_content(prompt, generation_config=config)
        return resposta.text
    except Exception as e:
        return (
            f"⚠️ O Tutor MarIO está ocupado agora. "
            f"Lembre-se: o gabarito correto é a alternativa {resposta_correta}!"
        )


# ==========================================
# 🛠️ HELPERS DE LIMPEZA
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
            except Exception:
                pass
    return str(conteudo)


# ==========================================
# 🔍 CARREGAMENTO DE SÉRIES DISPONÍVEIS
# ==========================================
@st.cache_data(ttl=300)
def carregar_series(_supabase):
    """Busca todas as séries únicas da tabela questoes. Cache de 5 minutos."""
    try:
        res = _supabase.table("questoes").select("serie").execute()
        if res.data:
            series = sorted(set(q["serie"] for q in res.data if q.get("serie")))
            return series
    except Exception as e:
        st.error(f"Erro ao carregar séries: {e}")
    return []


# ==========================================
# 📋 PAINEL DE FILTROS
# ==========================================
def exibir_painel_filtros(supabase):
    """
    Exibe o painel lateral (ou expandido) de filtros.
    Retorna (series_selecionadas, quantidade) ou None se o aluno ainda
    não confirmou o início.
    """
    st.title("📚 Treino de Questões")
    st.write("Selecione os filtros e clique em **Iniciar Treino**.")

    series_disponiveis = carregar_series(supabase)

    if not series_disponiveis:
        st.warning("Nenhuma série encontrada no banco de dados.")
        return None

    series_selecionadas = st.multiselect(
        "Filtrar por Série",
        options=series_disponiveis,
        default=[],
        placeholder="Todas as séries (sem filtro)",
    )

    quantidade = st.slider(
        "Quantidade de questões",
        min_value=5,
        max_value=50,
        value=10,
        step=5,
    )

    if st.button("🚀 Iniciar Treino", type="primary", use_container_width=True):
        return series_selecionadas, quantidade

    return None


# ==========================================
# 📦 CARREGAMENTO DE QUESTÕES
# ==========================================
def carregar_questoes(supabase, series_selecionadas, quantidade):
    """
    Busca questões do banco. Filtra por série se fornecido,
    ordena aleatoriamente e limita pela quantidade escolhida.
    """
    try:
        query = supabase.table("questoes").select("*")

        if series_selecionadas:
            query = query.in_("serie", series_selecionadas)

        # Ordena aleatoriamente pelo Postgres e limita
        res = query.limit(quantidade * 3).execute()  # Pega mais para poder embaralhar

        if not res.data:
            return []

        import random

        dados = res.data[:]
        random.shuffle(dados)
        return dados[:quantidade]

    except Exception as e:
        st.error(f"Erro ao carregar questões: {e}")
        return []


# ==========================================
# 📝 TELA DE EXECUÇÃO DA LISTA
# ==========================================
def exibir_execucao_lista(supabase):
    """
    Página principal de resolução de questões.
    Gerencia dois estados internos:
      - "filtros": mostra o painel de seleção
      - "respondendo": mostra as questões carregadas
    """

    # --- INICIALIZAÇÃO DO ESTADO INTERNO DA PÁGINA ---
    if "exec_estado" not in st.session_state:
        st.session_state.exec_estado = "filtros"

    if "exec_respondidas" not in st.session_state:
        # { id_questao: letra_marcada }
        st.session_state.exec_respondidas = {}

    if "exec_comentarios" not in st.session_state:
        # { id_questao: texto_comentario }  ← FIX: persiste os comentários da IA
        st.session_state.exec_comentarios = {}

    if "exec_questoes" not in st.session_state:
        st.session_state.exec_questoes = []

    # ==========================================
    # ESTADO 1: PAINEL DE FILTROS
    # ==========================================
    if st.session_state.exec_estado == "filtros":
        resultado = exibir_painel_filtros(supabase)

        if resultado is not None:
            series_sel, qtd = resultado
            with st.spinner("Carregando questões..."):
                questoes = carregar_questoes(supabase, series_sel, qtd)

            if not questoes:
                st.error(
                    "Nenhuma questão encontrada com os filtros selecionados. "
                    "Tente outras séries ou aumente a quantidade."
                )
            else:
                # Salva e muda de estado
                st.session_state.exec_questoes = questoes
                st.session_state.exec_respondidas = {}
                st.session_state.exec_comentarios = {}
                st.session_state.exec_estado = "respondendo"
                st.rerun()

        return  # Aguarda interação no painel de filtros

    # ==========================================
    # ESTADO 2: RESOLUÇÃO DAS QUESTÕES
    # ==========================================
    questoes = st.session_state.exec_questoes

    if not questoes:
        st.warning("Nenhuma questão carregada. Volte aos filtros.")
        if st.button("⬅️ Voltar aos Filtros"):
            st.session_state.exec_estado = "filtros"
            st.rerun()
        return

    # Calcula progresso
    total = len(questoes)
    respondidas = len(st.session_state.exec_respondidas)
    acertos = sum(
        1
        for id_q, letra in st.session_state.exec_respondidas.items()
        for q in questoes
        if str(q["id"]) == id_q
        and letra
        == str(q.get("resposta_correta") or q.get("gabarito", "")).strip().upper()
    )

    # Cabeçalho com progresso
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("📝 Resolução de Questões")
    with col2:
        st.metric("Respondidas", f"{respondidas}/{total}")
    with col3:
        if respondidas > 0:
            st.metric("Acertos", f"{acertos}/{respondidas}")

    if respondidas > 0:
        st.progress(respondidas / total)

    st.divider()

    # ==========================================
    # RENDERIZAÇÃO INDIVIDUAL DE CADA QUESTÃO
    # ==========================================
    for i, q in enumerate(questoes):
        id_q = str(q["id"])
        ja_respondeu = id_q in st.session_state.exec_respondidas

        with st.container(border=True):
            # Cabeçalho
            serie_str = q.get("serie", "Geral")
            assunto_str = q.get("assunto", "Sem Assunto")
            st.markdown(
                f"**Q{i + 1}.** "
                f"<span style='color:gray; font-size:0.85em'>"
                f"({serie_str} | {assunto_str})"
                f"</span>",
                unsafe_allow_html=True,
            )

            enunciado_puro = limpar_html(q.get("enunciado", ""))
            st.write(enunciado_puro)

            # Processa alternativas
            alts = q.get("alternativas", {})
            if isinstance(alts, str):
                try:
                    alts = ast.literal_eval(alts)
                except Exception:
                    alts = {}

            opcoes = []
            mapa_letras = {}
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in alts:
                    txt = extrair_texto_alternativa(alts[letra])
                    label = f"{letra}) {txt}"
                    opcoes.append(label)
                    mapa_letras[label] = letra

            if not opcoes:
                st.warning("Esta questão não possui alternativas cadastradas.")
                continue

            # Descobre qual opção estava marcada (para manter após rerun)
            idx_selecionado = None
            if ja_respondeu:
                letra_marcada = st.session_state.exec_respondidas[id_q]
                for idx_opt, opt_txt in enumerate(opcoes):
                    if opt_txt.startswith(f"{letra_marcada})"):
                        idx_selecionado = idx_opt
                        break

            # Radio de alternativas
            escolha = st.radio(
                f"alternativas_q{id_q}",
                options=opcoes,
                index=idx_selecionado,
                key=f"radio_{id_q}",
                disabled=ja_respondeu,
                label_visibility="collapsed",
            )

            # --- BOTÃO DE RESPONDER ---
            if not ja_respondeu:
                if st.button("✅ Responder", key=f"btn_resp_{id_q}"):
                    if escolha:
                        st.session_state.exec_respondidas[id_q] = mapa_letras[escolha]
                        st.rerun()
                    else:
                        st.warning("Selecione uma alternativa antes de responder!")

            # --- FEEDBACK PÓS-RESPOSTA ---
            else:
                letra_marcada = st.session_state.exec_respondidas[id_q]
                gabarito = (
                    str(q.get("resposta_correta") or q.get("gabarito", ""))
                    .strip()
                    .upper()
                )

                if letra_marcada == gabarito:
                    st.success(f"✅ **Acertou!** Gabarito: **{gabarito}**")
                else:
                    st.error(
                        f"❌ **Errou.** Você marcou **{letra_marcada}**, "
                        f"o correto é **{gabarito}**."
                    )

                # Exibe comentário já gerado (persiste entre reruns)  ← FIX PRINCIPAL
                if id_q in st.session_state.exec_comentarios:
                    st.info(
                        f"🤖 **Tutor MarIO:**\n\n"
                        f"{st.session_state.exec_comentarios[id_q]}"
                    )
                else:
                    # Botão para gerar o comentário pela primeira vez
                    if st.button("✨ Comentário do Tutor MarIO", key=f"btn_ia_{id_q}"):
                        with st.spinner("Gerando comentário..."):
                            comentario = explicar_com_ia(
                                enunciado_puro, letra_marcada, gabarito
                            )
                            # Salva no session_state para persistir
                            st.session_state.exec_comentarios[id_q] = comentario
                        st.rerun()

    # ==========================================
    # RODAPÉ
    # ==========================================
    st.divider()

    # Placar final se tudo respondido
    if respondidas == total:
        pct = round(acertos / total * 100)
        if pct >= 70:
            st.balloons()
            st.success(
                f"🎉 **Treino concluído!** Você acertou **{acertos}/{total}** ({pct}%). Ótimo desempenho!"
            )
        else:
            st.warning(
                f"📊 **Treino concluído!** Você acertou **{acertos}/{total}** ({pct}%). Continue praticando!"
            )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔄 Novo Treino (mesmos filtros)", use_container_width=True):
            # Mantém questoes mas reseta respostas
            st.session_state.exec_respondidas = {}
            st.session_state.exec_comentarios = {}
            st.rerun()

    with col_b:
        if st.button(
            "⬅️ Voltar e Mudar Filtros",
            type="secondary",
            use_container_width=True,
        ):
            for k in ["exec_questoes", "exec_respondidas", "exec_comentarios"]:
                st.session_state.pop(k, None)
            st.session_state.exec_estado = "filtros"
            st.rerun()
