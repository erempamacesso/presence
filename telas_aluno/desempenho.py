import streamlit as st
import pandas as pd
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota) or nota is None:
        return 0.0
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else:
        return float(inteiro + 1)

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Meu Desempenho Acadêmico")
    
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])
    
    # --- NOVO: SELETOR DE UNIDADE (Para espantar o fantasma) ---
    col_un, _ = st.columns([1, 2])
    with col_un:
        unidade_sel = st.selectbox("Selecione o Bimestre:", ["1", "2", "3", "4"], index=0)

    turma_aluno = str(aluno.get('turma', '')).lower()
    ano_ref = "2º ano" if "2º" in turma_aluno else ("3º ano" if "3º" in turma_aluno else "1º ano")
    
    # --- 1. BUSCA NOTAS DOS SIMULADOS (AT1 e AT2) ---
    def buscar_nota_simulado(termo_simulado):
        try:
            # Aqui buscamos o modelo que contenha o ano e a unidade (ex: 2º ano 1º SIMULADO 1)
            # Se seus simulados não mudam por unidade, mantenha como estava
            res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
            
            if res_p.data:
                p_id = res_p.data[0]['id']
                v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                res_r = db_provas.table("resultados_provas").select("acertos")\
                    .eq("aluno_id", aluno_id).eq("prova_id", p_id).execute()
                
                if res_r.data:
                    return min(float(res_r.data[0]['acertos']) * v_q, 4.0)
            return 0.0
        except: return 0.0

    at1 = buscar_nota_simulado("1º SIMULADO")
    at2 = buscar_nota_simulado("2º SIMULADO")

    # --- 2. BUSCA NOTAS MANUAIS (COM FILTRO DE UNIDADE) ---
    at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
    try:
        # AQUI ESTÁ O PULO DO GATO: Adicionamos .eq("unidade", unidade_sel)
        res_notas = db_provas.table("notas_atividades")\
            .select("at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id)\
            .eq("unidade", unidade_sel).execute()
        
        if res_notas.data:
            dados = res_notas.data[0]
            at3 = float(dados.get('at3', 0.0) or 0.0)
            at4 = float(dados.get('at4', 0.0) or 0.0)
            at5 = float(dados.get('at5', 0.0) or 0.0)
            n2  = float(dados.get('prova', 0.0) or 0.0)
    except: pass

    # --- 3. CÁLCULOS E EXIBIÇÃO ---
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    media_final = arredondar_siepe((soma_n1 + n2) / 2)

    df_exibicao = pd.DataFrame({
        "AT1": [at1], "AT2": [at2], "AT3": [at3], "AT4": [at4], "AT5": [at5],
        "Σ N1": [soma_n1], "N2": [n2], "Média": [media_final]
    })

    st.table(df_exibicao.style.format("{:.1f}"))

    if media_final >= 6.0:
        st.success(f"Aprovado na unidade! Média: {media_final:.1f}")
    else:
        st.error(f"Abaixo da média. Média: {media_final:.1f}")