import streamlit as st
import google.generativeai as genai
import pandas as pd
import re
import ast


# ==========================================
# 🤖 CONFIGURAÇÃO DO TUTOR IA
# ==========================================
@st.cache_resource
def configurar_tutor_ia():
    """Configura o modelo Gemini via Secrets de forma otimizada"""
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Chave GEMINI_API_KEY não configurada nos Secrets.")
        return None
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")


def explicar_com_ia(enunciado, resposta_aluno, resposta_correta, alternativas):
    model = configurar_tutor_ia()
    if not model:
        return "Erro na configuração da IA."

    prompt = f"""
    Você é o Tutor MarIO, um professor empático e motivador. 
    O aluno está treinando e errou ou teve dúvida em uma questão.
    ENUNCIADO: {enunciado}
    ALTERNATIVAS: {alternativas}
    RESPOSTA DO ALUNO: {resposta_aluno}
    GABARITO CORRETO: {resposta_correta}

    Explique de forma curta (3 a 4 linhas) o raciocínio correto. 
    Seja encorajador e use uma linguagem simples.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Não consegui analisar agora, mas continue treinando! (Erro: {e})"


# ==========================================
# 🛠️ HELPERS DE FORMATAÇÃO
# ==========================================
def limpar_html(html):
    return re.sub(r"<[^>]+>", "", str(html)).strip() if html else ""


def obter_questoes(supabase, ids):
    res = supabase.table("questoes").select("*").in_("id", ids).execute()
    return res.data if res.data else []


# ==========================================
# 📝 TELA DE EXECUÇÃO
# ==========================================
def exibir_execucao_lista(supabase):
    lista = st.session_state.get("lista_config")
    if not lista:
        st.error("Lista não carregada corretamente.")
        if st.button("Voltar"):
            st.session_state.etapa = "dashboard"
            st.rerun()
        return

    st.title(f"🏋️ Treino: {lista['titulo']}")

    if "respostas_treino" not in st.session_state:
        st.session_state.respostas_treino = {}
    if "corrigido" not in st.session_state:
        st.session_state.corrigido = False

    questoes = obter_questoes(supabase, lista["questoes_ids"])

    # Renderização das questões
    for i, q in enumerate(questoes):
        with st.container(border=True):
            st.markdown(f"**Questão {i+1}**")
            enunciado_puro = limpar_html(q["enunciado"])
            st.write(enunciado_puro)

            alts = q.get("alternativas", {})
            if isinstance(alts, str):
                alts = ast.literal_eval(alts)

            letras = [l for l in ["A", "B", "C", "D", "E"] if l in alts]

            # Opções de exibição
            opcoes_labels = {l: f"({l}) {alts[l].get('texto', '')}" for l in letras}

            # Bloqueia rádio se já corrigiu
            resp_atual = st.session_state.respostas_treino.get(str(q["id"]))

            escolha = st.radio(
                "Sua resposta:",
                options=letras,
                format_func=lambda x: opcoes_labels[x],
                key=f"treino_{q['id']}",
                index=letras.index(resp_atual) if resp_atual in letras else None,
                disabled=st.session_state.corrigido,
            )

            if not st.session_state.corrigido:
                st.session_state.respostas_treino[str(q["id"])] = escolha

            # --- FEEDBACK PÓS-CORREÇÃO ---
            if st.session_state.corrigido:
                gabarito = q["resposta_correta"]
                if escolha == gabarito:
                    st.success(f"🎯 Mandou bem! Resposta correta: {gabarito}")
                else:
                    st.error(
                        f"❌ Não foi dessa vez. Você marcou {escolha}, mas o correto é {gabarito}"
                    )

                # --- INTEGRAÇÃO TUTOR IA ---
                exp_key = f"exp_{q['id']}"
                if st.button("✨ Explicar com Tutor IA", key=exp_key):
                    with st.spinner("O Tutor MarIO está analisando..."):
                        explicacao = explicar_com_ia(
                            enunciado_puro, escolha, gabarito, str(opcoes_labels)
                        )
                        st.info(f"💡 **Dica do Tutor:**\n{explicacao}")

    st.divider()

    col_nav1, col_nav2 = st.columns(2)

    if not st.session_state.corrigido:
        if col_nav1.button(
            "🔍 CORRIGIR EXERCÍCIOS AGORA", type="primary", use_container_width=True
        ):
            if len(st.session_state.respostas_treino) < len(questoes):
                st.warning("Tente responder todas antes de corrigir!")
            else:
                st.session_state.corrigido = True
                st.rerun()
    else:
        if col_nav1.button("🔄 Refazer Treino", use_container_width=True):
            st.session_state.corrigido = False
            st.session_state.respostas_treino = {}
            st.rerun()

    if col_nav2.button("⬅️ Sair do Treino", use_container_width=True):
        st.session_state.corrigido = False
        st.session_state.respostas_treino = {}
        st.session_state.etapa = "dashboard"  # Ajuste conforme sua navegação
        st.rerun()
