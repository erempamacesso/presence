import streamlit as st
import pandas as pd
import io
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota):
        return nota
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else:
        return float(inteiro + 1)


def eh_recuperacao(prova):
    return prova.get("recuperacao") is True or str(prova.get("recuperacao")).lower() == "true"


def buscar_resultados_da_prova(supabase, prova_id_original):
    """Busca resultados tolerando prova_id salvo como texto ou número."""
    prova_id_texto = str(prova_id_original)
    registros = []

    try:
        res_texto = supabase.table("resultados_provas") \
            .select("aluno_id, questao_id, acertou, prova_id") \
            .eq("prova_id", prova_id_texto) \
            .execute()
        registros.extend(res_texto.data or [])
    except Exception:
        pass

    if prova_id_original != prova_id_texto:
        try:
            res_original = supabase.table("resultados_provas") \
                .select("aluno_id, questao_id, acertou, prova_id") \
                .eq("prova_id", prova_id_original) \
                .execute()
            registros.extend(res_original.data or [])
        except Exception:
            pass

    vistos = set()
    unicos = []
    for item in registros:
        chave = (
            str(item.get("aluno_id")),
            str(item.get("questao_id")),
            str(item.get("prova_id")),
        )
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)
    return unicos




def unidade_da_prova_analise(prova):
    titulo = str(prova.get("titulo", "")).upper()
    referencias = [
        ("4", ["4º BIMESTRE", "4Âº BIMESTRE", "4º TRIMESTRE", "4Âº TRIMESTRE", "4 BIMESTRE", "4 TRIMESTRE"]),
        ("3", ["3º BIMESTRE", "3Âº BIMESTRE", "3º TRIMESTRE", "3Âº TRIMESTRE", "3 BIMESTRE", "3 TRIMESTRE"]),
        ("2", ["2º BIMESTRE", "2Âº BIMESTRE", "2º TRIMESTRE", "2Âº TRIMESTRE", "2 BIMESTRE", "2 TRIMESTRE"]),
        ("1", ["1º BIMESTRE", "1Âº BIMESTRE", "1º TRIMESTRE", "1Âº TRIMESTRE", "1 BIMESTRE", "1 TRIMESTRE"]),
    ]
    for numero, termos in referencias:
        if any(termo in titulo for termo in termos):
            return f"{numero}º Bimestre"
    return "1º Bimestre"


def prefixo_turma_da_prova(prova):
    serie = str(prova.get("serie", ""))
    titulo = str(prova.get("titulo", ""))
    base = serie or titulo
    if "3" in base:
        return "3"
    if "2" in base:
        return "2"
    if "1" in base:
        return "1"
    return ""


def carregar_notas_recuperacao_consolidadas(supabase, prova):
    unidade = unidade_da_prova_analise(prova)
    prefixo_turma = prefixo_turma_da_prova(prova)

    query = supabase.table("notas_atividades").select("aluno_id, turma, rec").eq("unidade", unidade)
    if prefixo_turma:
        query = query.ilike("turma", f"{prefixo_turma}%")
    res = query.execute()

    dados = []
    for item in (res.data or []):
        rec = item.get("rec")
        if rec is None:
            continue
        try:
            rec_float = float(rec)
        except (TypeError, ValueError):
            continue
        if rec_float <= 0:
            continue
        dados.append({
            "aluno_id": str(item.get("aluno_id")),
            "turma_rec": item.get("turma"),
            "nota_rec": rec_float,
        })
    return pd.DataFrame(dados)



def recalcular_notas_recuperacao_analise(df_res, valor_q):
    if df_res.empty:
        return pd.DataFrame(columns=["aluno_id", "nota_calculada"])

    df_calc = df_res[df_res["acertou"] == True].copy()
    if df_calc.empty:
        return pd.DataFrame(columns=["aluno_id", "nota_calculada"])

    df_calc["aluno_id"] = df_calc["aluno_id"].astype(str)
    df_calc["prova_id"] = df_calc["prova_id"].astype(str)
    df_calc["questao_id"] = df_calc["questao_id"].astype(str)
    df_calc = df_calc.drop_duplicates(subset=["aluno_id", "prova_id", "questao_id"])
    notas = df_calc.groupby("aluno_id").size().reset_index(name="acertos_unicos")
    notas["nota_calculada"] = (notas["acertos_unicos"] * valor_q).clip(upper=10).apply(arredondar_siepe)
    return notas[["aluno_id", "nota_calculada"]]

def mostrar_tela_analise(supabase, supabase_alunos):
    st.markdown("## 📊 Análise de Dados e Notas")

    try:
        # 1. BUSCA DE DADOS MESTRE (Modelos e Alunos)
        res_p_modelos = supabase.table("modelos_prova") \
            .select("id, titulo, valor_questao, recuperacao, serie") \
            .order("id", desc=True) \
            .execute()
        res_alunos_base = supabase_alunos.table("alunos").select("id, turma, nome").execute()

        if not res_p_modelos.data:
            st.warning("Nenhuma prova encontrada no banco de dados.")
            return

        # SELETOR DE PROVA
        provas_dict = {}
        for p in res_p_modelos.data:
            tag_rec = " [RECUPERAÇÃO]" if eh_recuperacao(p) else ""
            rotulo = f"ID {p['id']} - {p.get('titulo', 'Sem título')}{tag_rec}"
            provas_dict[rotulo] = p

        prova_nome = st.selectbox("🎯 Selecione a Prova para Monitorar:", list(provas_dict.keys()))
        prova_obj = provas_dict[prova_nome]
        id_prova = prova_obj["id"]

        if eh_recuperacao(prova_obj):
            st.info("Esta atividade está marcada como recuperação.")

        # 2. BUSCA DE RESULTADOS (Cálculo antes de mostrar qualquer gráfico)
        resultados_prova = buscar_resultados_da_prova(supabase, id_prova)
        df_rec = carregar_notas_recuperacao_consolidadas(supabase, prova_obj) if eh_recuperacao(prova_obj) else pd.DataFrame()

        if (not resultados_prova and df_rec.empty) or not res_alunos_base.data:
            st.info("ℹ️ Ainda não existem envios para esta prova.")
            return

        # --- PROCESSAMENTO DE DADOS (O Coração do Dashboard) ---
        df_alunos = pd.DataFrame(res_alunos_base.data)
        df_alunos["id"] = df_alunos["id"].astype(str)
        valor_q = float(prova_obj.get("valor_questao", 1.0) or 1.0)

        if resultados_prova:
            df_res = pd.DataFrame(resultados_prova)
            df_res["aluno_id"] = df_res["aluno_id"].astype(str)
            df_res["questao_id"] = df_res["questao_id"].astype(str)
            df_res["pontos"] = df_res["acertou"].apply(lambda x: 1 if x is True else 0)
            df_notas = df_res.groupby("aluno_id").agg(total_acertos=("pontos", "sum")).reset_index()
            df_notas["nota_final"] = (df_notas["total_acertos"] * valor_q).apply(arredondar_siepe)
        else:
            df_res = pd.DataFrame(columns=["aluno_id", "questao_id", "acertou", "prova_id", "pontos"])
            df_notas = pd.DataFrame(columns=["aluno_id", "total_acertos", "nota_final"])

        if eh_recuperacao(prova_obj):
            df_calc_rec = recalcular_notas_recuperacao_analise(df_res, valor_q)
            if not df_rec.empty:
                df_notas = pd.merge(df_notas, df_rec, on="aluno_id", how="outer")
            if not df_calc_rec.empty:
                df_notas = pd.merge(df_notas, df_calc_rec, on="aluno_id", how="outer")
            df_notas["total_acertos"] = df_notas["total_acertos"].fillna(0).astype(int)
            if "nota_calculada" in df_notas.columns:
                df_notas["nota_final"] = df_notas["nota_calculada"].combine_first(df_notas["nota_final"])
                df_notas = df_notas.drop(columns=["nota_calculada"])
            if "nota_rec" in df_notas.columns:
                df_notas["nota_final"] = df_notas["nota_final"].combine_first(df_notas["nota_rec"])
                df_notas = df_notas.drop(columns=["nota_rec"])

        # Criação do dataframe principal (df_final agora existe ANTES dos gráficos)
        df_final = pd.merge(df_alunos, df_notas, left_on="id", right_on="aluno_id", how="right")
        if "turma_rec" in df_final.columns:
            df_final["turma"] = df_final["turma"].fillna(df_final["turma_rec"])
            df_final = df_final.drop(columns=["turma_rec"])
        df_final["nome"] = df_final["nome"].fillna("Aluno ID " + df_final["aluno_id"].astype(str))
        df_final["turma"] = df_final["turma"].fillna("Sem turma")

        if df_final.empty:
            st.warning("Não foi possível cruzar os dados dos alunos com os resultados.")
            return

        # ---------------------------------------------------------
        # 3. ÁREA DE GRÁFICOS
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("📈 Desempenho e Progresso por Turma")

        g1, g2 = st.columns(2)

        with g1:
            # Média de notas por turma
            df_media = df_final.groupby("turma")["nota_final"].mean().reset_index()
            st.write("**Média de Notas**")
            st.bar_chart(data=df_media, x="turma", y="nota_final", color="#2b83ba")
            st.caption("Desempenho acadêmico médio de cada turma.")

        with g2:
            # Total de alunos que fizeram por turma
            df_participacao = df_final.drop_duplicates(subset=["aluno_id"]).groupby("turma").size().reset_index(name="total")
            st.write("**Total de Participantes**")
            st.bar_chart(data=df_participacao, x="turma", y="total", color="#abdda4")
            st.caption("Quantidade de alunos que concluíram a prova.")

        st.markdown("---")

        # ↓↓ INÍCIO DO NOVO COMANDO: RAIO-X PEDAGÓGICO ↓↓
        st.subheader("🧠 Raio-X Pedagógico (Onde a turma precisa de ajuda?)")

        try:
            # Pega os IDs de todas as questões que apareceram nesses resultados
            if "questao_id" in df_res.columns:
                ids_questoes_feitas = df_res["questao_id"].dropna().unique().tolist()

                if ids_questoes_feitas:
                    # Busca na tabela de questões qual é o 'assunto' de cada questão
                    res_assuntos = supabase.table("questoes").select("id, assunto").in_("id", ids_questoes_feitas).execute()

                    if res_assuntos.data:
                        df_questoes = pd.DataFrame(res_assuntos.data)
                        df_questoes = df_questoes.rename(columns={"id": "questao_id"})
                        df_questoes["questao_id"] = df_questoes["questao_id"].astype(str)

                        # Preenche assuntos vazios com 'Sem classificação'
                        df_questoes["assunto"] = df_questoes["assunto"].fillna("Assunto não categorizado")

                        # Cruza quem acertou/errou com o assunto da questão
                        df_cruzado = pd.merge(df_res, df_questoes, on="questao_id", how="left")

                        # Calcula a PORCENTAGEM de acerto por assunto
                        df_desempenho_assunto = df_cruzado.groupby("assunto")["pontos"].mean().reset_index()
                        df_desempenho_assunto["taxa_acerto"] = df_desempenho_assunto["pontos"] * 100

                        # Separa os assuntos críticos (menos de 50% de acerto) dos dominados
                        df_desempenho_assunto = df_desempenho_assunto.sort_values(by="taxa_acerto", ascending=True)

                        st.write("Porcentagem de acertos da turma em cada competência avaliada:")

                        # Exibe o gráfico de barras
                        st.bar_chart(
                            data=df_desempenho_assunto,
                            x="taxa_acerto",
                            y="assunto",
                            color="#f46d43"
                        )

                        # Alertar o professor sobre os tópicos mais fracos
                        assuntos_criticos = df_desempenho_assunto[df_desempenho_assunto["taxa_acerto"] < 50]["assunto"].tolist()
                        if assuntos_criticos:
                            st.error(f"🚨 **Alerta de Revisão!** A turma teve menos de 50% de aproveitamento nos seguintes assuntos: **{', '.join(assuntos_criticos)}**")
                        else:
                            st.success("✨ Excelente! A turma teve mais de 50% de aproveitamento em todos os assuntos avaliados.")
            else:
                st.info("A coluna 'questao_id' não foi encontrada para gerar o gráfico.")

        except Exception as e:
            st.info(f"Para ver o gráfico, certifique-se de que a tabela 'questoes' possui a coluna 'assunto'. (Detalhe: {e})")

        st.markdown("---")
        # ↑↑ FIM DO NOVO COMANDO: RAIO-X PEDAGÓGICO ↑↑

        # ---------------------------------------------------------
        # 4. DIVISÃO EM COLUNAS (Tabela vs Monitoramento Lateral)
        # ---------------------------------------------------------
        col_tabela, col_monitor = st.columns([2, 1], gap="large")

        with col_tabela:
            st.subheader("📋 Notas Detalhadas")
            st.dataframe(
                df_final[["nome", "turma", "total_acertos", "nota_final"]].sort_values(["turma", "nome"]),
                use_container_width=True,
                height=450,
                column_config={
                    "nome": "Estudante",
                    "turma": "Turma",
                    "total_acertos": "Acertos",
                    "nota_final": st.column_config.NumberColumn("Nota da Atividade", format="%.1f")
                }
            )

            # Exportação Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                for turma in sorted(df_final["turma"].unique()):
                    df_turma = df_final[df_final["turma"] == turma].copy()
                    df_turma.to_excel(writer, sheet_name=f"Turma {turma}", index=False)

            st.download_button(
                label="📥 Baixar Relatório Completo (.xlsx)",
                data=output.getvalue(),
                file_name=f"Notas_{prova_nome}.xlsx",
                type="primary"
            )

        with col_monitor:
            st.subheader("👥 Status de Envio")
            if st.button("🔄 Atualizar agora", use_container_width=True):
                st.rerun()

            alunos_concluintes = df_final.drop_duplicates(subset=["aluno_id"]).sort_values(["turma", "nome"])
            stats = alunos_concluintes.groupby("turma").size().reset_index(name="qtd")

            for _, row in stats.iterrows():
                nomes_turma = alunos_concluintes[alunos_concluintes["turma"] == row["turma"]]["nome"].tolist()
                st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #2b83ba; margin-bottom: 10px;">
                        <span style="color: #6c757d; font-size: 14px;">TURMA {row['turma']}</span><br>
                        <span style="font-size: 22px; font-weight: bold; color: #1e293b;">{row['qtd']} Alunos Concluíram</span>
                    </div>
                """, unsafe_allow_html=True)
                with st.expander("Ver alunos", expanded=True):
                    for nome in nomes_turma:
                        st.write(f"✅ {nome}")

    except Exception as e:
        st.error(f"❌ Ocorreu um erro no processamento: {e}")
