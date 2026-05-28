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
        return f"⚠️ O Tutor MarIO está processando muitas dúvidas agora. Lembre-se: o gabarito correto é a alternativa {resposta_correta}!"


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
            except:
                pass
    return str(conteudo)


# ==========================================
# 📝 TELA ESTILO QCONCURSOS
# ==========================================
def exibir_execucao_lista(supabase):
    st.title("📚 QTreino - Resolução de Questões")
    st.caption("Filtre, responda e receba feedback imediato questão por questão.")

    # --- INICIALIZAÇÃO DE ESTADOS ---
    if "qc_questoes" not in st.session_state:
        st.session_state.qc_questoes = []
    if "qc_respondidas" not in st.session_state:
        st.session_state.qc_respondidas = {}  # Guarda {id_questao: alternativa_marcada}

    # ==========================================
    # 🔍 PAINEL DE FILTROS (MECANISMO DE BUSCA)
    # ==========================================
    # Se já tem questões carregadas, o expander fica fechado. Se não, fica aberto.
    expander_aberto = len(st.session_state.qc_questoes) == 0

    with st.expander("⚙️ Filtros de Busca", expanded=expander_aberto):
        with st.form("form_filtros_qc"):
            c1, c2, c3 = st.columns([2, 2, 1])
            lista_series = ["Todas", "1º ANO", "2º ANO", "3º ANO", "9º ANO", "EJA"]

            filtro_serie = c1.selectbox("Série / Ano:", lista_series)
            filtro_assunto = c2.text_input(
                "Assunto (Opcional):", placeholder="Ex: Frações, Revolução..."
            )
            limite_q = c3.number_input(
                "Quantidade:", min_value=1, max_value=50, value=10
            )

            btn_buscar = st.form_submit_button(
                "🔍 Filtrar Questões", type="primary", use_container_width=True
            )

            if btn_buscar:
                with st.spinner("Buscando no banco de dados..."):
                    # Monta a query dinâmica no Supabase
                    query = supabase.table("questoes").select("*")
                    if filtro_serie != "Todas":
                        query = query.eq("serie", filtro_serie)
                    if filtro_assunto:
                        query = query.ilike("assunto", f"%{filtro_assunto}%")

                    res = query.limit(limite_q).execute()

                    if res.data:
                        st.session_state.qc_questoes = res.data
                        st.session_state.qc_respondidas = (
                            {}
                        )  # Reseta o progresso ao buscar novas
                        st.rerun()
                    else:
                        st.warning("Nenhuma questão encontrada com esses filtros.")

    # ==========================================
    # 📖 LISTA DE QUESTÕES (RENDERIZAÇÃO INDIVIDUAL)
    # ==========================================
    questoes = st.session_state.qc_questoes

    if not questoes:
        st.info("👆 Utilize o painel acima para buscar questões e iniciar seu treino.")
        return

    st.write(f"**{len(questoes)} questões encontradas.** Bom estudo!")
    st.divider()

    for i, q in enumerate(questoes):
        id_q = str(q["id"])

        # Verifica se o aluno já respondeu ESTA questão específica
        ja_respondeu = id_q in st.session_state.qc_respondidas

        with st.container(border=True):
            # Cabeçalho da Questão
            serie_str = q.get("serie", "Geral")
            assunto_str = q.get("assunto", "Sem Assunto")
            st.markdown(
                f"**Q{i+1}.** <span style='color:gray; font-size:0.9em'>({serie_str} | {assunto_str}) ID: {id_q}</span>",
                unsafe_allow_html=True,
            )

            enunciado_puro = limpar_html(q.get("enunciado", ""))
            st.write(enunciado_puro)

            # Processamento das Alternativas
            alts = q.get("alternativas", {})
            if isinstance(alts, str):
                try:
                    alts = ast.literal_eval(alts)
                except:
                    alts = {}

            opcoes = []
            mapa_letras = {}
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in alts:
                    txt = extrair_texto_alternativa(alts[letra])
                    label = f"{letra}) {txt}"
                    opcoes.append(label)
                    mapa_letras[label] = letra

            # Se já respondeu, descobre qual foi a opção para deixar marcada no radio
            idx_selecionado = None
            if ja_respondeu:
                letra_marcada = st.session_state.qc_respondidas[id_q]
                for idx_opt, opt_txt in enumerate(opcoes):
                    if opt_txt.startswith(f"{letra_marcada})"):
                        idx_selecionado = idx_opt

            # Componente Radio (Desabilita apenas se já tiver respondido)
            escolha = st.radio(
                f"alternativas_q{id_q}",
                options=opcoes,
                index=idx_selecionado,
                key=f"radio_{id_q}",
                disabled=ja_respondeu,
                label_visibility="collapsed",
            )

            # ==========================================
            # AÇÃO DE RESPONDER E FEEDBACK IMEDIATO
            # ==========================================
            if not ja_respondeu:
                # Botão para submeter apenas esta questão
                if st.button("Responder", key=f"btn_resp_{id_q}"):
                    if escolha:
                        st.session_state.qc_respondidas[id_q] = mapa_letras[escolha]
                        st.rerun()
                    else:
                        st.warning("Selecione uma alternativa antes de responder!")
            else:
                # Lógica de Gabarito e IA para quando a questão estiver respondida
                letra_marcada = st.session_state.qc_respondidas[id_q]
                gabarito = (
                    str(q.get("resposta_correta") or q.get("gabarito")).strip().upper()
                )

                if letra_marcada == gabarito:
                    st.success(f"✅ **Acertou!** Gabarito: {gabarito}")
                else:
                    st.error(
                        f"❌ **Errou.** Você marcou {letra_marcada}, o correto é **{gabarito}**."
                    )

                # Botão para chamar a IA
                if st.button("✨ Comentário do Tutor MarIO", key=f"btn_ia_{id_q}"):
                    with st.spinner("Gerando comentário..."):
                        comentario = explicar_com_ia(
                            enunciado_puro, letra_marcada, gabarito
                        )
                        st.info(f"🤖 **Comentário do Tutor:**\n\n{comentario}")

    # ==========================================
    # RODAPÉ
    # ==========================================
    st.divider()
    if st.button("⬅️ Sair do Treino", type="secondary", use_container_width=True):
        keys_limpeza = ["qc_questoes", "qc_respondidas"]
        for k in keys_limpeza:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state.etapa = "ante_sala"
        st.rerun()
