import streamlit as st
import pandas as pd
import math # <-- IMPORTANTE PARA O ARREDONDAMENTO

# ==========================================
# 1. FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE
# ==========================================
def arredondar_siepe(nota):
    """
    Regra de arredondamento oficial SIEPE/PE:
    ,0 e ,1 -> ,0
    ,2 a ,6 -> ,5
    ,7 a ,9 -> +1,0 (próximo número inteiro)
    """
    if pd.isna(nota) or nota is None:
        return 0.0
        
    nota = float(nota)
    inteiro = math.floor(nota)
    # Pega o primeiro dígito decimal
    decimal = round((nota - inteiro) * 10)
    
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else: # 7, 8, 9, 10
        return float(inteiro + 1)

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Meu Desempenho Acadêmico (Padrão SIEPE)")
    
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])
    
    turma_aluno = str(aluno.get('turma', '')).lower()
    ano_ref = "2º ano" if "2º" in turma_aluno else ("3º ano" if "3º" in turma_aluno else "1º ano")
    
    # --- 1. BUSCA NOTAS AUTOMÁTICAS (SIMULADOS) ---
    def buscar_nota_simulado(termo_simulado):
        try:
            res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
            
            if res_p.data:
                p_id = res_p.data[0]['id']
                v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                res_r = db_provas.table("resultados_provas").select("acertos")\
                    .eq("aluno_id", aluno_id).eq("prova_id", p_id).execute()
                
                if res_r.data:
                    nota_bruta = float(res_r.data[0]['acertos']) * v_q
                    return min(nota_bruta, 4.0) 
            return 0.0
        except: return 0.0

    at1 = buscar_nota_simulado("1º SIMULADO")
    at2 = buscar_nota_simulado("2º SIMULADO")

    # --- 2. BUSCA NOTAS MANUAIS NA TABELA notas_atividades ---
    at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
    try:
        res_notas = db_provas.table("notas_atividades")\
            .select("at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id).execute()
        
        if res_notas.data:
            dados = res_notas.data[0]
            at3 = float(dados.get('at3', 0.0) or 0.0)
            at4 = float(dados.get('at4', 0.0) or 0.0)
            at5 = float(dados.get('at5', 0.0) or 0.0)
            n2  = float(dados.get('prova', 0.0) or 0.0)
    except: pass

    # =========================================================================
    # 3. CÁLCULOS COM ARREDONDAMENTO SIEPE
    # =========================================================================
    # A Soma N1 deve ser arredondada antes de calcular a média final
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    
    # A Média Final também passa pelo crivo do arredondamento
    media_final_bruta = (soma_n1 + n2) / 2
    media_final = arredondar_siepe(media_final_bruta)

    # DataFrame para exibição
    df_exibicao = pd.DataFrame({
        "AT1 🔒": [at1],
        "AT2 🔒": [at2],
        "AT3": [at3],
        "AT4": [at4],
        "AT5": [at5],
        "Σ N1 (Arred.)": [soma_n1],
        "N2 (Prova)": [n2],
        "Média Final": [media_final]
    })

    # Estilização da tabela
    st.dataframe(
        df_exibicao.style.format("{:.1f}"),
        use_container_width=True,
        hide_index=True
    )

    # Alertas Visuais
    if media_final >= 6.0:
        st.success(f"🔥 **Excelente!** Sua média final arredondada é **{media_final:.1f}**.")
    elif media_final >= 4.0:
        st.warning(f"⚠️ **Atenção:** Sua média é **{media_final:.1f}**. Você ainda tem chances, foque nos estudos!")
    else:
        st.error(f"🚨 **Alerta:** Sua média atual é **{media_final:.1f}**. Procure o professor para orientações.")

    with st.expander("❓ Como minha nota é calculada?"):
        st.write("""
        1. **AT1 e AT2**: Notas automáticas dos seus simulados online (Máximo 4.0).
        2. **AT3, AT4 e AT5**: Atividades diversas lançadas pelo professor.
        3. **Σ N1**: É a soma de todas as ATs, arredondada pelo padrão SIEPE.
        4. **N2**: É a sua nota da Prova Bimestral.
        5. **Média Final**: (Σ N1 + N2) dividido por 2, com arredondamento final.
        """)