import time
import streamlit as st


def mostrar_inscricao_aluno(
    db_alunos, db_provas, aluno, id_aluno, serie_aluno, turma_aluno
):
    st.title("🚀 Central de Inscrições")

    # Criar as abas do aluno
    tab_nova, tab_minhas = st.tabs(
        ["🚀 Realizar Nova Inscrição", "📋 Minhas Inscrições"]
    )

    # =========================================================================
    # ABA 1: NOVA INSCRIÇÃO
    # =========================================================================
    with tab_nova:
        st.info(
            "Selecione um evento na lista abaixo para realizar sua inscrição."
        )
        # INSIRA O CÓDIGO DA SUA ABA DE NOVA INSCRIÇÃO AQUI SE HOUVER

    # =========================================================================
    # ABA 2: MINHAS INSCRIÇÕES (Visualização e Gestão pelo Líder)
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
                    m.replace(" (Líder)", "").strip()
                    for m in insc.get("nomes_membros", "").split(",")
                    if m.strip()
                ]
                if nome_procurado in membros_limpos:
                    minhas_insc.append(insc)

            if not minhas_insc:
                st.info("Você ainda não está em nenhuma equipe inscrita.")
            else:
                for insc in minhas_insc:
                    # Busca segura do Evento
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

                    # Busca segura do Tema
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
                            # VERIFICAÇÃO DE LIDERANÇA DUPLA
                            lider_id_db = str(
                                insc.get("lider_id", "")
                            ).strip()
                            aluno_id_sessao = str(id_aluno).strip()
                            nome_lider_rotulo = (
                                f"{aluno.get('nome', '').strip()} (Líder)"
                            )

                            eh_lider = (
                                lider_id_db and lider_id_db == aluno_id_sessao
                            ) or (
                                nome_lider_rotulo
                                in insc.get("nomes_membros", "")
                            )

                            if eh_lider:
                                st.success("🌟 Você é o Líder")

                                # --- ALTERAR TEMA ---
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

                                            novo_tema_nome = st.selectbox(
                                                "Selecione o novo tema:",
                                                options=lista_nomes,
                                                index=idx_padrao,
                                                key=f"sel_t_edit_{insc['id']}",
                                            )

                                            if st.button(
                                                "💾 Confirmar Novo Tema",
                                                key=f"save_t_edit_{insc['id']}",
                                                type="primary",
                                                use_container_width=True,
                                            ):
                                                db_provas.table(
                                                    "feira_inscricoes"
                                                ).update(
                                                    {
                                                        "tema_id": opcoes_tema[
                                                            novo_tema_nome
                                                        ]
                                                    }
                                                ).eq(
                                                    "id", insc["id"]
                                                ).execute()
                                                st.success(
                                                    "✅ Tema atualizado com sucesso!"
                                                )
                                                time.sleep(1)
                                                st.rerun()
                                    except Exception as e_t:
                                        st.error(
                                            f"Erro ao carregar temas para edição: {e_t}"
                                        )

                                # --- GERENCIAR MEMBROS (CORRIGIDO) ---
                                with st.popover(
                                    "👥 Gerenciar Membros",
                                    use_container_width=True,
                                ):
                                    st.markdown("##### Editar Integrantes")
                                    if ev_d and isinstance(ev_d, dict):
                                        try:
                                            # Busca alunos da mesma turma
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
                                                c["nome"]
                                                for c in dados_alunos
                                                if c.get("nome")
                                                != aluno.get("nome")
                                            ]

                                            # Busca quem já está em outras equipes
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
                                                    x.replace(
                                                        " (Líder)", ""
                                                    ).strip()
                                                    for x in out.get(
                                                        "nomes_membros", ""
                                                    ).split(",")
                                                ]:
                                                    ocupados_outros.add(m)

                                            disp_edit = sorted(
                                                [
                                                    n
                                                    for n in todos_nomes_turma
                                                    if n not in ocupados_outros
                                                ]
                                            )

                                            # Membros cadastrados atualmente
                                            atuais = [
                                                m.replace(
                                                    " (Líder)", ""
                                                ).strip()
                                                for m in insc.get(
                                                    "nomes_membros", ""
                                                ).split(",")
                                                if "(Líder)" not in m
                                            ]

                                            # Persistência do multiselect na sessão
                                            ms_key = (
                                                f"ms_membros_{insc['id']}"
                                            )
                                            if ms_key not in st.session_state:
                                                st.session_state[ms_key] = [
                                                    m
                                                    for m in atuais
                                                    if m in disp_edit
                                                ]

                                            novos_membros = st.multiselect(
                                                "Selecione os integrantes:",
                                                options=disp_edit,
                                                key=ms_key,
                                            )

                                            if st.button(
                                                "💾 Atualizar Equipe",
                                                key=f"btn_save_m_{insc['id']}",
                                                use_container_width=True,
                                                type="primary",
                                            ):
                                                total = len(novos_membros) + 1
                                                min_e = int(
                                                    ev_d.get("min_membros", 1)
                                                )
                                                max_e = int(
                                                    ev_d.get("max_membros", 8)
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
                                                            f"{aluno.get('nome').strip()} (Líder), "
                                                            + ", ".join(
                                                                novos_membros
                                                            )
                                                        )
                                                    else:
                                                        equipe_final = f"{aluno.get('nome').strip()} (Líder)"

                                                    try:
                                                        db_provas.table(
                                                            "feira_inscricoes"
                                                        ).update(
                                                            {
                                                                "nomes_membros": equipe_final
                                                            }
                                                        ).eq(
                                                            "id", insc["id"]
                                                        ).execute()

                                                        st.success(
                                                            "✅ Equipe atualizada com sucesso!"
                                                        )
                                                        st.session_state.pop(
                                                            ms_key, None
                                                        )
                                                        time.sleep(1)
                                                        st.rerun()

                                                    except Exception as err_up:
                                                        st.error(
                                                            f"❌ Erro ao salvar no banco: {err_up}"
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