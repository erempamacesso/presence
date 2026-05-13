import streamlit as st
import pandas as pd
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    if pd.isna(nota) or nota is None:
        return 0.0
    try:
        nota = float(nota)
    except (ValueError, TypeError):
        return 0.0
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
    if valor is None or (isinstance(valor, str) and valor.strip() == ""):
        return 0.0
    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0

def buscar_todas_notas(db_provas, aluno_id, unidade):
    at1, at2, at3, at4, at5, n2 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        unidade_formatada = f"{unidade}º Bimestre"
        res_notas = db_provas.table("notas_atividades")\
            .select("at1, at2, at3, at4, at5, prova")\
            .eq("aluno_id", aluno_id)\
            .eq("unidade", unidade_formatada).execute()
        
        if res_notas.data and len(res_notas.data) > 0:
            dados = res_notas.data[0]
            at1 = validar_nota(dados.get('at1'))
            at2 = validar_nota(dados.get('at2'))
            at3 = validar_nota(dados.get('at3'))
            at4 = validar_nota(dados.get('at4'))
            at5 = validar_nota(dados.get('at5'))
            n2 = validar_nota(dados.get('prova'))
    except:
        pass
    return at1, at2, at3, at4, at5, n2

def buscar_notas_recuperacao(db_provas, aluno_id, unidade):
    rec = 0.0
    try:
        unidade_str = f"{unidade}º"
        res_p = db_provas.table("modelos_prova").select("id, valor_questao")\
            .ilike("titulo", f"%{unidade_str}%")\
            .ilike("titulo", "%RECUPERAÇÃO%").execute()
            
        if res_p.data:
            mapa_valores = {p['id']: float(p.get('valor_questao') or 0.0) for p in res_p.data}
            prova_ids = list(mapa_valores.keys())
            
            res_r = db_provas.table("resultados_provas")\
                .select("prova_id")\
                .eq("aluno_id", aluno_id)\
                .in_("prova_id", prova_ids)\
                .eq("acertou", True).execute()
            
            if res_r.data:
                for registro in res_r.data:
                    p_id = registro['prova_id']
                    rec += mapa_valores.get(p_id, 0.0)
    except:
        pass
    return rec

def mostrar_tela_desempenho(db_alunos, db_provas):
    st.subheader("📊 Meu Desempenho Acadêmico")
    
    if 'aluno' not in st.session_state:
        return
    
    aluno = st.session_state.aluno
    aluno_id = str(aluno['id'])
    
    col_un, _ = st.columns([1, 2])
    with col_un:
        unidade_sel = st.selectbox("Selecione o Bimestre:", ["1", "2", "3", "4"], index=0)
    
    # 1. Busca de dados
    at1, at2, at3, at4, at5, n2 = buscar_todas_notas(db_provas, aluno_id, unidade_sel)
    nota_rec = buscar_notas_recuperacao(db_provas, aluno_id, unidade_sel)
    
    # 2. Lógica de Cálculos (Padrão SIEPE)
    soma_n1_bruta = at1 + at2 + at3 + at4 + at5
    soma_n1 = arredondar_siepe(soma_n1_bruta)
    media_original = arredondar_siepe((soma_n1 + n2) / 2) if (soma_n1 + n2) > 0 else 0.0
    
    status_rec = "NÃO REALIZADA"
    media_final = media_original

    if nota_rec > 0:
        if nota_rec > media_original:
            status_rec = "✅ RECUPERADO"
            media_final = nota_rec
        else:
            status_rec = "❌ NÃO RECUPERADO"

    # 3. Métricas de Resumo
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Soma N1", f"{soma_n1:.1f}")
    c2.metric("Nota N2", f"{n2:.1f}")
    c3.metric("REC", f"{nota_rec:.1f}")
    c4.metric("Média Final", f"{media_final:.1f}")
    
    st.write("---")
    
    # 4. Tabela Detalhada com Sequência SIEPE
    df_exibicao = pd.DataFrame({
        "AT1": [f"{at1:.1f}"],
        "AT2": [f"{at2:.1f}"],
        "AT3": [f"{at3:.1f}"],
        "AT4": [f"{at4:.1f}"],
        "AT5": [f"{at5:.1f}"],
        "N1": [f"{soma_n1:.1f}"],
        "N2": [f"{n2:.1f}"],
        "Nota REC": [f"{nota_rec:.1f}"],
        "Status REC": [status_rec],
        "Média Final": [f"{media_final:.1f}"]
    })
    
    # Exibe a tabela sem o índice lateral
    st.table(df_exibicao)

    # Feedback visual para o aluno
    if status_rec == "✅ RECUPERADO":
        st.success(f"🎉 Parabéns! Média Final atualizada pela Recuperação: {media_final:.1f}")
    elif media_final >= 6.0:
        st.info(f"Aluno aprovado com média {media_final:.1f}")
    elif (soma_n1 + n2) > 0:
        st.warning(f"Atenção: Média atual {media_final:.1f} está abaixo de 6.0.")