import streamlit as st
import re
import ast
import random


# ==========================================
# 🛠️ HELPERS
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
                d = ast.literal_eval(conteudo)
                if isinstance(d, dict):
                    return str(d.get("texto", ""))
            except Exception:
                pass
    return str(conteudo)


def parse_alternativas(alts_raw):
    """Retorna dict {letra: texto} a partir do campo alternativas do banco."""
    if isinstance(alts_raw, dict):
        return alts_raw
    if isinstance(alts_raw, str):
        try:
            return ast.literal_eval(alts_raw)
        except Exception:
            pass
    return {}


# ==========================================
# 🔍 BUSCA NO BANCO
# ==========================================
def buscar_assuntos(supabase, serie):
    """Retorna lista de assuntos únicos para a série do aluno."""
    try:
        res = supabase.table("questoes").select("assunto").eq("serie", serie).execute()
        assuntos = sorted(set(r["assunto"] for r in res.data if r.get("assunto")))
        return assuntos
    except Exception as e:
        st.error(f"Erro ao buscar assuntos: {e}")
        return []


def buscar_questoes(supabase, serie, assuntos_selecionados, quantidade):
    """Busca questões da série do aluno, opcionalmente filtradas por assunto."""
    try:
        query = supabase.table("questoes").select("*").eq("serie", serie)
        if assuntos_selecionados:
            query = query.in_("assunto", assuntos_selecionados)
        res = query.limit(quantidade * 4).execute()
        if not res.data:
            return []
        dados = res.data[:]
        random.shuffle(dados)
        return dados[:quantidade]
    except Exception as e:
        st.error(f"Erro ao buscar questões: {e}")
        return []


# ==========================================
# 📝 PÁGINA PRINCIPAL
# ==========================================
def exibir_execucao_lista(supabase):

    # Série do aluno vinda do login/session
    serie_aluno = st.session_state.get("serie_aluno") or st.session_state.get("serie")

    if not serie_aluno:
        st.error("Série do aluno não encontrada na sessão.")
        return

    # ── Estados da página ──────────────────────────────────────────────
    if "el_fase" not in st.session_state:
        st.session_state.el_fase = "filtros"  # "filtros" | "questoes"
    if "el_questoes" not in st.session_state:
        st.session_state.el_questoes = []
    if "el_respondidas" not in st.session_state:
        st.session_state.el_respondidas = {}  # {id_q: letra_marcada}

    # ══════════════════════════════════════════════════════════════════
    # FASE 1 — FILTROS
    # ══════════════════════════════════════════════════════════════════
    if st.session_state.el_fase == "filtros":

        st.markdown(
            f"## 📚 Treino — {serie_aluno}",
        )
        st.caption("Escolha os assuntos e a quantidade de questões para começar.")
        st.divider()

        assuntos = buscar_assuntos(supabase, serie_aluno)
        if not assuntos:
            st.warning("Nenhuma questão encontrada para sua série no banco de dados.")
            return

        assuntos_sel = st.multiselect(
            "Filtrar por assunto",
            options=assuntos,
            placeholder="Todos os assuntos",
        )

        quantidade = st.select_slider(
            "Quantidade de questões",
            options=[5, 10, 15, 20, 30, 40, 50],
            value=10,
        )

        st.write("")  # espaço
        if st.button("▶ Iniciar treino", type="primary", use_container_width=True):
            with st.spinner("Carregando questões..."):
                qs = buscar_questoes(supabase, serie_aluno, assuntos_sel, quantidade)
            if not qs:
                st.error(
                    "Nenhuma questão encontrada com esses filtros. Tente outros assuntos."
                )
            else:
                st.session_state.el_questoes = qs
                st.session_state.el_respondidas = {}
                st.session_state.el_fase = "questoes"
                st.rerun()
        return

    # ══════════════════════════════════════════════════════════════════
    # FASE 2 — QUESTÕES
    # ══════════════════════════════════════════════════════════════════
    questoes = st.session_state.el_questoes
    respondidas = st.session_state.el_respondidas
    total = len(questoes)
    n_resp = len(respondidas)

    # ── Cabeçalho com progresso ────────────────────────────────────────
    col_titulo, col_prog = st.columns([3, 2])
    with col_titulo:
        st.markdown(f"## 📝 {serie_aluno}")
    with col_prog:
        if n_resp > 0:
            acertos = sum(
                1
                for id_q, letra in respondidas.items()
                for q in questoes
                if str(q["id"]) == id_q
                and letra
                == str(q.get("resposta_correta") or q.get("gabarito", ""))
                .strip()
                .upper()
            )
            st.metric(
                "Progresso",
                f"{n_resp}/{total}",
                delta=f"{acertos} acerto{'s' if acertos != 1 else ''}",
            )

    if n_resp > 0:
        st.progress(n_resp / total)

    st.divider()

    # ── Loop de questões ──────────────────────────────────────────────
    for i, q in enumerate(questoes):
        id_q = str(q["id"])
        ja_respondeu = id_q in respondidas

        # Container com borda estilo card
        with st.container(border=True):

            # Identificação
            assunto_str = q.get("assunto", "")
            badge = f"**Q{i + 1}**"
            if assunto_str:
                badge += f"  <span style='background:#f0f2f6; color:#555; font-size:0.78em; padding:2px 8px; border-radius:10px;'>{assunto_str}</span>"
            st.markdown(badge, unsafe_allow_html=True)

            # Enunciado
            enunciado = limpar_html(q.get("enunciado", ""))
            st.write(enunciado)

            # Alternativas
            alts = parse_alternativas(q.get("alternativas", {}))
            opcoes, mapa = [], {}
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in alts:
                    txt = extrair_texto_alternativa(alts[letra])
                    label = f"**{letra})** {txt}"
                    opcoes.append(label)
                    mapa[label] = letra

            if not opcoes:
                st.caption("⚠️ Questão sem alternativas cadastradas.")
                continue

            # Índice da alternativa já marcada (para o radio não resetar)
            idx_marcado = None
            if ja_respondeu:
                letra_marcada = respondidas[id_q]
                for idx, opt in enumerate(opcoes):
                    if mapa[opt] == letra_marcada:
                        idx_marcado = idx
                        break

            escolha = st.radio(
                f"q_{id_q}",
                options=opcoes,
                index=idx_marcado,
                key=f"radio_{id_q}",
                disabled=ja_respondeu,
                label_visibility="collapsed",
            )

            # ── Antes de responder ─────────────────────────────────────
            if not ja_respondeu:
                if st.button("Responder", key=f"resp_{id_q}"):
                    if escolha:
                        respondidas[id_q] = mapa[escolha]
                        st.session_state.el_respondidas = respondidas
                        st.rerun()
                    else:
                        st.warning("Selecione uma alternativa.")

            # ── Após responder ─────────────────────────────────────────
            else:
                letra_marcada = respondidas[id_q]
                gabarito = (
                    str(q.get("resposta_correta") or q.get("gabarito", ""))
                    .strip()
                    .upper()
                )

                if letra_marcada == gabarito:
                    st.success(f"✅ Correto! Gabarito: **{gabarito}**")
                else:
                    st.error(
                        f"❌ Incorreto. Você marcou **{letra_marcada}** — "
                        f"gabarito: **{gabarito}**"
                    )

    # ── Rodapé ────────────────────────────────────────────────────────
    st.divider()

    # Placar final
    if n_resp == total:
        acertos = sum(
            1
            for id_q, letra in respondidas.items()
            for q in questoes
            if str(q["id"]) == id_q
            and letra
            == str(q.get("resposta_correta") or q.get("gabarito", "")).strip().upper()
        )
        pct = round(acertos / total * 100)
        if pct >= 70:
            st.balloons()
            st.success(f"🎉 Treino concluído! **{acertos}/{total}** acertos ({pct}%)")
        else:
            st.warning(
                f"📊 Treino concluído! **{acertos}/{total}** acertos ({pct}%) — continue praticando!"
            )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Repetir com novos filtros", use_container_width=True):
            for k in ["el_fase", "el_questoes", "el_respondidas"]:
                st.session_state.pop(k, None)
            st.rerun()
    with col2:
        if st.button("⬅️ Voltar ao menu", type="secondary", use_container_width=True):
            for k in ["el_fase", "el_questoes", "el_respondidas"]:
                st.session_state.pop(k, None)
            st.session_state.etapa = "home"
            st.rerun()
