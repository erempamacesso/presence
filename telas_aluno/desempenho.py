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


def buscar_todas_notas(db_provas, aluno_id, unidade):
    """
    Busca TODAS as notas (AT1, AT2, AT3, AT4, AT5, Prova N2) da tabela notas_atividades.
    
    Retorna tupla: (at1, at2, at3, at4, at5, n2)
    
    IMPORTANTE: Todas as notas vêm de uma ÚNICA fonte: notas_atividades
    """
    at1, at2, at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    try:
        # Converte unidade para o formato correto: "1" → "1º Bimestre"
        unidade_formatada = f"{unidade}º Bimestre"
        
        # Busca TODAS as notas de uma vez na tabela notas_atividades
        res_notas = db_provas.table("notas_atividades")\
            .select("at1, at2, at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id)\
            .eq("unidade", unidade_formatada).execute()
        
        if res_notas.data and len(res_notas.data) > 0:
            dados = res_notas.data[0]
            
            # Extrai e valida cada nota
            at1 = validar_nota(dados.get('at1'))
            at2 = validar_nota(dados.get('at2'))
            at3 = validar_nota(dados.get('at3'))
            at4 = validar_nota(dados.get('at4'))
            at5 = validar_nota(dados.get('at5'))
            n2 = validar_nota(dados.get('prova'))
            
            st.write(f"✅ Notas carregadas com sucesso do bimestre {unidade}")
        else:
            st.info(f"ℹ️ Nenhuma nota registrada para o bimestre {unidade}.")
            
    except Exception as e:
        st.error(f"❌ Erro ao acessar tabela de notas: {str(e)}")
    
    return at1, at2, at3, at4, at5, n2


def buscar_notas_recuperacao(db_provas, aluno_id, unidade):
    """
    Busca a nota de recuperação (REC) se existir.
    """
    rec = 0.0
    
    try:
        # Converte unidade para o formato correto: "1" → "1º Bimestre"
        unidade_formatada = f"{unidade}º Bimestre"
        
        res_rec = db_provas.table("notas_atividades")\
            .select("rec")\
            .eq("aluno_id", aluno_id)\
            .eq("unidade", unidade_formatada).execute()
        
        if res_rec.data and len(res_rec.data) > 0:
            rec = validar_nota(res_rec.data[0].get('rec'))
            
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar nota de recuperação: {str(e)}")
    
    return rec


def mostrar_tela_desempenho(db_alunos, db_provas):
    """
    Exibe a tela de desempenho acadêmico do aluno.
    
    FLUXO CORRETO:
    1. Busca TODAS as notas de notas_atividades (AT1, AT2, AT3, AT4, AT5, Prova)
    2. Calcula somas e médias
    3. Exibe com arredondamento SIEPE
    """
    st.subheader("📊 Meu Desempenho Acadêmico")
    
    # === VALIDAÇÃO DA SESSÃO ===
    if 'aluno' not in st.session_state:
        st.error("❌ Erro: Sessão do aluno não encontrada. Faça login novamente.")
        return
    
    aluno = st.session_state.aluno
    
    if 'id' not in aluno or aluno['id'] is None:
        st.error("❌ Erro: ID do aluno inválido.")
        return
    
    aluno_id = str(aluno['id'])
    aluno_nome = aluno.get('nome', 'Aluno')
    
    # === SELEÇÃO DO BIMESTRE ===
    col_un, _ = st.columns([1, 2])
    with col_un:
        unidade_sel = st.selectbox(
            "Selecione o Bimestre:", 
            ["1", "2", "3", "4"], 
            index=0,
            key="unidade_selector"
        )
    
    st.write(f"**Aluno:** {aluno_nome} (ID: {aluno_id})")
    st.write(f"**Bimestre Selecionado:** {unidade_sel}º")
    st.write("---")
    
    # === BUSCA DE NOTAS ===
    at1, at2, at3, at4, at5, n2 = buscar_todas_notas(db_provas, aluno_id, unidade_sel)
    rec = buscar_notas_recuperacao(db_provas, aluno_id, unidade_sel)
    
    # === CÁLCULOS ===
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    
    # Cálculo da média: se houver recuperação, usa a maior entre N2 e REC
    n2_final = max(n2, rec) if rec > 0 else n2
    
    if (soma_n1 + n2_final) > 0:
        media_final = arredondar_siepe((soma_n1 + n2_final) / 2)
    else:
        media_final = 0.0
    
    # === EXIBIÇÃO DE MÉTRICAS ===
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Soma N1",
            f"{soma_n1:.1f}",
            help=f"AT1({at1:.1f}) + AT2({at2:.1f}) + AT3({at3:.1f}) + AT4({at4:.1f}) + AT5({at5:.1f})"
        )
    
    with col2:
        if rec > 0:
            st.metric(
                "Nota N2",
                f"{n2_final:.1f}",
                help=f"N2: {n2:.1f} | REC: {rec:.1f} (usando maior)"
            )
        else:
            st.metric(
                "Nota N2",
                f"{n2_final:.1f}",
                help=f"Prova (sem recuperação)"
            )
    
    with col3:
        if media_final >= 6.0:
            st.metric(
                "Média Final",
                f"{media_final:.1f}",
                delta="✅ Aprovado"
            )
        elif (soma_n1 + n2_final) > 0:
            st.metric(
                "Média Final",
                f"{media_final:.1f}",
                delta="⚠️ Abaixo de 6.0"
            )
        else:
            st.metric("Média Final", "0.0")
    
    st.write("---")
    
    # === TABELA DETALHADA ===
    df_exibicao = pd.DataFrame({
        "Simulado 1 (AT1)": [f"{at1:.1f}"],
        "Simulado 2 (AT2)": [f"{at2:.1f}"],
        "Qualitativa (AT3)": [f"{at3:.1f}"],
        "Atividade (AT4)": [f"{at4:.1f}"],
        "Outros (AT5)": [f"{at5:.1f}"],
        "N1 Total": [f"{soma_n1:.1f}"],
        "N2 Prova": [f"{n2:.1f}"],
        "REC": [f"{rec:.1f}" if rec > 0 else "-"],
        "Média Final": [f"{media_final:.1f}"]
    })
    
    st.table(df_exibicao)
    
    st.write("---")
    
    # === MENSAGENS E DIAGNÓSTICO ===
    if soma_n1_bruta == 0 and n2 == 0:
        st.warning(
            f"⚠️ **Nenhuma nota registrada para o bimestre {unidade_sel}**\n\n"
            f"💡 Verifique com seu professor se as notas foram lançadas no sistema."
        )
    
    elif media_final >= 6.0:
        st.success(f"✅ **Aprovado no bimestre {unidade_sel}!**\n\nMédia: {media_final:.1f}")
    
    elif (soma_n1 + n2_final) > 0:
        falta = 6.0 - media_final
        st.warning(
            f"⚠️ **Média abaixo de 6.0**\n\n"
            f"Sua média: {media_final:.1f}\n"
            f"Faltam {falta:.1f} pontos para aprovação"
        )
    
    # === SEÇÃO DE DEBUG ===
    with st.expander("📋 Detalhes Técnicos (Debug)"):
        st.write("### Informações do Aluno")
        st.write(f"- **ID:** {aluno_id}")
        st.write(f"- **Nome:** {aluno_nome}")
        st.write(f"- **Bimestre:** {unidade_sel}")
        
        st.write("### Notas Carregadas")
        st.write(f"- **AT1 (Simulado 1):** {at1:.2f}")
        st.write(f"- **AT2 (Simulado 2):** {at2:.2f}")
        st.write(f"- **AT3 (Qualitativa):** {at3:.2f}")
        st.write(f"- **AT4 (Atividade):** {at4:.2f}")
        st.write(f"- **AT5 (Outros):** {at5:.2f}")
        st.write(f"- **Soma N1 (bruta):** {soma_n1_bruta:.2f}")
        st.write(f"- **Soma N1 (arredondada):** {soma_n1:.2f}")
        
        st.write("### Notas de Avaliação")
        st.write(f"- **N2 (Prova):** {n2:.2f}")
        st.write(f"- **REC (Recuperação):** {rec:.2f}")
        st.write(f"- **N2 Final (maior entre N2 e REC):** {n2_final:.2f}")
        
        st.write("### Cálculo da Média")
        st.write(f"- **(N1 + N2) / 2 = ({soma_n1:.2f} + {n2_final:.2f}) / 2 = {(soma_n1 + n2_final) / 2:.2f}**")
        st.write(f"- **Após arredondamento SIEPE:** {media_final:.2f}")