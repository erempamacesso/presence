import streamlit as st
import pandas as pd
import io, math
from siepe_api import SiepeClient

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="Registro de Notas", layout="wide")

MAPA_IDS_SIEPE = {
    "2º A": {
        "turma_id": "2483",
        "disciplina_id": "1132",
        "ew_base": "",
        "ew_id": "",
        "dummy": "",
        "bimestre": "1"
    },
    "2º B": {
        "turma_id": "2484",
        "disciplina_id": "1132",
        "ew_base": "",
        "ew_id": "",
        "dummy": "",
        "bimestre": "1"
    }
}

ATIVIDADES = ["AT1", "AT2", "AT3", "AT4", "AT5"]
MEDIAS = ["N1", "N2", "Média", "Rec"]

# =========================================================
# ARREDONDAMENTO
# =========================================================

def arredondar_siepe(nota):

    if pd.isna(nota) or nota is None:
        return None

    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)

    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else:
        return float(inteiro + 1)

# =========================================================
# INTERFACE PRINCIPAL
# =========================================================

def mostrar_tela_boletim(supabase, supabase_alunos):

    st.title("📝 Meu Registro Pessoal de Notas")
    st.info("AT1-AT2: Simulados | AT3-AT5: Diversas | N2: Prova | Rec: Recuperação")

    try:
        # 1. Busca todos os alunos
        resposta_alunos = supabase_alunos.table("alunos").select("*").execute()

        if not resposta_alunos.data:
            st.warning("Nenhum aluno cadastrado.")
            return

        dados_alunos = pd.DataFrame(resposta_alunos.data)
        lista_turmas = sorted(dados_alunos["turma"].unique())

        c1, c2 = st.columns(2)

        with c1:
            turma_sel = st.selectbox("Turma:", lista_turmas)
        with c2:
            unidade_sel = st.selectbox("Bimestre:", ["1", "2", "3", "4"])

        # 2. Busca notas manuais existentes no banco
        resposta_notas = (
            supabase.table("notas_atividades")
            .select("aluno_id, at3, at4, at5, prova, rec")
            .eq("unidade", unidade_sel)
            .execute()
        )

        mapa_notas = {str(n["aluno_id"]): n for n in resposta_notas.data}

        # =========================================================================
        # CORREÇÃO DA CAPTAÇÃO: BUSCA ACERTOS DA RECUPERAÇÃO EM RESULTADOS_PROVAS
        # =========================================================================
        mapa_rec_automatica = {}
        try:
            # Puxa os resultados gerais de provas para processamento local
            resposta_resultados = (
                supabase.table("resultados_provas")
                .select("aluno_id, prova_id, acertou")
                .execute()
            )
            
            if resposta_resultados.data:
                df_resultados = pd.DataFrame(resposta_resultados.data)
                
                # Buscamos as provas mapeadas como recuperação para saber quais considerar
                resposta_provas = (
                    supabase.table("provas")
                    .select("id, valor_questao")
                    .eq("recuperacao", True)
                    .eq("unidade", int(unidade_sel))
                    .execute()
                )
                
                if resposta_provas.data:
                    df_provas_rec = pd.DataFrame(resposta_provas.data)
                    ids_provas_rec = df_provas_rec["id"].astype(str).tolist()
                    
                    # Filtra apenas os resultados que pertencem a essas provas de recuperação
                    df_filtrado = df_resultados[df_resultados["prova_id"].astype(str).isin(ids_provas_rec)]
                    
                    # Filtra apenas onde o aluno acertou (acertou == True)
                    df_acertos = df_filtrado[df_filtrado["acertou"] == True]
                    
                    # Agrupa contando a quantidade de acertos por aluno e prova
                    df_agrupado = df_acertos.groupby(["aluno_id", "prova_id"]).size().reset_index(name="total_acertos")
                    
                    # Junta com o valor da questão para calcular a nota final daquela prova
                    df_provas_rec["id"] = df_provas_rec["id"].astype(str)
                    df_calculado = pd.merge(df_agrupado, df_provas_rec, left_on="prova_id", right_on="id")
                    
                    # Nota = acertos * valor_questao
                    df_calculado["nota_rec"] = df_calculado["total_acertos"] * df_calculado["valor_questao"].astype(float)
                    
                    # Se um aluno fez mais de uma recuperação, pegamos a maior nota
                    df_maior_nota = df_calculado.groupby("aluno_id")["nota_rec"].max().reset_index()
                    
                    for _, row in df_maior_nota.iterrows():
                        # Aplica o arredondamento oficial e joga no mapa temporário da tela
                        nota_redonda = arredondar_siepe(row["nota_rec"])
                        mapa_rec_automatica[str(row["aluno_id"])] = nota_redonda
        except Exception as e_rec:
            # Caso a tabela 'provas' ou colunas novas ainda não existam, evita quebrar a tela inteira
            st.sidebar.warning(f"Aviso de sincronização automática de Rec: {e_rec}")
        # =========================================================================

        # 3. Monta a tabela unificada para exibição
        alunos_filtrados = (
            dados_alunos[dados_alunos["turma"] == turma_sel]
            .sort_values(by="nome")
        )

        linhas_tabela = []

        for _, aluno in alunos_filtrados.iterrows():

            id_aluno = str(aluno["id"])
            registro_nota = mapa_notas.get(id_aluno, {})

            # Notas manuais (Padrão 0.0 se não existirem)
            at3 = float(registro_nota.get("at3", 0.0) or 0.0)
            at4 = float(registro_nota.get("at4", 0.0) or 0.0)
            at5 = float(registro_nota.get("at5", 0.0) or 0.0)
            n2 = float(registro_nota.get("prova", 0.0) or 0.0)

            # Simulados fixos em 0.0
            at1, at2 = 0.0, 0.0

            # Lógica de cálculo sequencial
            n1_calculado = arredondar_siepe(at1 + at2 + at3 + at4 + at5)
            media_calculada = arredondar_siepe(
                ((n1_calculado or 0.0) + n2) / 2
            )

            # --- PRIORIDADE DA RECUPERAÇÃO AUTOMÁTICA ---
            # Se achou resultado na 'resultados_provas', usa ele. Caso contrário, mantém o do 'notas_atividades'
            if id_aluno in mapa_rec_automatica:
                nota_rec = mapa_rec_automatica[id_aluno]
            else:
                nota_rec = registro_nota.get("rec", None)
                if nota_rec is not None:
                    nota_rec = arredondar_siepe(float(nota_rec))

            # Montagem do dicionário estruturado para a linha do DataFrame
            item_tabela = {
                "aluno_id": id_aluno,
                "Nome": aluno["nome"],
                "AT1": at1,
                "AT2": at2,
                "AT3": at3,
                "AT4": at4,
                "AT5": at5,
                "N1": n1_calculado,
                "N2": n2,
                "Média": media_calculada,
                "Rec": nota_rec
            }

            linhas_tabela.append(item_tabela)

        df_visualizacao = pd.DataFrame(linhas_tabela)

        # Configura as travas de edição de colunas calculadas
        config_colunas = {
            "aluno_id": None,
            "Nome": st.column_config.TextColumn(disabled=True),
            "N1": st.column_config.NumberColumn(disabled=True),
            "Média": st.column_config.NumberColumn(disabled=True),
        }

        # Deixa travar também a edição manual de Rec caso ela venha preenchida automaticamente
        for col in ATIVIDADES:
            config_colunas[col] = st.column_config.NumberColumn(
                min_value=0.0, max_value=10.0, step=0.5
            )
        config_colunas["N2"] = st.column_config.NumberColumn(
            min_value=0.0, max_value=10.0, step=0.5
        )
        config_colunas["Rec"] = st.column_config.NumberColumn(
            min_value=0.0, max_value=10.0, step=0.5
        )

        editado = st.data_editor(
            df_visualizacao,
            column_config=config_colunas,
            hide_index=True,
            use_container_width=True,
            key="editor_boletim"
        )

        # 4. Painel de Ações inferiores
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            if st.button(
                "💾 Salvar Notas",
                type="primary",
                use_container_width=True
            ):

                dados_limpos = []

                for _, r in editado.iterrows():

                    def limpar(val):
                        if pd.isna(val) or val is None:
                            return None
                        return float(val)

                    dados_limpos.append({
                        "aluno_id": r["aluno_id"],
                        "unidade": unidade_sel,
                        "at3": limpar(r["AT3"]),
                        "at4": limpar(r["AT4"]),
                        "at5": limpar(r["AT5"]),
                        "prova": limpar(r["N2"]),
                        "rec": limpar(r["Rec"]) # Salva de volta o que calculamos ou ajustamos
                    })

                try:
                    (
                        supabase.table("notas_atividades")
                        .upsert(dados_limpos, on_conflict="aluno_id, unidade")
                        .execute()
                    )
                    st.success("✅ Salvo com distinção de NP!")
                    st.rerun()
                except Exception as e_salvar:
                    st.error(f"Erro ao salvar dados: {e_salvar}")

        with c2:
            cfg = MAPA_IDS_SIEPE.get(turma_sel)
            if cfg and st.button(
                "🚀 Sincronizar SIEPE",
                use_container_width=True
            ):
                try:
                    client = SiepeClient()
                    usuario = st.secrets["SIEPE_USER"]
                    senha = st.secrets["SIEPE_PASS"]

                    with st.spinner("Sincronizando..."):
                        ok, _ = client.fazer_login(usuario, senha)
                        if ok:
                            client.iniciar_robo_navegacao()
                            # Ajusta dinamicamente o bimestre da configuração com base no seletor da tela
                            cfg["bimestre"] = str(unidade_sel)
                            
                            sucesso, msg = (
                                client.sincronizar_dataframe_ao_siepe_final(
                                    editado,
                                    cfg
                                )
                            )
                            st.success(msg) if sucesso else st.error(msg)
                        else:
                            st.error("Falha login SIEPE")
                except Exception as erro:
                    st.error(f"Erro SIEPE: {erro}")

        with c3:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                (
                    editado
                    .drop(columns=["aluno_id"])
                    .to_excel(writer, index=False)
                )

            st.download_button(
                "📥 Baixar Planilha Excel",
                output.getvalue(),
                f"Boletim_{turma_sel}_Bimestre_{unidade_sel}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

        with c4:
            if st.button("🔄 Recarregar Dados", use_container_width=True):
                st.rerun()

    except Exception as erro_geral:
        st.error(f"Ocorreu um erro inesperado: {erro_geral}")