import streamlit as st
import datetime
import time
from github import Github


def exibir_gestao_feira(supabase_conn):
    st.title("🎪 Central de Eventos e Feiras")
    st.markdown("Gerencie os eventos, banners, editais e linhas de pesquisa da escola.")

    # Função para formatar data ISO (2025-05-20) para BR (20/05/2025)
    def formatar_data_br(data_iso):
        if not data_iso:
            return ""
        try:
            return datetime.datetime.strptime(str(data_iso), "%Y-%m-%d").strftime(
                "%d/%m/%Y"
            )
        except:
            return str(data_iso)

    # 1. Função de busca com cache
    @st.cache_data(ttl=60)
    def buscar_eventos_vitrine(_supabase):
        return (
            _supabase.table("feira_eventos")
            .select(
                "id, nome, data_inicio, data_fim, onde, turmas, edital_link, imagem_capa_link, min_membros, max_membros, ativo, insc_abertura, insc_final"
            )
            .eq("ativo", True)
            .execute()
        )

    aba_ver, aba_evento, aba_orientadores, aba_gestao_trabalhos = st.tabs(
        [
            "👀 Ver Eventos Ativos",
            "📅 1. Eventos EREMPAM",
            "👨‍🏫 2. Cadastrar Trabalhos",
            "🔧 3. Gerenciar Trabalhos",
        ]
    )

    # ==========================================
    # ABA 0: VITRINE (FORMATO BR)
    # ==========================================
    with aba_ver:
        if st.button("🔄 Atualizar Vitrine"):
            st.cache_data.clear()
            st.rerun()

        try:
            res = buscar_eventos_vitrine(supabase_conn)
            eventos = res.data

            if not eventos:
                st.info("Nenhum evento ativo no momento.")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        col_img, col_info, col_btn = st.columns([1.5, 3, 1.5])

                        with col_img:
                            link_db = ev.get("imagem_capa_link", "")
                            nome_evento = ev.get("nome", "").upper()

                            # 1. Identifica o caminho do arquivo dentro do GitHub
                            # Se for o NATUMAT antigo ou um link incompleto, ajustamos o caminho
                            caminho_no_github = ""
                            if "NATUMAT" in nome_evento:
                                caminho_no_github = "banners/natumat_2026.png"
                            elif link_db:
                                # Extrai apenas o final do link (ex: banners/arquivo.png)
                                caminho_no_github = link_db.split("/main/")[-1]

                            if caminho_no_github:
                                try:
                                    # 2. USA O TOKEN PARA BUSCAR A IMAGEM NO REPO PRIVADO
                                    token = st.secrets["GITHUB_TOKEN"]
                                    g = Github(token)
                                    # Certifique-se que o nome do repo aqui seja o mesmo do seu secrets
                                    repo = g.get_repo("erempamacesso/presence")

                                    contents = repo.get_contents(caminho_no_github)
                                    # Exibe a imagem usando os bytes decodificados (sem precisar de URL pública)
                                    st.image(
                                        contents.decoded_content,
                                        use_container_width=True,
                                    )

                                except Exception as e:
                                    st.error("Erro ao carregar imagem privada")
                                    # Opcional: st.write(e) para debug
                            else:
                                st.markdown(
                                    "<div style='height: 150px; background-color: #f0f2f6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #888;'>🖼️ Sem Imagem</div>",
                                    unsafe_allow_html=True,
                                )

                        with col_info:
                            st.subheader(f"🏆 {ev.get('nome', 'Evento')}")

                            # Datas do Evento (Formatadas BR)
                            d_ini = formatar_data_br(ev.get("data_inicio"))
                            d_fim = formatar_data_br(ev.get("data_fim"))
                            st.markdown(
                                f"🗓️ **Período do Evento:** <span style='color: #ff4b4b;'>{d_ini} até {d_fim}</span>",
                                unsafe_allow_html=True,
                            )

                            # Datas de Inscrição (Formatadas BR)
                            d_insc_ini = formatar_data_br(ev.get("insc_abertura"))
                            d_insc_fim = formatar_data_br(ev.get("insc_final"))
                            if d_insc_ini and d_insc_fim:
                                st.markdown(
                                    f"✍️ **Inscrições:** <span style='color: #2e7d32; font-weight: bold;'>{d_insc_ini} a {d_insc_fim}</span>",
                                    unsafe_allow_html=True,
                                )

                            st.write(f"📍 **Onde:** {ev.get('onde', 'EREM PAM')}")
                            st.write(f"👥 **Turmas:** {ev.get('turmas', 'Geral')}")

                        with col_btn:
                            v_min, v_max = ev.get("min_membros", 0), ev.get(
                                "max_membros", 0
                            )
                            st.markdown(
                                f"""
                                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e6e6e6; margin-bottom: 12px;">
                                    <span style="font-size: 0.70rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">ALUNOS POR GRUPO</span><br>
                                    <span style="font-size: 1.4rem; font-weight: 800; color: #1f77b4;">{v_min} a {v_max}</span>
                                </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            if ev.get("edital_link"):
                                st.link_button(
                                    "📄 Ver Edital",
                                    ev["edital_link"],
                                    use_container_width=True,
                                )

        except Exception as e:
            st.error(f"Erro ao carregar vitrine: {e}")

    # ==========================================
    # ABA 1: FORMULÁRIO
    # ==========================================
    with aba_evento:
        st.subheader("Configuração de Eventos")

        # Busca todos os eventos para permitir edição
        try:
            res_todos = (
                supabase_conn.table("feira_eventos")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            eventos_lista = res_todos.data if res_todos.data else []
            nomes_eventos = ["-- NOVO EVENTO --"] + [e["nome"] for e in eventos_lista]

            evento_selecionado_nome = st.selectbox(
                "Selecione um evento para editar ou criar um novo:", nomes_eventos
            )
            ev_edit = next(
                (e for e in eventos_lista if e["nome"] == evento_selecionado_nome), None
            )
            is_edit = ev_edit is not None
        except:
            ev_edit = None
            is_edit = False

        with st.form("form_evento_mestre", clear_on_submit=not is_edit):
            nome_evento = st.text_input(
                "Nome do Evento",
                value=ev_edit["nome"] if is_edit else "",
                placeholder="Ex: NATUMAT 2026",
            )

            st.markdown("##### 🗓️ Datas do Evento")
            col1, col2 = st.columns(2)

            def converter_data(data_str):
                try:
                    return datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
                except:
                    return datetime.date.today()

            d_ini = (
                converter_data(ev_edit.get("data_inicio"))
                if is_edit
                else datetime.date.today()
            )
            d_fim = (
                converter_data(ev_edit.get("data_fim"))
                if is_edit
                else datetime.date.today()
            )
            data_inicio = col1.date_input(
                "Data de Início do Evento", value=d_ini, format="DD/MM/YYYY"
            )
            data_fim = col2.date_input(
                "Data de Fim do Evento", value=d_fim, format="DD/MM/YYYY"
            )

            st.markdown("##### ⏳ Período de Inscrições")
            col_insc1, col_insc2 = st.columns(2)

            d_i_ab = (
                converter_data(ev_edit.get("insc_abertura"))
                if is_edit
                else datetime.date.today()
            )
            d_i_fn = (
                converter_data(ev_edit.get("insc_final"))
                if is_edit
                else datetime.date.today()
            )
            data_insc_abertura = col_insc1.date_input(
                "Abertura das Inscrições", value=d_i_ab, format="DD/MM/YYYY"
            )
            data_insc_final = col_insc2.date_input(
                "Encerramento das Inscrições", value=d_i_fn, format="DD/MM/YYYY"
            )

            st.markdown("##### 📍 Detalhes e Regras")
            col3, col4 = st.columns(2)
            local_ev = col3.text_input(
                "Local da Feira",
                value=ev_edit.get("onde", "") if is_edit else "",
                placeholder="Ex: Pátio e Laboratórios",
            )
            turmas_ev = col4.text_input(
                "Público-Alvo / Turmas",
                value=ev_edit.get("turmas", "") if is_edit else "",
                placeholder="Ex: 1º e 2º Anos",
            )

            col5, col6 = st.columns(2)
            min_alunos = col5.number_input(
                "Mínimo de Alunos por Grupo",
                min_value=1,
                value=int(ev_edit.get("min_membros", 4)) if is_edit else 4,
            )
            max_alunos = col6.number_input(
                "Máximo de Alunos por Grupo",
                min_value=1,
                value=int(ev_edit.get("max_membros", 8)) if is_edit else 8,
            )

            observacoes = st.text_area(
                "Observações Extras",
                value=ev_edit.get("observacoes", "") if is_edit else "",
                placeholder="Digite instruções adicionais...",
            )

            if is_edit:
                st.toggle(
                    "Evento Ativo?",
                    value=bool(ev_edit.get("ativo", True)),
                    key="ev_ativo_toggle",
                )

            st.markdown("---")
            st.write("🖼️ **Banner de Divulgação (Imagem)**")
            arquivo_banner = st.file_uploader(
                "Arraste a capa aqui (JPG ou PNG)", type=["png", "jpg", "jpeg"]
            )

            st.write("📄 **Edital Oficial (PDF)**")
            arquivo_pdf = st.file_uploader("Arraste o edital aqui", type=["pdf"])

            salvar_evento = st.form_submit_button(
                "💾 EVENTOS EREMPAM", type="primary", use_container_width=True
            )

            if salvar_evento:
                if not nome_evento:
                    st.warning("⚠️ Você precisa digitar pelo menos o nome do evento!")
                else:
                    try:
                        token = st.secrets["GITHUB_TOKEN"]
                        g = Github(token)
                        repo = g.get_repo("erempamacesso/presence")
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                        link_foto_final = (
                            ev_edit.get("imagem_capa_link", "") if is_edit else ""
                        )
                        if arquivo_banner:
                            path_img = f"banners/banner_{ts}_{arquivo_banner.name}"
                            repo.create_file(
                                path_img,
                                f"Upload Banner: {nome_evento}",
                                arquivo_banner.read(),
                                branch="main",
                            )
                            link_foto_final = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_img}"

                        link_pdf_final = (
                            ev_edit.get("edital_link", "") if is_edit else ""
                        )
                        if arquivo_pdf:
                            path_pdf = f"editais/edital_{ts}_{arquivo_pdf.name}"
                            repo.create_file(
                                path_pdf,
                                f"Upload Edital: {nome_evento}",
                                arquivo_pdf.read(),
                                branch="main",
                            )
                            link_pdf_final = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_pdf}"

                        dados_para_salvar = {
                            "nome": nome_evento,
                            "data_inicio": str(data_inicio),
                            "data_fim": str(data_fim),
                            "insc_abertura": str(data_insc_abertura),
                            "insc_final": str(data_insc_final),
                            "onde": local_ev,
                            "turmas": turmas_ev,
                            "min_membros": min_alunos,
                            "max_membros": max_alunos,
                            "observacoes": observacoes,
                            "imagem_capa_link": link_foto_final,
                            "edital_link": link_pdf_final,
                            "ativo": (
                                st.session_state.get("ev_ativo_toggle", True)
                                if is_edit
                                else True
                            ),
                        }

                        if is_edit:
                            supabase_conn.table("feira_eventos").update(
                                dados_para_salvar
                            ).eq("id", ev_edit["id"]).execute()
                        else:
                            supabase_conn.table("feira_eventos").insert(
                                dados_para_salvar
                            ).execute()

                        # Mensagem de sucesso com datas BR
                        st.success(
                            f"✅ Evento '{nome_evento}' publicado! Inscrições de {data_insc_abertura.strftime('%d/%m/%Y')} até {data_insc_final.strftime('%d/%m/%Y')}."
                        )
                        st.cache_data.clear()
                        time.sleep(2)
                        st.rerun()

                    except Exception as e:
                        st.error(f"🚨 Erro: {e}")

    # ==========================================
    # ABA 2: CADASTRAR TRABALHOS (ORIENTADORES)
    # ==========================================
    with aba_orientadores:
        st.subheader("Cadastro de Linhas de Pesquisa / Temas")
        try:
            res_ev = (
                supabase_conn.table("feira_eventos")
                .select("id, nome")
                .eq("ativo", True)
                .execute()
            )
            dict_eventos = {item["nome"]: item["id"] for item in res_ev.data}

            with st.form("form_novo_trabalho_mestre", clear_on_submit=True):
                ev_selecionado = (
                    st.selectbox("Para qual evento?", list(dict_eventos.keys()))
                    if dict_eventos
                    else None
                )
                res_prof = (
                    supabase_conn.table("professores_matriculas")
                    .select("professor")
                    .execute()
                )
                lista_profs = ["Selecione..."] + sorted(
                    list(set([p["professor"] for p in res_prof.data if p["professor"]]))
                )
                prof_selecionado = st.selectbox("Professor Orientador", lista_profs)

                titulo = st.text_input("Título da Linha de Pesquisa")
                descricao = st.text_area("Descrição Breve")

                # --- NOVOS CAMPOS: DISCIPLINA E SÉRIE ---
                col_disc, col_serie = st.columns(2)
                disciplina_selecionada = col_disc.selectbox(
                    "Disciplina do Trabalho",
                    ["Selecione...", "Química", "Física", "Biologia", "Matemática"],
                )

                serie_selecionada = col_serie.selectbox(
                    "Série Destinada", ["Selecione...", "1º", "2º", "3º", "Geral"]
                )
                # ----------------------------------------

                vagas = st.number_input(
                    "Limite de Grupos (Vagas)", min_value=1, value=5
                )

                if st.form_submit_button("➕ Adicionar Tema", use_container_width=True):
                    # Validação para garantir que o professor escolheu a disciplina e a série
                    if (
                        ev_selecionado
                        and prof_selecionado != "Selecione..."
                        and titulo
                        and disciplina_selecionada != "Selecione..."
                        and serie_selecionada != "Selecione..."
                    ):

                        supabase_conn.table("feira_temas").insert(
                            {
                                "evento_id": dict_eventos[ev_selecionado],
                                "professor_nome": prof_selecionado,
                                "titulo_trabalho": titulo,
                                "descricao": descricao,
                                "vagas_grupos": vagas,
                                "disciplina": disciplina_selecionada,  # NOVO CAMPO
                                "Serie": serie_selecionada,  # NOVO CAMPO (Exatamente como está no Supabase)
                            }
                        ).execute()

                        st.success("✅ Linha de pesquisa cadastrada com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning(
                            "⚠️ Preencha todos os campos obrigatórios (Evento, Orientador, Título, Disciplina e Série)!"
                        )

        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    # ==========================================
    # ABA 3: GERENCIAR TRABALHOS (VIEW/EDIT/DEL)
    # ==========================================
    with aba_gestao_trabalhos:
        st.subheader("Gerenciar Trabalhos Cadastrados")
        try:
            res_ev_g = supabase_conn.table("feira_eventos").select("id, nome").execute()
            dict_ev_g = {item["nome"]: item["id"] for item in res_ev_g.data}

            ev_g_sel = st.selectbox(
                "1. Filtrar por Evento:", ["Selecione..."] + list(dict_ev_g.keys())
            )

            if ev_g_sel != "Selecione...":
                ev_id = dict_ev_g[ev_g_sel]
                res_temas = (
                    supabase_conn.table("feira_temas")
                    .select("*")
                    .eq("evento_id", ev_id)
                    .execute()
                )

                if not res_temas.data:
                    st.info("Nenhum trabalho cadastrado para este evento.")
                else:
                    temas = res_temas.data
                    tema_nomes = {
                        f"{t['titulo_trabalho']} ({t['professor_nome']})": t
                        for t in temas
                    }
                    tema_sel_nome = st.selectbox(
                        "2. Selecione o Trabalho para Gerenciar:",
                        ["Selecione..."] + list(tema_nomes.keys()),
                    )

                    if tema_sel_nome != "Selecione...":
                        t_edit = tema_nomes[tema_sel_nome]

                        with st.form(f"form_edit_tema_{t_edit['id']}"):
                            st.write(f"✍️ Editando: **{t_edit['titulo_trabalho']}**")
                            novo_titulo = st.text_input(
                                "Título da Linha de Pesquisa",
                                value=t_edit["titulo_trabalho"],
                            )
                            nova_desc = st.text_area(
                                "Descrição", value=t_edit["descricao"]
                            )

                            res_prof_g = (
                                supabase_conn.table("professores_matriculas")
                                .select("professor")
                                .execute()
                            )
                            lista_profs_g = sorted(
                                list(
                                    set(
                                        [
                                            p["professor"]
                                            for p in res_prof_g.data
                                            if p["professor"]
                                        ]
                                    )
                                )
                            )
                            novo_prof = st.selectbox(
                                "Professor Orientador",
                                lista_profs_g,
                                index=(
                                    lista_profs_g.index(t_edit["professor_nome"])
                                    if t_edit["professor_nome"] in lista_profs_g
                                    else 0
                                ),
                            )

                            col_d, col_s = st.columns(2)
                            disciplinas = [
                                "Química",
                                "Física",
                                "Biologia",
                                "Matemática",
                            ]
                            nova_disc = col_d.selectbox(
                                "Disciplina",
                                disciplinas,
                                index=(
                                    disciplinas.index(t_edit["disciplina"])
                                    if t_edit["disciplina"] in disciplinas
                                    else 0
                                ),
                            )

                            series = ["1º", "2º", "3º", "Geral"]
                            nova_serie = col_s.selectbox(
                                "Série",
                                series,
                                index=(
                                    series.index(t_edit["Serie"])
                                    if t_edit["Serie"] in series
                                    else 0
                                ),
                            )

                            novas_vagas = st.number_input(
                                "Limite de Grupos (Vagas)",
                                min_value=1,
                                value=int(t_edit["vagas_grupos"]),
                            )

                            c_salvar, c_deletar = st.columns(2)
                            btn_upd = c_salvar.form_submit_button(
                                "💾 Salvar Alterações",
                                use_container_width=True,
                                type="primary",
                            )
                            btn_del = c_deletar.form_submit_button(
                                "🗑️ Excluir Trabalho", use_container_width=True
                            )

                            if btn_upd:
                                supabase_conn.table("feira_temas").update(
                                    {
                                        "titulo_trabalho": novo_titulo,
                                        "descricao": nova_desc,
                                        "professor_nome": novo_prof,
                                        "disciplina": nova_disc,
                                        "Serie": nova_serie,
                                        "vagas_grupos": novas_vagas,
                                    }
                                ).eq("id", t_edit["id"]).execute()
                                st.success("Trabalho atualizado com sucesso!")
                                time.sleep(1)
                                st.rerun()

                            if btn_del:
                                supabase_conn.table("feira_temas").delete().eq(
                                    "id", t_edit["id"]
                                ).execute()
                                st.success("Trabalho removido permanentemente!")
                                time.sleep(1)
                                st.rerun()
        except Exception as e:
            st.error(f"Erro na gestão de trabalhos: {e}")
