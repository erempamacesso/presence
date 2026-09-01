import streamlit as st
import datetime
import time
from collections import defaultdict


def mostrar_inscricao_aluno(db_alunos, db_provas):
    # --- 1. ESTILO CSS ---
    st.markdown(
        """
        <style>
        .event-card {
            background-color: white; padding: 20px; border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-left: 6px solid #00d4ff;
            margin-bottom: 20px;
        }
        .step-container {
            display: flex; justify-content: space-between; margin-bottom: 30px;
            background: white; padding: 15px; border-radius: 10px;
        }
        .step { color: #bdc3c7; font-weight: bold; width: 30%; text-align: center; font-size: 0.9rem; }
        .step-active { color: #00d4ff; border-bottom: 3px solid #00d4ff; }
        
        .tema-card {
            background: #f8f9fa; padding: 15px; border-radius: 8px;
            margin: 10px 0; border-left: 4px solid #00d4ff;
        }
        .tema-card-bloqueado {
            background: #ffe6e6; border-left-color: #d32f2f;
            opacity: 0.7;
        }
        .tema-card-disciplina-bloqueada {
            background: #fff3e0; border-left-color: #f57c00;
            opacity: 0.7;
        }
        .disciplina-titulo {
            font-weight: bold; font-size: 1.1rem; color: #333;
            padding: 10px; background: #e3f2fd; border-radius: 5px;
            margin-top: 15px; margin-bottom: 10px;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Identificação da estudante (garantindo id como string limpa)
    aluno = st.session_state.get("aluno", {})
    turma_aluno = aluno.get("turma", "Sem Turma")
    id_aluno = str(aluno.get("id", "")).strip()

    # Lógica de extração da série
    serie_aluno = "Geral"
    if "1º" in turma_aluno:
        serie_aluno = "1º"
    elif "2º" in turma_aluno:
        serie_aluno = "2º"
    elif "3º" in turma_aluno:
        serie_aluno = "3º"

    st.title("🚀 Central de Inscrições")
    st.info(
        f"🎓 **{aluno.get('nome')}** | Série: **{serie_aluno}** | Turma: **{turma_aluno}**"
    )

    # --- SISTEMA DE ABAS ---
    tab_insc, tab_minhas = st.tabs(
        ["🚀 Realizar Nova Inscrição", "📋 Minhas Inscrições"]
    )

    # =========================================================================
    # ABA 1: REALIZAR INSCRIÇÃO
    # =========================================================================
    with tab_insc:
        if "passo_insc" not in st.session_state:
            st.session_state.passo_insc = 1

        # Stepper Visual
        p1, p2, p3 = [
            "step-active" if st.session_state.passo_insc == i else ""
            for i in range(1, 4)
        ]
        st.markdown(
            f"""
            <div class="step-container">
                <div class="step {p1}">1. EVENTO</div>
                <div class="step {p2}">2. TEMA</div>
                <div class="step {p3}">3. EQUIPE E FINALIZAR</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # PASSO 1: SELEÇÃO DE EVENTO
        if st.session_state.passo_insc == 1:
            st.markdown("### 1. SELEÇÃO DE EVENTO")
            if st.button("⬅️ Voltar ao Início"):
                st.session_state.etapa = "ante_sala"
                st.rerun()

            try:
                res_eventos = (
                    db_alunos.table("feira_eventos")
                    .select("*")
                    .eq("ativo", True)
                    .execute()
                )
                dados_eventos = res_eventos.data if (res_eventos and hasattr(res_eventos, "data") and res_eventos.data) else []

                if not dados_eventos:
                    st.info("No momento não há eventos com inscrições abertas.")
                else:
                    agora = datetime.datetime.now()
                    for evento in dados_eventos:
                        with st.container(border=True):

                            def parse_dt(v, default_d):
                                if not v:
                                    return default_d
                                try:
                                    return datetime.datetime.strptime(
                                        str(v).split("T")[0], "%Y-%m-%d"
                                    ).date()
                                except:
                                    return default_d

                            def parse_tm(v, default_t):
                                if not v:
                                    return default_t
                                try:
                                    return datetime.datetime.strptime(
                                        str(v)[:5], "%H:%M"
                                    ).time()
                                except:
                                    return default_t

                            d_ev_inicio = parse_dt(
                                evento.get("data_inicio"), agora.date()
                            )
                            d_ev_fim = parse_dt(evento.get("data_fim"), agora.date())
                            h_ab = parse_tm(
                                evento.get("insc_hora_abertura"), datetime.time(0, 0)
                            )
                            h_fn = parse_tm(
                                evento.get("insc_hora_final"), datetime.time(23, 59)
                            )
                            d_insc_ini = parse_dt(
                                evento.get("insc_abertura"), d_ev_inicio
                            )
                            d_insc_fim = parse_dt(evento.get("insc_final"), d_ev_fim)
                            dt_insc_ini = datetime.datetime.combine(d_insc_ini, h_ab)
                            dt_insc_fim = datetime.datetime.combine(d_insc_fim, h_fn)

                            st.markdown(f"### {evento['nome']}")
                            st.caption(
                                f"📅 Evento: {d_ev_inicio.strftime('%d/%m/%Y')} a {d_ev_fim.strftime('%d/%m/%Y')}"
                            )
                            st.markdown(
                                f"✍️ **Inscrições:** {dt_insc_ini.strftime('%d/%m/%Y %H:%M')} até {dt_insc_fim.strftime('%d/%m/%Y %H:%M')}"
                            )

                            ja_inscrito = False
                            res_ver = (
                                db_provas.table("feira_inscricoes")
                                .select("nomes_membros")
                                .eq("evento_id", evento["id"])
                                .execute()
                            )
                            dados_ver = res_ver.data if (res_ver and hasattr(res_ver, "data") and res_ver.data) else []
                            for insc in dados_ver:
                                if aluno.get("nome") in [
                                    m.replace(" (Líder)", "").strip()
                                    for m in insc.get("nomes_membros", "").split(",")
                                ]:
                                    ja_inscrito = True
                                    break

                            if ja_inscrito:
                                st.error(
                                    "🚨 Você já faz parte de uma equipe inscrita para este evento."
                                )
                                st.button(
                                    "JÁ INSCRITO",
                                    key=f"btn_insc_{evento['id']}",
                                    disabled=True,
                                    use_container_width=True,
                                )
                            elif agora < dt_insc_ini:
                                st.warning(
                                    f"⏳ Inscrições abrem em {dt_insc_ini.strftime('%d/%m às %H:%M')}"
                                )
                                st.button(
                                    "EM BREVE",
                                    key=f"btn_wait_{evento['id']}",
                                    disabled=True,
                                    use_container_width=True,
                                )
                            elif agora > dt_insc_fim:
                                st.error("🚫 Prazo encerrado.")
                                st.button(
                                    "PRAZO ENCERRADO",
                                    key=f"btn_end_{evento['id']}",
                                    disabled=True,
                                    use_container_width=True,
                                )
                            else:
                                if st.button(
                                    f"INSCREVER-SE EM: {evento['nome']}",
                                    type="primary",
                                    key=f"btn_{evento['id']}",
                                    use_container_width=True,
                                ):
                                    st.session_state.evento_selecionado = evento
                                    st.session_state.passo_insc = 2
                                    st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

        # PASSO 2: FILTRAR TEMAS
        elif st.session_state.passo_insc == 2:
            evento = st.session_state.evento_selecionado
            st.subheader(f"Temas Disponíveis para o {serie_aluno} Ano")
            if st.button("⬅️ Voltar"):
                st.session_state.passo_insc = 1
                st.rerun()
            try:
                res_insc = (
                    db_provas.table("feira_inscricoes")
                    .select("tema_id, turma")
                    .eq("evento_id", evento["id"])
                    .execute()
                )
                dados_insc_temas = res_insc.data if (res_insc and hasattr(res_insc, "data") and res_insc.data) else []
                temas_bloqueados = [i["tema_id"] for i in dados_insc_temas if "tema_id" in i]

                disc_bloqueadas_turma = set()
                res_t_all = (
                    db_alunos.table("feira_temas")
                    .select("*")
                    .eq("evento_id", evento["id"])
                    .execute()
                )
                dados_temas_all = res_t_all.data if (res_t_all and hasattr(res_t_all, "data") and res_t_all.data) else []
                todos_dict = {t["id"]: t for t in dados_temas_all}

                for i in dados_insc_temas:
                    if i.get("turma") == turma_aluno and i.get("tema_id") in todos_dict:
                        disc_bloqueadas_turma.add(
                            todos_dict[i["tema_id"]].get("disciplina", "")
                        )

                temas_f = [
                    t
                    for t in dados_temas_all
                    if str(t.get("Serie")).strip() in (serie_aluno, "Geral")
                ]
                temas_por_d = defaultdict(list)
                for t in temas_f:
                    temas_por_d[t.get("disciplina", "Sem Disciplina")].append(t)

                for d in sorted(temas_por_d.keys()):
                    bloq_t = d in disc_bloqueadas_turma
                    label = f"📛 {d} (Sua turma já escolheu)" if bloq_t else f"📚 {d}"
                    with st.expander(label):
                        if bloq_t:
                            st.warning(
                                f"⚠️ A sua turma já selecionou um trabalho desta disciplina."
                            )
                        else:
                            for tema in temas_por_d[d]:
                                bloq_g = tema["id"] in temas_bloqueados
                                st.markdown(
                                    f'<div class="tema-card {"tema-card-bloqueado" if bloq_g else ""}">' ,
                                    unsafe_allow_html=True,
                                )
                                c1, c2 = st.columns([3, 1])
                                with c1:
                                    st.write(f"**{tema['titulo_trabalho']}**")
                                    st.caption(f"👨‍🏫 {tema.get('professor_nome')}")
                                if bloq_g:
                                    c2.button(
                                        "OCUPADO",
                                        key=f"t_{tema['id']}",
                                        disabled=True,
                                        use_container_width=True,
                                    )
                                else:
                                    if c2.button(
                                        "ESCOLHER",
                                        key=f"t_{tema['id']}",
                                        type="primary",
                                        use_container_width=True,
                                    ):
                                        st.session_state.tema_selecionado = tema
                                        st.session_state.passo_insc = 3
                                        st.rerun()
                                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Erro: {e}")

        # PASSO 3: FINALIZAR
        elif st.session_state.passo_insc == 3:
            tema, evento = (
                st.session_state.tema_selecionado,
                st.session_state.evento_selecionado,
            )
            st.success(f"📍 Trabalho: **{tema['titulo_trabalho']}**")
            try:
                res_col = (
                    db_alunos.table("alunos")
                    .select("nome")
                    .eq("turma", turma_aluno)
                    .execute()
                )
                dados_colegas = res_col.data if (res_col and hasattr(res_col, "data") and res_col.data) else []
                t_turma = [
                    c["nome"] for c in dados_colegas if c.get("nome") != aluno.get("nome")
                ]

                res_oc = (
                    db_provas.table("feira_inscricoes")
                    .select("nomes_membros")
                    .eq("evento_id", evento["id"])
                    .eq("turma", turma_aluno)
                    .execute()
                )
                dados_ocupados_passo3 = res_oc.data if (res_oc and hasattr(res_oc, "data") and res_oc.data) else []
                ja_em_grupo = set()
                for insc in dados_ocupados_passo3:
                    for m in [
                        x.replace(" (Líder)", "").strip()
                        for x in insc.get("nomes_membros", "").split(",")
                    ]:
                        ja_em_grupo.add(m)
                disp = sorted([n for n in t_turma if n not in ja_em_grupo])

                with st.form("form_f"):
                    st.markdown("### 👥 Formação da Equipe")
                    st.text_input(
                        "Líder (Você)", value=aluno.get("nome"), disabled=True
                    )
                    m_sel = st.multiselect(
                        "Selecione seus colegas disponíveis na turma:", options=disp
                    )
                    if st.form_submit_button(
                        "CONFIRMAR INSCRIÇÃO", type="primary", use_container_width=True
                    ):
                        total = len(m_sel) + 1
                        if total < int(evento["min_membros"]) or total > int(
                            evento["max_membros"]
                        ):
                            st.error(
                                f"O grupo deve ter entre {evento['min_membros']} e {evento['max_membros']} integrantes."
                            )
                        else:
                            db_provas.table("feira_inscricoes").insert(
                                {
                                    "evento_id": evento["id"],
                                    "tema_id": tema["id"],
                                    "lider_id": id_aluno,
                                    "turma": turma_aluno,
                                    "nomes_membros": f"{aluno.get('nome')} (Líder), {', '.join(m_sel)}" if m_sel else f"{aluno.get('nome')} (Líder)",
                                    "data_inscricao": str(datetime.date.today()),
                                }
                            ).execute()
                            st.balloons()
                            st.success("Inscrição Realizada!")
                            time.sleep(2)
                            st.session_state.passo_insc = 1
                            st.session_state.etapa = "ante_sala"
                            st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
            if st.button("⬅️ Trocar Tema"):
                st.session_state.passo_insc = 2
                st.rerun()

    # =========================================================================
    # ABA 2: MINHAS INSCRIÇÕES (Visualização e Gestão pelo Líder)
    # =========================================================================
    with tab_minhas:
        col_titulo, col_refresh = st.columns([5, 1])
        with col_titulo:
            st.subheader("📋 Inscrições em que você participa")
        with col_refresh:
            if st.button("🔄", help="Atualizar lista", use_container_width=True):
                st.rerun()

        try:
            res_all = db_provas.table("feira_inscricoes").select("*").execute()
            minhas_insc = []
            nome_procurado = aluno.get("nome", "").strip()

            dados_inscricoes = res_all.data if (res_all and hasattr(res_all, "data") and res_all.data) else []

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
                            nome_evento = ev_d.get("nome", "Evento") if isinstance(ev_d, dict) else "Evento"
                            titulo_trabalho = tm_d.get("titulo_trabalho", "Tema não encontrado") if isinstance(tm_d, dict) else "Tema não encontrado"
                            disciplina = tm_d.get("disciplina", "-") if isinstance(tm_d, dict) else "-"

                            st.markdown(f"#### 🏆 {nome_evento}")
                            st.markdown(f"**Trabalho:** {titulo_trabalho}")
                            st.caption(f"🧪 Disciplina: {disciplina}")
                            st.write(f"👥 **Equipe:** {insc.get('nomes_membros', '')}")

                        with c_ops:
                            # VERIFICAÇÃO DE LIDERANÇA DUPLA
                            lider_id_db = str(insc.get("lider_id", "")).strip()
                            aluno_id_sessao = str(id_aluno).strip()
                            nome_lider_rotulo = f"{aluno.get('nome', '').strip()} (Líder)"

                            eh_lider = (
                                (lider_id_db and lider_id_db == aluno_id_sessao) or 
                                (nome_lider_rotulo in insc.get("nomes_membros", ""))
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
                                            .eq("evento_id", insc["evento_id"])
                                            .execute()
                                        )
                                        temas_evento = res_t.data if (res_t and hasattr(res_t, "data") and res_t.data) else []
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
                                        outras_insc = res_i.data if (res_i and hasattr(res_i, "data") and res_i.data) else []

                                        temas_ocupados = [
                                            i["tema_id"] for i in outras_insc if "tema_id" in i
                                        ]
                                        disc_bloqueadas = {
                                            todos_t_dict[i["tema_id"]].get("disciplina")
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
                                            lista_nomes = list(opcoes_tema.keys())
                                            idx_padrao = 0
                                            for i, nome in enumerate(lista_nomes):
                                                if opcoes_tema[nome] == tema_atual_id:
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
                                    "👥 Gerenciar Membros", use_container_width=True
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
                                            dados_alunos = res_c.data if (res_c and hasattr(res_c, "data") and res_c.data) else []
                                            todos_nomes_turma = [
                                                c["nome"]
                                                for c in dados_alunos
                                                if c.get("nome") != aluno.get("nome")
                                            ]

                                            # Busca quem já está em outras equipes
                                            res_o = (
                                                db_provas.table("feira_inscricoes")
                                                .select("nomes_membros")
                                                .eq("evento_id", insc["evento_id"])
                                                .neq("id", insc["id"])
                                                .execute()
                                            )
                                            dados_outros = res_o.data if (res_o and hasattr(res_o, "data") and res_o.data) else []
                                            ocupados_outros = set()
                                            for out in dados_outros:
                                                for m in [
                                                    x.replace(" (Líder)", "").strip()
                                                    for x in out.get("nomes_membros", "").split(",")
                                                ]:
                                                    ocupados_outros.add(m)

                                            disp_edit = sorted(
                                                [
                                                    n
                                                    for n in todos_nomes_turma
                                                    if n not in ocupados_outros
                                                ]
                                            )

                                            # Membros atualmente cadastrados no banco para esta inscrição
                                            atuais = [
                                                m.replace(" (Líder)", "").strip()
                                                for m in insc.get("nomes_membros", "").split(",")
                                                if "(Líder)" not in m
                                            ]

                                            # 🎯 CHAVE ÚNICA DE SESSÃO: Garante a persistência dos nomes selecionados no Multiselect
                                            ms_key = f"ms_membros_{insc['id']}"
                                            if ms_key not in st.session_state:
                                                st.session_state[ms_key] = [m for m in atuais if m in disp_edit]

                                            novos_membros = st.multiselect(
                                                "Selecione os integrantes:",
                                                options=disp_edit,
                                                key=ms_key
                                            )

                                            if st.button(
                                                "💾 Atualizar Equipe",
                                                key=f"btn_save_m_{insc['id']}",
                                                use_container_width=True,
                                                type="primary",
                                            ):
                                                total = len(novos_membros) + 1
                                                min_e = int(ev_d.get("min_membros", 1))
                                                max_e = int(ev_d.get("max_membros", 8))

                                                if total < min_e or total > max_e:
                                                    st.error(
                                                        f"⚠️ A equipe deve ter entre {min_e} e {max_e} integrantes. (Atual: {total})"
                                                    )
                                                else:
                                                    if novos_membros:
                                                        equipe_final = (
                                                            f"{aluno.get('nome').strip()} (Líder), "
                                                            + ", ".join(novos_membros)
                                                        )
                                                    else:
                                                        equipe_final = f"{aluno.get('nome').strip()} (Líder)"

                                                    # Atualização explícita no Supabase
                                                    res_up = db_provas.table("feira_inscricoes").update(
                                                        {"nomes_membros": equipe_final}
                                                    ).eq("id", insc["id"]).execute()

                                                    if res_up and hasattr(res_up, "data") and res_up.data:
                                                        st.success("✅ Equipe atualizada com sucesso!")
                                                        # Limpa a chave da sessão para recarregar com os novos dados
                                                        st.session_state.pop(ms_key, None)
                                                        time.sleep(1)
                                                        st.rerun()
                                                    else:
                                                        st.error("❌ O Supabase não confirmou a atualização. Verifique as permissões (RLS).")

                                        except Exception as e_edit:
                                            st.error(f"Erro ao atualizar integrantes: {e_edit}")
                                    else:
                                        st.warning("Dados do evento não encontrados para validação.")

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