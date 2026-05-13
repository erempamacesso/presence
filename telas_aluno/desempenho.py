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
    
    # Verificação de segurança da sessão
    if 'aluno' not in st.session_state:
        st.error("Erro: Sessão do aluno não encontrada.")
        return

    aluno = st.session_state.aluno
    aluno_id = str(aluno['id']) # O aluno_id na tabela resultados_provas é texto
    
    # --- SELETOR DE UNIDADE ---
    col_un, _ = st.columns([1, 2])
    with col_un:
        unidade_sel = st.selectbox("Selecione o Bimestre:", ["1", "2", "3", "4"], index=0)

    # Melhoria na lógica do ano de referência para evitar erros de busca
    turma_aluno = str(aluno.get('turma', '')).upper()
    if "1º" in turma_aluno: ano_num = "1º"
    elif "2º" in turma_aluno: ano_num = "2º"
    elif "3º" in turma_aluno: ano_num = "3º"
    else: ano_num = ""

    # --- 1. BUSCA NOTAS DOS SIMULADOS (AT1 e AT2) ---
    def buscar_nota_simulado(termo_simulado):
        try:
            # Removida a palavra fixa "ano" para tornar a busca mais flexível
            # Procura por "1º" E "1º SIMULADO", por exemplo.
            query_titulo = f"%{ano_num}%{termo_simulado}%"
            
            res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                .ilike("titulo", query_titulo).execute()
            
            if not res_p.data:
                # Se não encontrar, tenta uma busca ainda mais genérica apenas pelo termo
                res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                    .ilike("titulo", f"%{termo_simulado}%").execute()

            if res_p.data:
                p_id = res_p.data[0]['id']
                v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                
                res_r = db_provas.table("resultados_provas").select("acertos")\
                    .eq("aluno_id", aluno_id).eq("prova_id", p_id).execute()
                
                if res_r.data:
                    return min(float(res_r.data[0]['acertos']) * v_q, 4.0)
            return 0.0
        except Exception as e:
            st.warning(f"Aviso técnico: Erro ao buscar {termo_simulado}: {e}")
            return 0.0

    at1 = buscar_nota_simulado("1º SIMULADO")
    at2 = buscar_nota_simulado("2º SIMULADO")

    # --- 2. BUSCA NOTAS MANUAIS ---
    at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
    try:
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
        else:
            # Se não houver dados, mostramos um aviso informativo
            st.info(f"Notas da {unidade_sel}ª unidade ainda não lançadas para este aluno.")
            
    except Exception as e:
        st.error(f"Erro ao aceder à tabela de notas_atividades: {e}")

    # --- 3. CÁLCULOS E EXIBIÇÃO ---
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    media_final = arredondar_siepe((soma_n1 + n2) / 2)

    # Layout de cards para ficar mais visível que a tabela
    c1, c2, c3 = st.columns(3)
    c1.metric("Soma N1", f"{soma_n1:.1f}")
    c2.metric("Nota N2", f"{n2:.1f}")
    c3.metric("Média Final", f"{media_final:.1f}")

    st.write("---")
    st.markdown("**Detalhamento das Atividades:**")
    df_exibicao = pd.DataFrame({
        "Simulado 1 (AT1)": [at1], 
        "Simulado 2 (AT2)": [at2], 
        "Qualitativa (AT3)": [at3], 
        "Atividade (AT4)": [at4], 
        "Outros (AT5)": [at5]
    })
    st.table(df_exibicao.style.format("{:.1f}"))

    if media_final >= 6.0:
        st.success(f"Parabéns! Estás aprovado nesta unidade.")
    elif (soma_n1 + n2) > 0:
        st.warning(f"Atenção: A tua média está abaixo de 6.0.")