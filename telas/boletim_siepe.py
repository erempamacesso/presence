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
    return float(inteiro + 1)

# =========================================================
# ESTILOS
# =========================================================

def estilo_atividades(valor):
    if pd.isna(valor):
        return "color:#9CA3AF;"
    return """
        background-color:#EFF6FF;
        color:#1D4ED8;
        font-weight:bold;
    """

def estilo_medias(valor):
    if pd.isna(valor):
        return "color:#9CA3AF;"
    try:
        valor = float(valor)
        if valor < 6:
            return """
                background-color:#FEF2F2;
                color:#DC2626;
                font-weight:bold;
            """
        return """
            background-color:#ECFDF5;
            color:#047857;
            font-weight:bold;
        """
    except:
        return "color:#9CA3AF;"

# =========================================================
# BUSCAS AUTOMÁTICAS (SIMULADOS E REC)
# =========================================================

def buscar_simulado(supabase, ano_ref, termo, limite=4.0):
    try:
        prova = (
            supabase.table("modelos_prova")
            .select("id, valor_questao")
            .ilike("titulo", f"%{ano_ref}%{termo}%")
            .execute()
        )
        if not prova.data:
            return {}

        prova = prova.data[0]
        resultados = (
            supabase.table("resultados_provas")
            .select("aluno_id, acertou")
            .eq("prova_id", prova["id"])
            .execute()
        )
        if not resultados.data:
            return {}

        df = pd.DataFrame(resultados.data)
        df = (
            df[df["acertou"] == True]
            .groupby("aluno_id")
            .size()
            .reset_index(name="acertos")
        )
        valor_q = float(prova.get("valor_questao") or 1)
        df["nota"] = (
            (df["acertos"] * valor_q)
            .clip(upper=limite)
            .apply(arredondar_siepe)
        )
        return dict(zip(df["aluno_id"].astype(str), df["nota"]))
    except Exception as erro:
        st.warning(f"Erro simulados: {erro}")
        return {}

def buscar_rec_auto(supabase, ano_ref):
    try:
        # Busca na tabela correta 'modelos_prova' se é recuperação
        prova = (
            supabase.table("modelos_prova")
            .select("id, valor_questao")
            .eq("recuperacao", True)
            .ilike("titulo", f"%{ano_ref}%")
            .execute()
        )
        if not prova.data:
            return {}

        prova = prova.data[0]
        resultados = (
            supabase.table("resultados_provas")
            .select("aluno_id, acertou")
            .eq("prova_id", prova["id"])
            .execute()
        )
        if not resultados.data:
            return {}

        df = pd.DataFrame(resultados.data)
        df = (
            df[df["acertou"] == True]
            .groupby("aluno_id")
            .size()
            .reset_index(name="acertos")
        )
        valor_q = float(prova.get("valor_questao") or 0.5)
        df["nota"] = (df["acertos"] * valor_q).apply(arredondar_siepe)
        return dict(zip(df["aluno_id"].astype(str), df["nota"]))
    except Exception as erro:
        st.warning(f"Erro REC: {erro}")
        return {}

# =========================================================
# CÁLCULOS
# =========================================================

def calcular_n1(df):
    df["N1"] = (
        df[ATIVIDADES]
        .fillna(0)
        .sum(axis=1)
        .apply(arredondar_siepe)
    )
    return df

def calcular_media(df):
    df["Média"] = (
        (df["N1"].fillna(0) + df["N2"].fillna(0)) / 2
    ).apply(arredondar_siepe)
    return df

# =========================================================
# LOAD DADOS
# =========================================================

def carregar_dados_turma(supabase, supabase_alunos, turma, unidade_label):
    alunos = (
        supabase_alunos.table("alunos")
        .select("*")
        .execute()
    )
    df_alunos = pd.DataFrame(alunos.data)
    df_alunos = df_alunos[df_alunos["turma"] == turma].copy()
    df_alunos.rename(columns={"id": "aluno_id"}, inplace=True)

    ano_ref = "2º ano" if "2º" in turma else "3º ano"

    mapa_at1 = buscar_simulado(supabase, ano_ref, "1º Simulado")
    mapa_at2 = buscar_simulado(supabase, ano_ref, "2º Simulado")

    notas = (
        supabase.table("notas_atividades")
        .select("*")
        .eq("turma", turma)
        .eq("unidade", unidade_label)
        .execute()
    )

    mapas = {
        "AT3": {},
        "AT4": {},
        "AT5": {},
        "N2": {},
        "Rec": {}
    }

    for item in notas.data:
        aid = str(item["aluno_id"])
        mapas["AT3"][aid] = item.get("at3")
        mapas["AT4"][aid] = item.get("at4")
        mapas["AT5"][aid] = item.get("at5")
        mapas["N2"][aid] = item.get("prova")
        mapas["Rec"][aid] = item.get("rec")

    mapa_rec = buscar_rec_auto(supabase, ano_ref)

    df = df_alunos[["aluno_id", "nome"]].copy()
    df["AT1"] = df["aluno_id"].astype(str).map(mapa_at1)
    df["AT2"] = df["aluno_id"].astype(str).map(mapa_at2)

    for col in ["AT3", "AT4", "AT5", "N2"]:
        df[col] = df["aluno_id"].astype(str).map(mapas[col])

    df["Rec"] = df["aluno_id"].apply(
        lambda aid: mapa_rec.get(str(aid), mapas["Rec"].get(str(aid)))
    )

    df = calcular_n1(df)
    df = calcular_media(df)

    return df.sort_values("nome").reset_index(drop=True)

# =========================================================
# SAVE
# =========================================================

def salvar_banco(supabase, df, turma, unidade_label):
    limpar = lambda x: float(x) if pd.notna(x) else None

    dados = [{
        "aluno_id": r["aluno_id"],
        "turma": turma,
        "unidade": unidade_label,
        "at1": limpar(r["AT1"]),
        "at2": limpar(r["AT2"]),
        "at3": limpar(r["AT3"]),
        "at4": limpar(r["AT4"]),
        "at5": limpar(r["AT5"]),
        "prova": limpar(r["N2"]),
        "rec": limpar(r["Rec"])
    } for _, r in df.iterrows()]

    supabase.table("notas_atividades").upsert(dados, on_conflict="aluno_id, unidade").execute()

# =========================================================
# INTERFACE
# =========================================================

def mostrar_tela_boletim(supabase, supabase_alunos):
    st.title("📝 Registro de Notas")

    st.info("""
    AT1 e AT2 → Simulados  
    AT3 até AT5 → Atividades  
    N2 → Prova  
    REC → Recuperação automática
    """)

    alunos = (
        supabase_alunos.table("alunos")
        .select("*")
        .execute()
    )
    df_todos = pd.DataFrame(alunos.data)
    turmas = sorted(df_todos["turma"].dropna().unique())

    c1, c2 = st.columns(2)
    with c1:
        turma = st.selectbox("Selecione a turma", turmas)
    with c2:
        # Alinhando os labels textuais com o que está gravado na sua tabela 'notas_atividades'
        mapa_unidades = {
            "1º Bimestre": "1",
            "2º Bimestre": "2",
            "3º Bimestre": "3",
            "4º Bimestre": "4"
        }
        unidade_sel = st.selectbox("Selecione o Bimestre", list(mapa_unidades.keys()))

    if not turma:
        return

    # A chave do estado agora muda caso você altere o bimestre também
    state_key = f"df_{turma}_{unidade_sel}"

    if state_key not in st.session_state:
        with st.spinner("Carregando dados..."):
            st.session_state[state_key] = carregar_dados_turma(
                supabase,
                supabase_alunos,
                turma,
                unidade_sel
            )

    df = st.session_state[state_key]

    # Aplicando os estilos visuais nas colunas
    df_estilo = df.style.map(
        estilo_atividades,
        subset=ATIVIDADES
    ).map(
        estilo_medias,
        subset=MEDIAS
    )

    config = {
        "aluno_id": None,
        "nome": st.column_config.TextColumn("ESTUDANTE", disabled=True, width="large"),
        **{col: st.column_config.NumberColumn(col, format="%.1f") for col in ["AT3", "AT4", "AT5", "N2"]},
        "AT1": st.column_config.NumberColumn("AT1", format="%.1f", disabled=True),
        "AT2": st.column_config.NumberColumn("AT2", format="%.1f", disabled=True),
        "N1": st.column_config.NumberColumn("Σ N1", format="%.1f", disabled=True),
        "Média": st.column_config.NumberColumn("MÉDIA", format="%.1f", disabled=True),
        "Rec": st.column_config.NumberColumn("REC", format="%.1f", disabled=True),
    }

    editado = st.data_editor(
        df_estilo,
        hide_index=True,
        use_container_width=True,
        column_config=config,
        key=f"editor_{turma}_{unidade_sel}",
        height=700
    )

    editado = calcular_n1(editado)
    editado = calcular_media(editado)
    st.session_state[state_key] = editado

    st.divider()
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("💾 Salvar", type="primary", use_container_width=True):
            try:
                salvar_banco(supabase, editado, turma, unidade_sel)
                st.success("Notas salvas com sucesso.")
                st.rerun()
            except Exception as erro:
                st.error(f"Erro ao salvar: {erro}")

    with c2:
        cfg = MAPA_IDS_SIEPE.get(turma)
        if cfg and st.button("🚀 Sincronizar SIEPE", use_container_width=True):
            try:
                client = SiepeClient()
                usuario = st.secrets["SIEPE_USER"]
                senha = st.secrets["SIEPE_PASS"]

                with st.spinner("Sincronizando..."):
                    ok, _ = client.fazer_login(usuario, senha)
                    if ok:
                        client.iniciar_robo_navegacao()
                        # Passa o número puro ("1", "2"...) exigido pela API do SIEPE
                        cfg["bimestre"] = mapa_unidades[unidade_sel]
                        sucesso, msg = client.sincronizar_dataframe_ao_siepe_final(editado, cfg)
                        st.success(msg) if sucesso else st.error(msg)
                    else:
                        st.error("Falha login SIEPE")
            except Exception as erro:
                st.error(f"Erro SIEPE: {erro}")

    with c3:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            editado.drop(columns=["aluno_id"]).to_excel(writer, index=False)

        st.download_button(
            "📥 Excel",
            data=output.getvalue(),
            file_name=f"Notas_{turma}_{unidade_sel}.xlsx",
            use_container_width=True
        )