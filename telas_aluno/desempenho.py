import streamlit as st
import pandas as pd

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Meu Desempenho Acadêmico")
    
    # Recupera os dados do aluno logado
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])
    
    # Define o ano de referência para buscar o simulado (1º, 2º ou 3º ano)
    turma_aluno = str(aluno.get('turma', '')).lower()
    ano_ref = "2º ano" if "2º" in turma_aluno else ("3º ano" if "3º" in turma_aluno else "1º ano")
    
    # =========================================================================
    # 1. BUSCA NOTAS AUTOMÁTICAS (AT1 e AT2 - SIMULADOS)
    # =========================================================================
    def buscar_nota_simulado(termo_simulado):
        try:
            # Busca o modelo da prova para saber o valor de cada questão
            res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
                .ilike("titulo", f"%{ano_ref}%{termo_simulado}%").execute()
            
            if res_p.data:
                p_id = res_p.data[0]['id']
                v_q = float(res_p.data[0].get('valor_questao') or 1.0)
                
                # Busca quantos acertos o aluno teve nessa prova
                res_r = db_provas.table("resultados_provas").select("acertos")\
                    .eq("aluno_id", aluno_id).eq("prova_id", p_id).execute()
                
                if res_r.data:
                    nota = float(res_r.data[0]['acertos']) * v_q
                    return min(nota, 4.0) # Trava em 4.0 como no boletim
            return 0.0
        except:
            return 0.0

    at1 = buscar_nota_simulado("1º SIMULADO")
    at2 = buscar_nota_simulado("2º SIMULADO")

    # =========================================================================
    # 2. BUSCA NOTAS MANUAIS (AT3, AT4, AT5 e N2) NA TABELA notas_atividades
    # =========================================================================
    at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
    
    try:
        # Busca o registro do aluno na tabela de notas
        # Obs: Se você usar unidades (1º Bim, 2º Bim), adicione .eq("unidade", "1")
        res_notas = db_provas.table("notas_atividades")\
            .select("at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id).execute()
        
        if res_notas.data:
            dados = res_notas.data[0]
            at3 = float(dados.get('at3', 0.0) or 0.0)
            at4 = float(dados.get('at4', 0.0) or 0.0)
            at5 = float(dados.get('at5', 0.0) or 0.0)
            n2  = float(dados.get('prova', 0.0) or 0.0)
    except Exception as e:
        st.warning("Aguardando lançamento de notas complementares pelo professor.")

    # =========================================================================
    # 3. CÁLCULOS FINAIS E EXIBIÇÃO
    # =========================================================================
    soma_n1 = at1 + at2 + at3 + at4 + at5
    media_final = (soma_n1 + n2) / 2

    # Criando o DataFrame para exibição (estilo tabela)
    df_exibicao = pd.DataFrame({
        "AT1 (Simulado 1)": [at1],
        "AT2 (Simulado 2)": [at2],
        "AT3 (Atividade)": [at3],
        "AT4 (Atividade)": [at4],
        "AT5 (Atividade)": [at5],
        "Soma N1": [soma_n1],
        "N2 (Prova Final)": [n2],
        "Média Final": [media_final]
    })

    # Formata para mostrar sempre uma casa decimal (ex: 7.0)
    st.dataframe(
        df_exibicao.style.format("{:.1f}"),
        use_container_width=True,
        hide_index=True
    )

    # Mensagem de incentivo baseada na média
    if media_final >= 6.0:
        st.success(f"Parabéns! Sua média atual é **{media_final:.1f}**. Continue assim!")
    elif media_final > 0:
        st.warning(f"Sua média é **{media_final:.1f}**. Fique atento às próximas atividades!")