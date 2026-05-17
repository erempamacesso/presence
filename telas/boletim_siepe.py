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
# HELPERS DE RECUPERACAO
# =========================================================

def normalizar_id(valor):
    return str(valor).strip() if valor is not None else ""


def termos_unidade(unidade_label):
    numero = str(unidade_label)[:1]
    return [
        f"{numero}º BIMESTRE", f"{numero}Âº BIMESTRE",
        f"{numero}º TRIMESTRE", f"{numero}Âº TRIMESTRE",
        f"{numero} BIMESTRE", f"{numero} TRIMESTRE",
    ]


def titulo_tem_unidade(titulo, unidade_label):
    titulo_norm = str(titulo or "").upper()
    return any(termo in titulo_norm for termo in termos_unidade(unidade_label))


def buscar_resultados_por_provas(supabase, prova_ids, somente_acertos=False):
    ids_texto = [normalizar_id(pid) for pid in prova_ids if normalizar_id(pid)]
    if not ids_texto:
        return []

    query = supabase.table("resultados_provas").select("aluno_id, prova_id, acertou")
    query = query.in_("prova_id", ids_texto)
    if somente_acertos:
        query = query.eq("acertou", True)
    res = query.execute()
    return res.data or []


def calcular_recuperacoes(supabase, ano_ref, unidade_label=None):
    provas = (
        supabase.table("modelos_prova")
        .select("id, valor_questao, titulo")
        .eq("recuperacao", True)
        .ilike("titulo", f"%{ano_ref}%")
        .execute()
    )

    if not provas.data:
        return {}

    provas_rec = provas.data
    if unidade_label:
        provas_rec = [p for p in provas_rec if titulo_tem_unidade(p.get("titulo"), unidade_label)]

    if not provas_rec:
        return {}

    mapa_valores = {
        normalizar_id(p["id"]): float(p.get("valor_questao") or 0.5)
        for p in provas_rec
    }

    resultados = buscar_resultados_por_provas(supabase, list(mapa_valores.keys()), somente_acertos=True)
    if not resultados:
        return {}

    df = pd.DataFrame(resultados)
    df["aluno_id"] = df["aluno_id"].astype(str)
    df["prova_id"] = df["prova_id"].astype(str)
    df["valor"] = df["prova_id"].map(mapa_valores).fillna(0.0)

    notas = df.groupby("aluno_id")["valor"].sum().reset_index()
    notas["nota"] = notas["valor"].apply(arredondar_siepe)
    return dict(zip(notas["aluno_id"].astype(str), notas["nota"]))


def sincronizar_recuperacoes_turma(supabase, supabase_alunos, turma, unidade_label):
    ano_ref = "2º ano" if "2" in str(turma) else "3º ano"
    mapa_rec = calcular_recuperacoes(supabase, ano_ref, unidade_label)
    if not mapa_rec:
        return 0

    alunos = supabase_alunos.table("alunos").select("id, turma").eq("turma", turma).execute()
    ids_turma = {normalizar_id(a.get("id")) for a in (alunos.data or [])}

    dados = []
    for aluno_id, nota in mapa_rec.items():
        if aluno_id not in ids_turma:
            continue
        dados.append({
            "aluno_id": aluno_id,
            "turma": turma,
            "unidade": unidade_label,
            "rec": float(nota) if nota is not None else None,
        })

    if not dados:
        return 0

    supabase.table("notas_atividades").upsert(dados, on_conflict="aluno_id, unidade").execute()
    return len(dados)

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

def buscar_rec_auto(supabase, ano_ref, unidade_label=None):
    try:
        return calcular_recuperacoes(supabase, ano_ref, unidade_label)
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

    mapa_rec = buscar_rec_auto(supabase, ano_ref, unidade_label)

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
    N1 = soma de AT1 + AT2 + AT3 + AT4 + AT5
    N2 = nota da prova importada pelo CSV
    Média = média aritmética entre N1 e N2
    REC = nota da recuperação
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
    if st.button("🔄 Sincronizar recuperações no banco", use_container_width=True):
        try:
            qtd = sincronizar_recuperacoes_turma(supabase, supabase_alunos, turma, unidade_sel)
            st.session_state.pop(state_key, None)
            if qtd:
                st.success(f"Recuperações sincronizadas para {qtd} aluno(s).")
            else:
                st.info("Nenhuma recuperação encontrada para sincronizar nesta turma/bimestre.")
            st.rerun()
        except Exception as erro:
            st.error(f"Erro ao sincronizar recuperações: {erro}")

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