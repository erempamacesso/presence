import time
import streamlit as st


def mostrar_inscricao_aluno(
    db_alunos,
    db_provas,
    aluno=None,
    id_aluno=None,
    serie_aluno=None,
    turma_aluno=None,
):
    # Recuperação de dados da sessão
    if aluno is None:
        aluno = st.session_state.get("aluno", {})
    if id_aluno is None:
        id_aluno = (
            aluno.get("id")
            or st.session_state.get("id_aluno")
            or st.session_state.get("usuario_id", "")
        )
    if serie_aluno is None:
        serie_aluno = str(
            aluno.get("serie") or st.session_state.get("serie_aluno", "")
        ).strip()
    if turma_aluno is None:
        turma_aluno = str(
            aluno.get("turma") or st.session_state.get("turma_aluno", "")
        ).strip()

    st.title("🚀 Central de Inscrições")

    tab_nova, tab_minhas = st.tabs(
        ["🚀 Realizar Nova Inscrição", "📋 Minhas Inscrições"]
    )

    # =========================================================================
    # ABA 1: NOVA INSCRIÇÃO (SISTEMA COMPLETO DE INSCRICÃO DE EQUIPE)
    # =========================================================================
    with tab_nova:
        st.subheader("🚀 Eventos Disponíveis para Inscrição")
        nome_aluno_sessao = aluno.get("nome", "").strip()

        try:
            # 1. Buscar todos os eventos cadastrados
            res_ev = db_alunos.table("feira_eventos").select("*").execute()
            eventos = (
                res_ev.data
                if (res_ev and hasattr(res_ev, "data") and res_ev.data)
                else []
            )

            # 2. Buscar inscrições existentes para saber em quais o aluno já participa
            res_insc_all = (
                db_provas.table("feira_inscricoes").select("*").execute()
            )
            inscricoes_all = (
                res_insc_all.data
                if (
                    res_insc_all
                    and hasattr(res_insc_all, "data")
                    and res_insc_all.data
                )
                else []
            )

            eventos_ja_inscrito = set()
            for insc in inscricoes_all:
                membros_list = [
                    m.replace(" (Líder)", "").replace(" (Lider)", "").strip()
                    for m in insc.get("nomes_membros", "").split(",")
                    if m.strip()
                ]
                if (
                    nome_aluno_sessao in membros_list
                    or str(insc.get("lider_id", "")).strip()
                    == str(id_aluno).strip()
                ):
                    eventos_ja_inscrito.add(insc.get("evento_id"))

            # 3. Filtrar eventos nos quais o aluno ainda não se inscreveu
            eventos_disponiveis = [
                ev for ev in eventos if ev.get("id") not in eventos_ja_inscrito
            ]

            if not eventos_disponiveis:
                st.info(
                    "Você não possui novos eventos disponíveis no momento (ou já está inscrito em todos os eventos ativos)."
                )
            else:
                for ev in eventos_disponiveis:
                    with st.container(border=True):
                        st.markdown(f"### 🏆 {ev.get('nome', 'Evento')}")
                        min_m = int(ev.get("min_membros", 1))
                        max_m = int(ev.get("max_membros", 8))
                        st.caption(
                            f"👥 **Tamanho da Equipe:** Mínimo de {min_m} e máximo de {max_m} integrantes (incluindo o Líder)."
                        )

                        # Buscar temas disponíveis para o evento
                        res_temas = (
                            db_alunos.table("feira_temas")
                            .select("*")
                            .eq("evento_id", ev["id"])
                            .execute()
                        )
                        temas_ev = (
                            res_temas.data
                            if (
                                res_temas
                                and hasattr(res_temas, "data")
                                and res_temas.data
                            )
                            else []
                        )

                        # Inscrições já feitas neste evento especifico
                        insc_deste_evento = [
                            i
                            for i in inscricoes_all
                            if i.get("evento_id") == ev["id"]
                        ]
                        temas_ocupados = {
                            i.get("tema_id")
                            for i in insc_deste_evento
                            if i.get("tema_id")
                        }

                        # Identificar integrantes e disciplinas bloqueadas por turma
                        ocupados_evento = set()
                        disc_bloqueadas_turma = set()
                        dict_temas_todos = {t["id"]: t for t in temas_ev}

                        for i in insc_deste_evento:
                            for m in [
                                x.replace(" (Líder)", "")
                                .replace(" (Lider)", "")
                                .strip()
                                for x in i.get("nomes_membros", "").split(",")
                                if x.strip()
                            ]:
                                ocupados_evento.add(m)

                            if (
                                i.get("turma") == turma_aluno
                                and i.get("tema_id") in dict_temas_todos
                            ):
                                disc_bloqueadas_turma.add(
                                    dict_temas_todos[i["tema_id"]].get(
                                        "disciplina"
                                    )
                                )

                        # Filtrar temas por série e disponibilidade
                        opcoes_temas = {}
                        for t in temas_ev:
                            serie_tema = str(
                                t.get("Serie") or t.get("serie", "")
                            ).strip()
                            if serie_tema in (serie_aluno, "Geral", ""):
                                if (
                                    t["id"] not in temas_ocupados
                                    and t.get("disciplina")
                                    not in disc_bloqueadas_turma
                                ):
                                    opcoes_temas[
                                        f"{t['titulo_trabalho']} ({t['disciplina']})"
                                    ] = t["id"]

                        # Buscar colegas de turma disponíveis
                        res_colegas = (
                            db_alunos.table("alunos")
                            .select("nome")
                            .eq("turma", turma_aluno)
                            .execute()
                        )
                        colegas_data = (
                            res_colegas.data
                            if (
                                res_colegas
                                and hasattr(res_colegas, "data")
                                and res_colegas.data
                            )
                            else []
                        )

                        colegas_disponiveis = sorted(
                            [
                                c["nome"].strip()
                                for c in colegas_data
                                if c.get("nome")
                                and c["nome"].strip() != nome_aluno_sessao
                                and c["nome"].strip() not in ocupados_evento
                            ]
                        )

                        if not opcoes_temas:
                            st.warning(
                                "⚠️ Não há temas disponíveis para a sua turma ou série neste evento."
                            )
                        else:
                            with st.form(key=f"form_nova_insc_{ev['id']}"):
                                tema_sel_nome = st.selectbox(
                                    "Selecione o Tema do Trabalho:",
                                    options=list(opcoes_temas.keys()),
                                )
                                membros_sel = st.multiselect(
                                    "Selecione os integrantes da sua turma:",
                                    options=colegas_disponiveis,
                                    help="Você já é incluído automaticamente como Líder.",
                                )

                                btn_inscrever = st.form_submit_button(
                                    "🚀 Finalizar Inscrição",
                                    type="primary",
                                    use_container_width=True,
                                )

                                if btn_inscrever:
                                    total_equipe = (
                                        len(membros_sel) + 1
                                    )  # +1 para o próprio aluno (líder)
                                    if (
                                        total_equipe < min_m
                                        or total_equipe > max_m
                                    ):
                                        st.error(
                                            f"⚠️ A equipe precisa ter entre {min_m} e {max_m} integrantes. Você selecionou {total_equipe} (Você como Líder + {len(membros_sel)} membro(s))."
                                        )
                                    else:
                                        lider_rotulo = (
                                            f"{nome_aluno_sessao} (Líder)"
                                        )
                                        if membros_sel:
                                            equipe_str = (
                                                f"{lider_rotulo}, "
                                                + ", ".join(membros_sel)
                                            )
                                        else:
                                            equipe_str = lider_rotulo

                                        dados_nova_insc = {
                                            "evento_id": ev["id"],
                                            "tema_id": opcoes_temas[
                                                tema_sel_nome
                                            ],
                                            "lider_id": str(id_aluno),
                                            "turma": turma_aluno,
                                            "nomes_membros": equipe_str,
                                        }

                                        res_ins = (
                                            db_provas.table("feira_inscricoes")
                                            .insert(dados_nova_insc)
                                            .execute()
                                        )
                                        if (
                                            res_ins
                                            and hasattr(res_ins, "data")
                                            and res_ins.data
                                        ):
                                            st.success(
                                                "🎉 Inscrição realizada com sucesso!"
                                            )
                                            time.sleep(1.5)
                                            st.rerun()
                                        else:
                                            st.error(
                                                "❌ Erro ao gravar inscrição no Supabase. Verifique se o RLS está desativado na tabela 'feira_inscricoes'."
                                            )
        except Exception as e_nova:
            st.error(f"Erro ao carregar formulário de inscrição: {e_nova}")

    # =========================================================================
    # ABA 2: MINHAS INSCRIÇÕES (Visualização e Gestão)
    # =========================================================================
    with tab_minhas:
        col_titulo, col_refresh = st.columns([5, 1])
        with col_titulo:
            st.subheader("📋 Inscrições em que você participa")
        with col_refresh:
            if st.button(
                "🔄", help="Atualizar lista", use_container_width=True
            ):
                st.rerun()

        try:
            res_all = db_provas.table("feira_inscricoes").select("*").execute()
            minhas_insc = []
            nome_procurado = aluno.get("nome", "").strip()

            dados_inscricoes = (
                res_all.data
                if (res_all and hasattr(res_all, "data") and res_all.data)
                else []
            )

            for insc in dados_inscricoes:
                membros_limpos = [
                    m.replace(" (Líder)", "").replace(" (Lider)", "").strip()
                    for m in insc.get("nomes_membros", "").split(",")
                    if m.strip()
                ]
                if (
                    nome_procurado in membros_limpos
                    or str(insc.get("lider_id", "")).strip()
                    == str(id_aluno).strip()
                ):
                    minhas_insc.append(insc)

            if not minhas_insc:
                st.info("Você ainda não está em nenhuma equipe inscrita.")
            else:
                for insc in minhas_insc:
                    ev_d = None
                    try:
                        res_ev_meta = (
                            db_alunos.table("feira_eventos")
                            .select("nome, min_membros, max_membros")
                            .eq("id", insc["evento_id"])
                            .maybe_single()
                            .execute()
                        )
                        if res_ev_meta and hasattr(res_ev_meta, "data"):
                            ev_d = res_ev_meta.data
                    except Exception:
                        ev_d = None

                    tm_d = None
                    try:
                        res_tm_meta = (
                            db_alunos.table("feira_temas")
                            .select("titulo_trabalho, disciplina")
                            .eq("id", insc["tema_id"])
                            .maybe_single()
                            .execute()
                        )
                        if res_tm_meta and hasattr(res_tm_meta, "data"):
                            tm_d = res_tm_meta.data
                    except Exception:
                        tm_d = None

                    with st.container(border=True):
                        c_inf, c_ops = st.columns([3, 1])
                        with c_inf:
                            nome_evento = (
                                ev_d.get("nome", "Evento")
                                if isinstance(ev_d, dict)
                                else "Evento"
                            )
                            titulo_trabalho = (
                                tm_d.get(
                                    "titulo_trabalho", "Tema não encontrado"
                                )
                                if isinstance(tm_d, dict)
                                else "Tema não encontrado"
                            )
                            disciplina = (
                                tm_d.get("disciplina", "-")
                                if isinstance(tm_d, dict)
                                else "-"
                            )

                            st.markdown(f"#### 🏆 {nome_evento}")
                            st.markdown(f"**Trabalho:** {titulo_trabalho}")
                            st.caption(f"🧪 Disciplina: {disciplina}")
                            st.write(
                                f"👥 **Equipe:** {insc.get('nomes_membros', '')}"
                            )

                        with c_ops:
                            lider_id_db = str(
                                insc.get("lider_id", "")
                            ).strip()
                            aluno_id_sessao = str(id_aluno).strip()
                            nome_lider_rotulo = (
                                f"{aluno.get('nome', '').strip()} (Líder)"
                            )

                            eh_lider = (
                                (lider_id_db and lider_id_db == aluno_id_sessao)
                                or (
                                    nome_lider_rotulo
                                    in insc.get("nomes_membros", "")
                                )
                                or (
                                    "(Líder)" in insc.get("nomes_membros", "")
                                    and aluno.get("nome", "").strip()
                                    in insc.get("nomes_membros", "")
                                )
                            )

                            if eh_lider:
                                st.success("🌟 Você é o Líder")

                                with st.popover(
                                    "📝 Alterar Tema", use_container_width=True
                                ):
                                    st.markdown("##### Escolha um novo Tema")
                                    try:
                                        res_t = (
                                            db_alunos.table("feira_temas")
                                            .select("*")
                                            .eq(
                                                "evento_id",
                                                insc["evento_id"],
                                            )
                                            .execute()
                                        )
                                        temas_evento = (
                                            res_t.data
                                            if (
                                                res_t
                                                and hasattr(res_t, "data")
                                                and res_t.data
                                            )
                                            else []
                                        )
                                        todos_t_dict = {
                                            t["id"]: t for t in temas_evento
                                        }

                                        res_i = (
                                            db_provas.table("feira_inscricoes")
                                            .select("tema_id, turma")
                                            .eq("evento_id", insc["evento_id"])
                                            .neq("id", insc["id"])
                                            .execute()
                                        )
                                        outras_insc = (
                                            res_i.data
                                            if (
                                                res_i
                                                and hasattr(res_i, "data")
                                                and res_i.data
                                            )
                                            else []
                                        )

                                        temas_ocupados = [
                                            i["tema_id"]
                                            for i in outras_insc
                                            if "tema_id" in i
                                        ]
                                        disc_bloqueadas = {
                                            todos_t_dict[i["tema_id"]].get(
                                                "disciplina"
                                            )
                                            for i in outras_insc
                                            if i.get("turma") == turma_aluno
                                            and i.get("tema_id") in todos_t_dict
                                        }

                                        opcoes_tema = {}
                                        for t in temas_evento:
                                            if str(t.get("Serie")).strip() in (
                                                serie_aluno,
                                                "Geral",
                                            ):
                                                if (
                                                    t["id"] not in temas_ocupados
                                                    and t.get("disciplina")
                                                    not in disc_bloqueadas
                                                ):
                                                    opcoes_tema[
                                                        f"{t['titulo_trabalho']} ({t['disciplina']})"
                                                    ] = t["id"]

                                        if not opcoes_tema:
                                            st.warning(
                                                "Não há outros temas disponíveis no momento."
                                            )
                                        else:
                                            tema_atual_id = insc["tema_id"]
                                            lista_nomes = list(
                                                opcoes_tema.keys()
                                            )
                                            idx_padrao = 0
                                            for i, nome in enumerate(
                                                lista_nomes
                                            ):
                                                if (
                                                    opcoes_tema[nome]
                                                    == tema_atual_id
                                                ):
                                                    idx_padrao = i
                                                    break

                                            with st.form(
                                                key=f"form_tema_{insc['id']}"
                                            ):
                                                novo_tema_nome = st.selectbox(
                                                    "Selecione o novo tema:",
                                                    options=lista_nomes,
                                                    index=idx_padrao,
                                                )

                                                sub_t = st.form_submit_button(
                                                    "💾 Confirmar Novo Tema",
                                                    type="primary",
                                                    use_container_width=True,
                                                )

                                                if sub_t:
                                                    up_res = (
                                                        db_provas.table(
                                                            "feira_inscricoes"
                                                        )
                                                        .update(
                                                            {
                                                                "tema_id": opcoes_tema[
                                                                    novo_tema_nome
                                                                ]
                                                            }
                                                        )
                                                        .eq("id", insc["id"])
                                                        .execute()
                                                    )

                                                    if (
                                                        up_res
                                                        and hasattr(
                                                            up_res, "data"
                                                        )
                                                        and up_res.data
                                                    ):
                                                        st.success(
                                                            "✅ Tema atualizado com sucesso!"
                                                        )
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        st.error(
                                                            "❌ O Supabase recusou a alteração. Desative o RLS da tabela 'feira_inscricoes'."
                                                        )
                                    except Exception as e_t:
                                        st.error(
                                            f"Erro ao carregar temas para edição: {e_t}"
                                        )

                                with st.popover(
                                    "👥 Gerenciar Membros",
                                    use_container_width=True,
                                ):
                                    st.markdown("##### Editar Integrantes")
                                    if ev_d and isinstance(ev_d, dict):
                                        try:
                                            res_c = (
                                                db_alunos.table("alunos")
                                                .select("nome")
                                                .eq("turma", turma_aluno)
                                                .execute()
                                            )
                                            dados_alunos = (
                                                res_c.data
                                                if (
                                                    res_c
                                                    and hasattr(res_c, "data")
                                                    and res_c.data
                                                )
                                                else []
                                            )
                                            todos_nomes_turma = [
                                                c["nome"].strip()
                                                for c in dados_alunos
                                                if c.get("nome")
                                            ]

                                            res_o = (
                                                db_provas.table(
                                                    "feira_inscricoes"
                                                )
                                                .select("nomes_membros")
                                                .eq(
                                                    "evento_id",
                                                    insc["evento_id"],
                                                )
                                                .neq("id", insc["id"])
                                                .execute()
                                            )
                                            dados_outros = (
                                                res_o.data
                                                if (
                                                    res_o
                                                    and hasattr(res_o, "data")
                                                    and res_o.data
                                                )
                                                else []
                                            )
                                            ocupados_outros = set()
                                            for out in dados_outros:
                                                for m in [
                                                    x.replace(" (Líder)", "")
                                                    .replace(" (Lider)", "")
                                                    .strip()
                                                    for x in out.get(
                                                        "nomes_membros", ""
                                                    ).split(",")
                                                    if x.strip()
                                                ]:
                                                    ocupados_outros.add(m)

                                            membros_atuais_raw = [
                                                x.strip()
                                                for x in insc.get(
                                                    "nomes_membros", ""
                                                ).split(",")
                                                if x.strip()
                                            ]
                                            atuais_membros = []
                                            nome_lider_da_equipe = ""
                                            for m in membros_atuais_raw:
                                                if (
                                                    "(Líder)" in m
                                                    or "(Lider)" in m
                                                ):
                                                    nome_lider_da_equipe = (
                                                        m.replace(
                                                            "(Líder)", ""
                                                        )
                                                        .replace("(Lider)", "")
                                                        .strip()
                                                    )
                                                else:
                                                    atuais_membros.append(m)

                                            if not nome_lider_da_equipe:
                                                nome_lider_da_equipe = (
                                                    aluno.get("nome", "").strip()
                                                )

                                            disponiveis = [
                                                n
                                                for n in todos_nomes_turma
                                                if n not in ocupados_outros
                                                and n != nome_lider_da_equipe
                                            ]

                                            opcoes_multiselect = sorted(
                                                list(
                                                    set(disponiveis)
                                                    | set(atuais_membros)
                                                )
                                            )

                                            with st.form(
                                                key=f"form_membros_{insc['id']}"
                                            ):
                                                novos_membros = st.multiselect(
                                                    "Selecione os integrantes:",
                                                    options=opcoes_multiselect,
                                                    default=atuais_membros,
                                                )

                                                submit_membros = (
                                                    st.form_submit_button(
                                                        "💾 Atualizar Equipe",
                                                        use_container_width=True,
                                                        type="primary",
                                                    )
                                                )

                                                if submit_membros:
                                                    total = (
                                                        len(novos_membros) + 1
                                                    )
                                                    min_e = int(
                                                        ev_d.get(
                                                            "min_membros", 1
                                                        )
                                                    )
                                                    max_e = int(
                                                        ev_d.get(
                                                            "max_membros", 8
                                                        )
                                                    )

                                                    if (
                                                        total < min_e
                                                        or total > max_e
                                                    ):
                                                        st.error(
                                                            f"⚠️ A equipe deve ter entre {min_e} e {max_e} integrantes. (Atual: {total})"
                                                        )
                                                    else:
                                                        if novos_membros:
                                                            equipe_final = (
                                                                f"{nome_lider_da_equipe} (Líder), "
                                                                + ", ".join(
                                                                    novos_membros
                                                                )
                                                            )
                                                        else:
                                                            equipe_final = f"{nome_lider_da_equipe} (Líder)"

                                                        resp_up = (
                                                            db_provas.table(
                                                                "feira_inscricoes"
                                                            )
                                                            .update(
                                                                {
                                                                    "nomes_membros": equipe_final
                                                                }
                                                            )
                                                            .eq(
                                                                "id",
                                                                insc["id"],
                                                            )
                                                            .execute()
                                                        )

                                                        if (
                                                            resp_up
                                                            and hasattr(
                                                                resp_up, "data"
                                                            )
                                                            and resp_up.data
                                                        ):
                                                            st.success(
                                                                "✅ Equipe atualizada com sucesso!"
                                                            )
                                                            time.sleep(1)
                                                            st.rerun()
                                                        else:
                                                            st.error(
                                                                "❌ O Supabase rejeitou a gravação! Verifique se o RLS está desativado na tabela 'feira_inscricoes'."
                                                            )

                                        except Exception as e_edit:
                                            st.error(
                                                f"Erro ao atualizar integrantes: {e_edit}"
                                            )
                                    else:
                                        st.warning(
                                            "Dados do evento não encontrados para validação."
                                        )

                                if st.button(
                                    "🗑️ Cancelar Inscrição",
                                    key=f"del_{insc['id']}",
                                    use_container_width=True,
                                    type="secondary",
                                    help="Atenção: Isso removerá o grupo permanentemente deste evento.",
                                ):
                                    db_provas.table("feira_inscricoes").delete().eq(
                                        "id", insc["id"]
                                    ).execute()
                                    st.toast("Inscrição cancelada.")
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.info("👤 Membro do Grupo")
                                st.button(
                                    "Bloqueado",
                                    key=f"lock_{insc['id']}",
                                    disabled=True,
                                    use_container_width=True,
                                    help="Apenas o líder pode excluir ou alterar a inscrição.",
                                )
        except Exception as e:
            st.error(f"Erro ao carregar seu histórico de inscrições: {e}")