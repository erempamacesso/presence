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
# 📝 PÁGINA PRINCIPAL
# ==========================================
def exibir_execucao_lista(supabase):
    # Tenta recuperar a configuração vinda do dashboard
    config = st.session_state.get("lista_config")
    aluno = st.session_state.get("aluno")

    if not config or not aluno:
        st.warning("Nenhuma configuração de treino encontrada.")
        if st.button("Voltar ao Menu"):
            st.session_state.etapa = "home"
            st.rerun()
        return

    serie_aluno = aluno.get("serie") or aluno.get("turma", "2º Ano")
    st.title(f"📚 {config.get('titulo', 'Treino Livre')}")
    st.caption(f"Série: {serie_aluno} | Responda e receba feedback imediato.")

    # ── Estados da página ──────────────────────────────────────────────
    if "el_respondidas" not in st.session_state:
        st.session_state.el_respondidas = {}  # {id_q: letra_marcada}

    # Carrega as questões apenas uma vez
    if "el_questoes" not in st.session_state or not st.session_state.el_questoes:
        with st.spinner("Carregando questões selecionadas..."):
            ids = config.get("questoes_ids", [])
            res = supabase.table("questoes").select("*").in_("id", ids).execute()
            if res.data:
                mapa_questoes = {q["id"]: q for q in res.data}
                st.session_state.el_questoes = [
                    mapa_questoes[id_q] for id_q in ids if id_q in mapa_questoes
                ]
            else:
                st.error("Não foi possível carregar as questões.")
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
        if st.button("🔄 Novo Treino", use_container_width=True):
            for k in ["el_questoes", "el_respondidas", "lista_config"]:
                st.session_state.pop(k, None)
            st.session_state.menu_active = "treino"
            st.session_state.etapa = "home"
            st.rerun()
    with col2:
        if st.button("⬅️ Sair do Treino", type="secondary", use_container_width=True):
            for k in ["el_questoes", "el_respondidas", "lista_config"]:
                st.session_state.pop(k, None)
            st.session_state.menu_active = "treino"
            st.session_state.etapa = "home"
            st.rerun()
