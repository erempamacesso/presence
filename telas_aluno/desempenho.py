import streamlit as st
import pandas as pd
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    """
    Arredonda notas conforme regras SIEPE:
    - [0.0, 0.1] → 0.0
    - [0.2, 0.6] → 0.5
    - [0.7, 1.0] → 1.0
    """
    if pd.isna(nota) or nota is None:
        return 0.0
    
    try:
        nota = float(nota)
    except (ValueError, TypeError):
        return 0.0
    
    # Validação: nota não pode ser negativa
    if nota < 0:
        return 0.0
    
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else:
        return float(inteiro + 1)


def validar_nota(valor):
    """
    Converte valor para float, retornando 0.0 se inválido.
    Protege contra None, strings vazias e valores não numéricos.
    """
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return 0.0
    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0


def buscar_notas_simulados(db_provas, aluno_id, ano_num):
    """
    Busca as notas dos simulados (1º e 2º) de forma robusta.
    Retorna tupla (nota_simulado1, nota_simulado2)
    """
    at1, at2 = 0.0, 0.0
    
    try:
        # Busca 1º SIMULADO
        query_sim1 = f"%{ano_num}%SIMULADO%" if ano_num else "%SIMULADO%"
        res_p1 = db_provas.table("modelos_prova").select("id, valor_questao")\
            .ilike("titulo", query_sim1).execute()
        
        if res_p1.data and len(res_p1.data) > 0:
            # Se houver múltiplos resultados, pega o primeiro
            p1_id = res_p1.data[0]['id']
            v_q1 = validar_nota(res_p1.data[0].get('valor_questao', 1.0))
            if v_q1 == 0:
                v_q1 = 1.0
            
            res_r1 = db_provas.table("resultados_provas").select("acertos")\
                .eq("aluno_id", aluno_id).eq("prova_id", p1_id).execute()
            
            if res_r1.data and len(res_r1.data) > 0:
                acertos_1 = validar_nota(res_r1.data[0].get('acertos', 0))
                at1 = min(acertos_1 * v_q1, 4.0)
    
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar 1º Simulado: {str(e)}")
    
    try:
        # Busca 2º SIMULADO (mesmo padrão)
        query_sim2 = f"%{ano_num}%SIMULADO%" if ano_num else "%SIMULADO%"
        res_p2 = db_provas.table("modelos_prova").select("id, valor_questao")\
            .ilike("titulo", query_sim2).execute()
        
        # Se encontrou resultados, pega o último (2º simulado)
        if res_p2.data and len(res_p2.data) > 1:
            p2_id = res_p2.data[1]['id']
            v_q2 = validar_nota(res_p2.data[1].get('valor_questao', 1.0))
            if v_q2 == 0:
                v_q2 = 1.0
            
            res_r2 = db_provas.table("resultados_provas").select("acertos")\
                .eq("aluno_id", aluno_id).eq("prova_id", p2_id).execute()
            
            if res_r2.data and len(res_r2.data) > 0:
                acertos_2 = validar_nota(res_r2.data[0].get('acertos', 0))
                at2 = min(acertos_2 * v_q2, 4.0)
    
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar 2º Simulado: {str(e)}")
    
    return at1, at2


def buscar_notas_manuais(db_provas, aluno_id, unidade):
    """
    Busca as notas manuais (AT3, AT4, AT5 e Prova N2).
    Retorna tupla (at3, at4, at5, n2)
    """
    at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0
    
    try:
        res_notas = db_provas.table("notas_atividades")\
            .select("at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id)\
            .eq("unidade", str(unidade)).execute()
        
        if res_notas.data and len(res_notas.data) > 0:
            dados = res_notas.data[0]
            at3 = validar_nota(dados.get('at3'))
            at4 = validar_nota(dados.get('at4'))
            at5 = validar_nota(dados.get('at5'))
            n2 = validar_nota(dados.get('prova'))
        
    except Exception as e:
        st.error(f"❌ Erro ao acessar tabela de notas: {str(e)}")
    
    return at3, at4, at5, n2


def mostrar_tela_desempenho(db_alunos, db_provas):
    """
    Exibe a tela de desempenho acadêmico do aluno com tratamento robusto de erros.
    """
    st.subheader("📊 Meu Desempenho Acadêmico")
    
    # Validação da sessão
    if 'aluno' not in st.session_state:
        st.error("❌ Erro: Sessão do aluno não encontrada. Faça login novamente.")
        return
    
    aluno = st.session_state.aluno
    
    # Validação do ID do aluno
    if 'id' not in aluno or aluno['id'] is None:
        st.error("❌ Erro: ID do aluno inválido.")
        return
    
    aluno_id = str(aluno['id'])
    
    # Seleção do bimestre
    col_un, _ = st.columns([1, 2])
    with col_un:
        unidade_sel = st.selectbox(
            "Selecione o Bimestre:", 
            ["1", "2", "3", "4"], 
            index=0
        )
    
    # Extração do ano escolar
    turma_aluno = str(aluno.get('turma', '')).upper()
    ano_num = ""
    
    if "1º" in turma_aluno:
        ano_num = "1º"
    elif "2º" in turma_aluno:
        ano_num = "2º"
    elif "3º" in turma_aluno:
        ano_num = "3º"
    
    # Se não conseguir extrair o ano, avisa o usuário
    if not ano_num:
        st.warning(f"⚠️ Ano escolar não identificado para a turma: {turma_aluno}")
    
    # --- BUSCA DE TODAS AS NOTAS ---
    at1, at2 = buscar_notas_simulados(db_provas, aluno_id, ano_num)
    at3, at4, at5, n2 = buscar_notas_manuais(db_provas, aluno_id, unidade_sel)
    
    # --- CÁLCULOS ---
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    media_final = arredondar_siepe((soma_n1 + n2) / 2) if (soma_n1 + n2) > 0 else 0.0
    
    # --- EXIBIÇÃO DE MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Soma N1", f"{soma_n1:.1f}")
    with col2:
        st.metric("Nota N2", f"{n2:.1f}")
    with col3:
        st.metric("Média Final", f"{media_final:.1f}")
    
    st.write("---")
    
    # --- TABELA DETALHADA ---
    df_exibicao = pd.DataFrame({
        "Simulado 1 (AT1)": [f"{at1:.1f}"],
        "Simulado 2 (AT2)": [f"{at2:.1f}"],
        "Qualitativa (AT3)": [f"{at3:.1f}"],
        "Atividade (AT4)": [f"{at4:.1f}"],
        "Outros (AT5)": [f"{at5:.1f}"],
        "N1 Total": [f"{soma_n1:.1f}"],
        "N2 Prova": [f"{n2:.1f}"],
        "Média Final": [f"{media_final:.1f}"]
    })
    
    st.table(df_exibicao)
    
    # --- DIAGNÓSTICO ---
    st.write("---")
    
    if soma_n1_bruta == 0 and n2 == 0:
        st.warning(f"⚠️ Nenhuma nota registrada para o bimestre {unidade_sel}.")
        st.info("💡 Dica: Verifique com seu professor se as notas foram lançadas no sistema.")
    
    elif media_final >= 6.0:
        st.success(f"✅ Aprovado! Média: {media_final:.1f}")
    
    elif (soma_n1 + n2) > 0:
        st.warning(f"⚠️ Média abaixo de 6.0: {media_final:.1f}")
    
    # --- RESUMO DEBUG (Opcional - comentar se não necessário) ---
    with st.expander("📋 Detalhes Técnicos (Debug)"):
        st.write(f"**Aluno ID:** {aluno_id}")
        st.write(f"**Turma:** {turma_aluno}")
        st.write(f"**Ano Escolar Detectado:** {ano_num if ano_num else 'Não identificado'}")
        st.write(f"**Unidade Selecionada:** {unidade_sel}")
        st.write(f"**Soma N1 Bruta:** {soma_n1_bruta:.2f}")
        st.write(f"**Componentes N1:** AT1={at1:.1f}, AT2={at2:.1f}, AT3={at3:.1f}, AT4={at4:.1f}, AT5={at5:.1f}")
        st.write(f"**N2 (Prova):** {n2:.1f}")
        st.write(f"**Média Sem Arredondamento:** {(soma_n1_bruta + n2) / 2:.2f}")
        st.write(f"**Média Com Arredondamento:** {media_final:.1f}")