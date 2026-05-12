import streamlit as st
import pandas as pd
import io
import math
from siepe_api import SiepeClient

# =========================================================
# CONFIGURAÇÕES
# =========================================================

st.set_page_config(
    page_title="Registro de Notas",
    layout="wide"
)

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
    },
}

COLUNAS_NOTAS = [
    "AT1",
    "AT2",
    "AT3",
    "AT4",
    "AT5",
    "N2",
    "N1",
    "Média",
    "Rec"
]

# =========================================================
# FUNÇÕES
# =========================================================

def arredondar_siepe(nota):
    """
    Arredondamento oficial do SIEPE
    """

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


def estilo_notas(valor):
    """
    Estilo visual das células
    """

    try:

        if pd.isna(valor):
            return """
                color: #9CA3AF;
            """

        valor = float(valor)

        # VERMELHO
        if valor < 6:
            return """
                background-color: #FEF2F2;
                color: #DC2626;
                font-weight: bold;
            """

        # VERDE
        if valor >= 8:
            return """
                background-color: #ECFDF5;
                color: #047857;
                font-weight: bold;
            """

        # AZUL
        return """
            background-color: #EFF6FF;
            color: #1D4ED8;
            font-weight: bold;
        """

    except:
        return "color: #9CA3AF;"


def buscar_simulado(
    supabase,
    ano_ref,
    termo_simulado,
    limite=4.0
):
    """
    Busca notas automáticas dos simulados
    """

    mapa = {}

    try:

        res_prova = (
            supabase
            .table("modelos_prova")
            .select("id, valor_questao")
            .ilike("titulo", f"%{ano_ref}%{termo_simulado}%")
            .execute()
        )

        if not res_prova.data:
            return mapa

        prova = res_prova.data[0]

        prova_id = prova["id"]

        valor_questao = float(
            prova.get("valor_questao") or 1.0
        )

        res_resultados = (
            supabase
            .table("resultados_provas")
            .select("aluno_id, acertou")
            .eq("prova_id", prova_id)
            .execute()
        )

        if not res_resultados.data:
            return mapa

        df = pd.DataFrame(res_resultados.data)

        df = (
            df[df["acertou"] == True]
            .groupby("aluno_id")
            .size()
            .reset_index(name="acertos")
        )

        df["nota"] = (
            (df["acertos"] * valor_questao)
            .clip(upper=limite)
            .apply(arredondar_siepe)
        )

        mapa = dict(
            zip(
                df["aluno_id"].astype(str),
                df["nota"]
            )
        )

    except Exception as erro:
        st.warning(f"Erro simulados: {erro}")

    return mapa


def buscar_recuperacao_automatica(
    supabase,
    ano_ref
):
    """
    Busca REC automática
    """

    mapa = {}

    try:

        res_prova = (
            supabase
            .table("modelos_prova")
            .select("id, valor_questao")
            .eq("recuperacao", True)
            .ilike("titulo", f"%{ano_ref}%")
            .execute()
        )

        if not res_prova.data:
            return mapa

        prova = res_prova.data[0]

        prova_id = prova["id"]

        valor_questao = float(
            prova.get("valor_questao") or 0.5
        )

        res_resultados = (
            supabase
            .table("resultados_provas")
            .select("aluno_id, acertou")
            .eq("prova_id", prova_id)
            .execute()
        )

        if not res_resultados.data:
            return mapa

        df = pd.DataFrame(res_resultados.data)

        df = (
            df[df["acertou"] == True]
            .groupby("aluno_id")
            .size()
            .reset_index(name="acertos")
        )

        df["nota"] = (
            df["acertos"] * valor_questao
        ).apply(arredondar_siepe)

        mapa = dict(
            zip(
                df["aluno_id"].astype(str),
                df["nota"]
            )
        )

    except Exception as erro:
        st.warning(f"Erro REC: {erro}")

    return mapa


def calcular_n1(df):

    atividades = [
        "AT1",
        "AT2",
        "AT3",
        "AT4",
        "AT5"
    ]

    df["N1"] = (
        df[atividades]
        .fillna(0)
        .sum(axis=1)
        .apply(arredondar_siepe)
    )

    return df


def calcular_media(df):

    df["Média"] = (
        (
            df["N1"].fillna(0)
            +
            df["N2"].fillna(0)
        ) / 2
    ).apply(arredondar_siepe)

    return df


def carregar_dados_turma(
    supabase,
    supabase_alunos,
    turma
):
    """
    Carrega todos os dados
    """

    res_alunos = (
        supabase_alunos
        .table("alunos")
        .select("*")
        .execute()
    )

    df_alunos = pd.DataFrame(res_alunos.data)

    df_alunos = (
        df_alunos[df_alunos["turma"] == turma]
        .copy()
    )

    df_alunos = df_alunos.rename(
        columns={
            "id": "aluno_id",
            "nome": "nome"
        }
    )

    ano_ref = (
        "2º ano"
        if "2º" in turma
        else "3º ano"
    )

    # =====================================================
    # SIMULADOS
    # =====================================================

    mapa_at1 = buscar_simulado(
        supabase,
        ano_ref,
        "1º Simulado"
    )

    mapa_at2 = buscar_simulado(
        supabase,
        ano_ref,
        "2º Simulado"
    )

    # =====================================================
    # NOTAS MANUAIS
    # =====================================================

    res_notas = (
        supabase
        .table("notas_atividades")
        .select("*")
        .eq("turma", turma)
        .eq("unidade", "1º Bimestre")
        .execute()
    )

    mapas = {
        "AT3": {},
        "AT4": {},
        "AT5": {},
        "N2": {},
        "Rec": {}
    }

    for item in res_notas.data:

        aid = str(item["aluno_id"])

        mapas["AT3"][aid] = item.get("at3")
        mapas["AT4"][aid] = item.get("at4")
        mapas["AT5"][aid] = item.get("at5")
        mapas["N2"][aid] = item.get("prova")
        mapas["Rec"][aid] = item.get("rec")

    # =====================================================
    # REC AUTOMÁTICA
    # =====================================================

    mapa_rec_auto = buscar_recuperacao_automatica(
        supabase,
        ano_ref
    )

    # =====================================================
    # MONTAGEM
    # =====================================================

    df = df_alunos[
        ["aluno_id", "nome"]
    ].copy()

    df["AT1"] = (
        df["aluno_id"]
        .astype(str)
        .map(mapa_at1)
    )

    df["AT2"] = (
        df["aluno_id"]
        .astype(str)
        .map(mapa_at2)
    )

    for coluna in ["AT3", "AT4", "AT5", "N2"]:

        df[coluna] = (
            df["aluno_id"]
            .astype(str)
            .map(mapas[coluna])
        )

    def definir_rec(aid):

        aid = str(aid)

        nota_auto = mapa_rec_auto.get(aid)

        if nota_auto is not None:
            return nota_auto

        return mapas["Rec"].get(aid)

    df["Rec"] = (
        df["aluno_id"]
        .apply(definir_rec)
    )

    # =====================================================
    # CÁLCULOS
    # =====================================================

    df = calcular_n1(df)

    df = calcular_media(df)

    # =====================================================
    # ORDENA
    # =====================================================

    df = (
        df
        .sort_values("nome")
        .reset_index(drop=True)
    )

    return df


def salvar_banco(
    supabase,
    df,
    turma
):

    dados = []

    for _, linha in df.iterrows():

        limpar = (
            lambda x:
            float(x)
            if pd.notna(x)
            else None
        )

        dados.append({

            "aluno_id": linha["aluno_id"],

            "turma": turma,

            "unidade": "1º Bimestre",

            "at1": limpar(linha["AT1"]),
            "at2": limpar(linha["AT2"]),
            "at3": limpar(linha["AT3"]),
            "at4": limpar(linha["AT4"]),
            "at5": limpar(linha["AT5"]),

            "prova": limpar(linha["N2"]),

            "rec": limpar(linha["Rec"])
        })

    (
        supabase
        .table("notas_atividades")
        .upsert(
            dados,
            on_conflict="aluno_id, unidade"
        )
        .execute()
    )


# =========================================================
# INTERFACE
# =========================================================

def mostrar_tela_boletim(
    supabase,
    supabase_alunos
):

    st.title("📝 Registro de Notas")

    st.info(
        """
        AT1 e AT2 → Simulados

        AT3 até AT5 → Atividades

        N2 → Prova

        REC → Recuperação automática
        """
    )

    # =====================================================
    # TURMAS
    # =====================================================

    res = (
        supabase_alunos
        .table("alunos")
        .select("*")
        .execute()
    )

    df_todos = pd.DataFrame(res.data)

    turmas = sorted(
        df_todos["turma"]
        .dropna()
        .unique()
    )

    turma = st.selectbox(
        "Selecione a turma",
        turmas
    )

    if not turma:
        return

    state_key = f"df_{turma}"

    # =====================================================
    # LOAD
    # =====================================================

    if state_key not in st.session_state:

        with st.spinner("Carregando dados..."):

            st.session_state[state_key] = (
                carregar_dados_turma(
                    supabase,
                    supabase_alunos,
                    turma
                )
            )

    df = st.session_state[state_key]

    # =====================================================
    # ESTILO
    # =====================================================

    df_estilo = (
        df.style.map(
            estilo_notas,
            subset=COLUNAS_NOTAS
        )
    )

    # =====================================================
    # CONFIG COLUNAS
    # =====================================================

    config = {

        "aluno_id": None,

        "nome": st.column_config.TextColumn(
            "ESTUDANTE",
            disabled=True,
            width="large"
        ),

        "AT1": st.column_config.NumberColumn(
            "AT1",
            format="%.1f",
            disabled=True
        ),

        "AT2": st.column_config.NumberColumn(
            "AT2",
            format="%.1f",
            disabled=True
        ),

        "AT3": st.column_config.NumberColumn(
            "AT3",
            format="%.1f"
        ),

        "AT4": st.column_config.NumberColumn(
            "AT4",
            format="%.1f"
        ),

        "AT5": st.column_config.NumberColumn(
            "AT5",
            format="%.1f"
        ),

        "N2": st.column_config.NumberColumn(
            "N2",
            format="%.1f"
        ),

        "N1": st.column_config.NumberColumn(
            "Σ N1",
            format="%.1f",
            disabled=True
        ),

        "Média": st.column_config.NumberColumn(
            "MÉDIA",
            format="%.1f",
            disabled=True
        ),

        "Rec": st.column_config.NumberColumn(
            "REC",
            format="%.1f",
            disabled=True
        ),
    }

    # =====================================================
    # EDITOR
    # =====================================================

    editado = st.data_editor(
        df_estilo,
        hide_index=True,
        use_container_width=True,
        column_config=config,
        key=f"editor_{turma}",
        height=700
    )

    # =====================================================
    # RECÁLCULO
    # =====================================================

    editado = calcular_n1(editado)

    editado = calcular_media(editado)

    st.session_state[state_key] = editado

    # =====================================================
    # BOTÕES
    # =====================================================

    c1, c2, c3 = st.columns(3)

    # =====================================================
    # SALVAR
    # =====================================================

    with c1:

        if st.button(
            "💾 Salvar",
            type="primary",
            use_container_width=True
        ):

            try:

                salvar_banco(
                    supabase,
                    editado,
                    turma
                )

                st.success(
                    "Notas salvas com sucesso."
                )

            except Exception as erro:

                st.error(
                    f"Erro ao salvar: {erro}"
                )

    # =====================================================
    # SIEPE
    # =====================================================

    with c2:

        cfg = MAPA_IDS_SIEPE.get(turma)

        if cfg:

            if st.button(
                "🚀 Sincronizar SIEPE",
                use_container_width=True
            ):

                try:

                    client = SiepeClient()

                    usuario = st.secrets["SIEPE_USER"]
                    senha = st.secrets["SIEPE_PASS"]

                    with st.spinner("Sincronizando..."):

                        ok, _ = client.fazer_login(
                            usuario,
                            senha
                        )

                        if ok:

                            client.iniciar_robo_navegacao()

                            sucesso, msg = (
                                client
                                .sincronizar_dataframe_ao_siepe_final(
                                    editado,
                                    cfg
                                )
                            )

                            if sucesso:
                                st.success(msg)
                            else:
                                st.error(msg)

                        else:
                            st.error(
                                "Falha login SIEPE"
                            )

                except Exception as erro:

                    st.error(
                        f"Erro SIEPE: {erro}"
                    )

    # =====================================================
    # EXCEL
    # =====================================================

    with c3:

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="xlsxwriter"
        ) as writer:

            (
                editado
                .drop(columns=["aluno_id"])
                .to_excel(
                    writer,
                    index=False
                )
            )

        st.download_button(
            "📥 Excel",
            data=output.getvalue(),
            file_name=f"Notas_{turma}.xlsx",
            use_container_width=True
        )