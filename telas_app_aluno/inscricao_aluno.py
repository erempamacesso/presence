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

    # Identificação da estudante
    aluno = st.session_state.get("aluno", {})
    turma_aluno = aluno.get("turma", "Sem Turma")
    id_aluno = str(aluno.get("id", ""))

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
    # ABA 1: REALIZAR INSCRIÇÃO (Lógica Original do Stepper)
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
                if not res_eventos.data:
                    st.info("No momento não há eventos com inscrições abertas.")
                else:
                    agora = datetime.datetime.now()
                    for evento in res_eventos.data:
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
                            for insc in res_ver.data:
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
                temas_bloqueados = [i["tema_id"] for i in res_insc.data]
                disc_bloqueadas_turma = set()
                res_t_all = (
                    db_alunos.table("feira_temas")
                    .select("*")
                    .eq("evento_id", evento["id"])
                    .execute()
                )
                todos_dict = {t["id"]: t for t in res_t_all.data}
                for i in res_insc.data:
                    if i["turma"] == turma_aluno and i["tema_id"] in todos_dict:
                        disc_bloqueadas_turma.add(
                            todos_dict[i["tema_id"]].get("disciplina", "")
                        )

                temas_f = [
                    t
                    for t in res_t_all.data
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
                                    f'<div class="tema-card {"tema-card-bloqueado" if bloq_g else ""}">',
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
                t_turma = [
                    c["nome"] for c in res_col.data if c["nome"] != aluno.get("nome")
                ]
                res_oc = (
                    db_provas.table("feira_inscricoes")
                    .select("nomes_membros")
                    .eq("evento_id", evento["id"])
                    .eq("turma", turma_aluno)
                    .execute()
                )
                ja_em_grupo = set()
                for insc in res_oc.data:
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
                                    "nomes_membros": f"{aluno.get('nome')} (Líder), {', '.join(m_sel)}",
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
        st.subheader("📋 Inscrições em que você participa")
        try:
            # Busca todas as inscrições para filtrar localmente (garante encontrar o aluno como membro ou líder)
            res_all = db_provas.table("feira_inscricoes").select("*").execute()
            minhas_insc = []
            nome_procurado = aluno.get("nome", "")

            for insc in res_all.data or []:
                membros_limpos = [
                    m.replace(" (Líder)", "").strip()
                    for m in insc.get("nomes_membros", "").split(",")
                ]
                if nome_procurado in membros_limpos:
                    minhas_insc.append(insc)

            if not minhas_insc:
                st.info("Você ainda não está em nenhuma equipe inscrita.")
            else:
                for insc in minhas_insc:
                    # Busca nomes reais do evento e tema para exibição
                    ev_d = (
                        db_alunos.table("feira_eventos")
                        .select("nome")
                        .eq("id", insc["evento_id"])
                        .maybe_single()
                        .execute()
                        .data
                    )
                    tm_d = (
                        db_alunos.table("feira_temas")
                        .select("titulo_trabalho, disciplina")
                        .eq("id", insc["tema_id"])
                        .maybe_single()
                        .execute()
                        .data
                    )

                    with st.container(border=True):
                        c_inf, c_ops = st.columns([3, 1])
                        with c_inf:
                            st.markdown(f"#### 🏆 {ev_d['nome'] if ev_d else 'Evento'}")
                            st.markdown(
                                f"**Trabalho:** {tm_d['titulo_trabalho'] if tm_d else 'Tema'}"
                            )
                            st.caption(
                                f"🧪 Disciplina: {tm_d['disciplina'] if tm_d else '-'}"
                            )
                            st.write(f"👥 **Equipe:** {insc['nomes_membros']}")

                        with c_ops:
                            # Verificação de Liderança
                            if str(insc.get("lider_id")) == id_aluno:
                                st.success("🌟 Você é o Líder")
                                if st.button(
                                    "🗑️ Excluir Inscrição",
                                    key=f"del_{insc['id']}",
                                    use_container_width=True,
                                    type="secondary",
                                ):
                                    db_provas.table("feira_inscricoes").delete().eq(
                                        "id", insc["id"]
                                    ).execute()
                                    st.toast("Inscrição removida com sucesso!")
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
