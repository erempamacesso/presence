import streamlit as st
import pandas as pd


def exibir_importacao(supabase):
    st.title("📤 Sistema de Sincronização SIGERPAM")
    st.markdown("---")

    # ─────────────────────────────────────────────
    # 1. UPLOAD DO ARQUIVO
    # ─────────────────────────────────────────────
    arquivo = st.file_uploader("Suba a planilha oficial do SIEPE", type=["xls", "xlsx"])

    if not arquivo:
        return

    try:
        xl = pd.ExcelFile(arquivo)
        abas_turmas = [a for a in xl.sheet_names if "EM45" in a]

        if not abas_turmas:
            st.error("Nenhuma aba com 'EM45' encontrada na planilha.")
            return

        # ─────────────────────────────────────────────
        # 2. LEITURA DA PLANILHA
        # ─────────────────────────────────────────────
        dados_lidos = []

        for aba in abas_turmas:
            sigla = aba.split('-')[-1].strip() if '-' in aba else aba.strip()
            turma_f = (
                f"{sigla[0]}º {sigla[-1]}"
                if len(sigla) >= 2 and sigla[0].isdigit()
                else aba
            )

            df = pd.read_excel(xl, sheet_name=aba, header=0)
            df.columns = df.columns.str.strip().str.upper()

            # Busca flexível pelas colunas
            col_nome       = next((c for c in df.columns if "NOME"        in c), None)
            col_matricula  = next((c for c in df.columns if "MATR"        in c), None)
            col_nascimento = next((c for c in df.columns if "NASCIMENTO"  in c or "NASC" in c), None)
            col_sexo       = next((c for c in df.columns if "SEXO"        in c), None)
            col_situacao   = next((c for c in df.columns if "SITUA"       in c), None)

            if not col_nome:
                st.warning(f"Aba '{aba}' ignorada: coluna NOME não encontrada.")
                continue

            df = df.dropna(subset=[col_nome])

            for _, linha in df.iterrows():
                nome_limpo = str(linha[col_nome]).strip().upper()
                if not nome_limpo or nome_limpo == "NAN":
                    continue

                matricula = (
                    str(linha[col_matricula]).strip()
                    if col_matricula and pd.notna(linha[col_matricula])
                    else ""
                )
                nascimento = (
                    str(linha[col_nascimento]).strip()
                    if col_nascimento and pd.notna(linha[col_nascimento])
                    else ""
                )
                sexo_raw = linha[col_sexo] if col_sexo and pd.notna(linha.get(col_sexo)) else None
                sexo = str(sexo_raw)[0].upper() if sexo_raw else ""

                situacao = (
                    str(linha[col_situacao]).strip().upper()
                    if col_situacao and pd.notna(linha.get(col_situacao))
                    else "NÃO INFORMADA"
                )

                dados_lidos.append({
                    "nome":             nome_limpo,
                    "turma":            turma_f,
                    "numero_matricula": matricula,
                    "data_nascimento":  nascimento,
                    "sexo":             sexo,
                    "situacao":         situacao,
                    "aba_original":     aba,
                })

        if not dados_lidos:
            st.error("Nenhum aluno foi encontrado nas abas da planilha.")
            return

        df_excel = pd.DataFrame(dados_lidos).drop_duplicates(subset=["nome"])
        st.success(f"Planilha lida com sucesso! **{len(df_excel)}** alunos encontrados.")

        # ─────────────────────────────────────────────
        # 3. ABAS DA INTERFACE
        # ─────────────────────────────────────────────
        tab_raio_x, tab_cruzamento, tab_sincronismo = st.tabs([
            "🔍 1. Raio-X da Planilha",
            "📊 2. Cruzamento com o Banco",
            "🚀 3. Sincronizar",
        ])

        # ══════════════════════════════════════════════
        # ABA 1 — RAIO-X (igual ao raiox.py)
        # ══════════════════════════════════════════════
        with tab_raio_x:
            st.subheader("Resumo por Turma")
            resumo = df_excel.groupby("turma").size().reset_index(name="Total de Alunos")
            st.dataframe(resumo, hide_index=True, use_container_width=True)

            st.divider()

            col_esq, col_dir = st.columns([1, 2])

            with col_esq:
                st.subheader("Lista por Sala")
                turma_sel = st.selectbox(
                    "Selecione a turma:",
                    ["Todas"] + sorted(df_excel["turma"].unique().tolist()),
                )
                df_exibir = (
                    df_excel if turma_sel == "Todas"
                    else df_excel[df_excel["turma"] == turma_sel]
                )
                st.dataframe(
                    df_exibir[["nome", "turma", "numero_matricula", "situacao"]].sort_values("nome"),
                    hide_index=True,
                    use_container_width=True,
                )

            with col_dir:
                st.subheader("🔎 Busca Rápida por Nome")
                busca = st.text_input("Digite o nome do aluno:")
                if busca:
                    resultado = df_excel[df_excel["nome"].str.contains(busca.strip().upper())]
                    if not resultado.empty:
                        st.error(f"⚠️ **{busca.upper()}** ESTÁ na planilha.")
                        st.dataframe(resultado, hide_index=True, use_container_width=True)
                    else:
                        st.success(f"✅ **{busca.upper()}** NÃO está na planilha.")

        # ══════════════════════════════════════════════
        # ABA 2 — CRUZAMENTO COM O BANCO
        # ══════════════════════════════════════════════
        with tab_cruzamento:
            st.subheader("Comparação com o Banco de Dados (Supabase)")
            st.write("Clique para verificar as três situações abaixo.")

            if st.button("🔍 Iniciar Cruzamento", type="primary"):

                with st.spinner("Buscando alunos no Supabase..."):
                    res_bd = supabase.table("alunos").select(
                        "nome, turma, numero_matricula, data_nascimento, sexo"
                    ).execute()
                    df_bd = pd.DataFrame(res_bd.data) if res_bd.data else pd.DataFrame(
                        columns=["nome", "turma", "numero_matricula", "data_nascimento", "sexo"]
                    )

                nomes_excel = set(df_excel["nome"])
                nomes_bd    = set(df_bd["nome"]) if not df_bd.empty else set()

                # ── A) Alunos novos (na planilha, fora do banco) ──
                novos       = nomes_excel - nomes_bd
                # ── B) Transferidos (no banco, fora da planilha) ──
                transferidos = nomes_bd - nomes_excel
                # ── C) No banco e na planilha, mas com dados incompletos ──
                em_comum    = nomes_excel & nomes_bd
                df_comuns_bd = df_bd[df_bd["nome"].isin(em_comum)].copy()

                def campo_vazio(val):
                    return (
                        val is None
                        or str(val).strip() == ""
                        or str(val).strip().upper() in ("NAN", "NONE", "NAT")
                    )

                mask_incompletos = df_comuns_bd.apply(
                    lambda r: (
                        campo_vazio(r.get("numero_matricula"))
                        or campo_vazio(r.get("data_nascimento"))
                        or campo_vazio(r.get("sexo"))
                    ),
                    axis=1,
                )
                df_incompletos = df_comuns_bd[mask_incompletos].copy()

                # Marca quais campos faltam
                def quais_faltam(r):
                    faltando = []
                    if campo_vazio(r.get("numero_matricula")): faltando.append("matrícula")
                    if campo_vazio(r.get("data_nascimento")):  faltando.append("nascimento")
                    if campo_vazio(r.get("sexo")):             faltando.append("sexo")
                    return ", ".join(faltando)

                if not df_incompletos.empty:
                    df_incompletos["campos_faltando"] = df_incompletos.apply(quais_faltam, axis=1)

                # Salva no session_state para usar na aba 3
                st.session_state["_cruzamento"] = {
                    "df_excel":       df_excel,
                    "df_bd":          df_bd,
                    "novos":          novos,
                    "transferidos":   transferidos,
                    "df_incompletos": df_incompletos,
                }

                # ── Exibição ──
                st.divider()

                # Métricas rápidas no topo
                m1, m2, m3 = st.columns(3)
                m1.metric("🟢 Alunos Novos",        len(novos))
                m2.metric("🔴 Transferidos",         len(transferidos))
                m3.metric("🟡 Dados Incompletos",    len(df_incompletos))

                st.divider()

                # ── A) Novos ──
                with st.expander(f"🟢 A) Alunos NOVOS — presentes na planilha, ausentes no banco ({len(novos)})", expanded=True):
                    if novos:
                        df_novos_exib = df_excel[df_excel["nome"].isin(novos)][
                            ["nome", "turma", "numero_matricula", "data_nascimento", "sexo"]
                        ].sort_values("turma")
                        st.dataframe(df_novos_exib, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhum aluno novo.")

                # ── B) Transferidos ──
                with st.expander(f"🔴 B) TRANSFERIDOS — presentes no banco, ausentes na planilha ({len(transferidos)})", expanded=True):
                    if transferidos:
                        df_transf_exib = df_bd[df_bd["nome"].isin(transferidos)][
                            ["nome", "turma"]
                        ].sort_values("turma")
                        st.dataframe(df_transf_exib, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhum transferido.")

                # ── C) Dados incompletos ──
                with st.expander(f"🟡 C) DADOS INCOMPLETOS — no banco e na planilha, mas faltando campos ({len(df_incompletos)})", expanded=True):
                    if not df_incompletos.empty:
                        cols_exib = ["nome", "turma", "numero_matricula", "data_nascimento", "sexo", "campos_faltando"]
                        st.dataframe(
                            df_incompletos[cols_exib].sort_values("turma"),
                            hide_index=True,
                            use_container_width=True,
                        )
                    else:
                        st.info("Todos os alunos em comum têm matrícula, nascimento e sexo preenchidos.")

        # ══════════════════════════════════════════════
        # ABA 3 — SINCRONIZAR
        # ══════════════════════════════════════════════
        with tab_sincronismo:
            st.subheader("Aplicar Alterações no SIGERPAM")

            if "_cruzamento" not in st.session_state:
                st.info("⬅️ Primeiro execute o cruzamento na Aba 2.")
                return

            dados  = st.session_state["_cruzamento"]
            novos        = dados["novos"]
            transferidos = dados["transferidos"]
            df_excel_s   = dados["df_excel"]
            df_incompletos = dados["df_incompletos"]

            tem_mudanca = bool(novos or transferidos)

            if not tem_mudanca:
                st.success("✅ Banco já está idêntico à planilha. Nenhuma ação de entrada/saída necessária.")
            else:
                st.warning(
                    f"⚠️ Serão realizadas as seguintes ações:\n\n"
                    f"- **Inserir** {len(novos)} aluno(s) novo(s)\n"
                    f"- **Remover** {len(transferidos)} aluno(s) transferido(s)"
                )

            if not df_incompletos.empty:
                st.info(
                    f"ℹ️ {len(df_incompletos)} aluno(s) com dados incompletos **não serão alterados** automaticamente. "
                    "Corrija manualmente no Supabase ou na planilha."
                )

            if tem_mudanca:
                st.error("🔴 **ATENÇÃO:** a remoção é permanente. Confira a Aba 2 antes de confirmar.")
                confirmar = st.button("🚀 CONFIRMAR E SINCRONIZAR AGORA", type="primary")

                if confirmar:
                    with st.spinner("Sincronizando..."):
                        erros = []

                        # Remove transferidos
                        for nome_rem in transferidos:
                            try:
                                supabase.table("alunos").delete().eq("nome", nome_rem).execute()
                            except Exception as e:
                                erros.append(f"Erro ao remover '{nome_rem}': {e}")

                        # Insere/atualiza novos
                        if novos:
                            registros_novos = (
                                df_excel_s[df_excel_s["nome"].isin(novos)]
                                [[
                                    "nome", "turma",
                                    "numero_matricula", "data_nascimento", "sexo"
                                ]]
                                .rename(columns={
                                    "numero_matricula": "numero_matricula",
                                    "data_nascimento":  "data_nascimento",
                                })
                                .to_dict("records")
                            )
                            # Limpa campos vazios para não sobrescrever com string vazia
                            for r in registros_novos:
                                for k, v in list(r.items()):
                                    if str(v).strip() in ("", "NAN", "NAT", "NONE"):
                                        r[k] = None

                            try:
                                supabase.table("alunos").upsert(
                                    registros_novos, on_conflict="nome"
                                ).execute()
                            except Exception as e:
                                erros.append(f"Erro ao inserir novos alunos: {e}")

                        if erros:
                            for err in erros:
                                st.error(err)
                        else:
                            st.success("🎉 Sincronização concluída com sucesso!")
                            st.balloons()
                            # Limpa o cache do cruzamento
                            del st.session_state["_cruzamento"]

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        raise e