import streamlit as st
import time
from datetime import datetime
import re
import random
import ast
import math
from datetime import time as dt_time

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE ---
def arredondar_siepe(nota):
    """
    Regra de arredondamento:
    ,0 e ,1 -> ,0
    ,2 a ,6 -> ,5
    ,7 a ,9 -> +1,0 (próximo número inteiro)
    """
    if nota is None:
        return 0.0
        
    nota = float(nota)
    inteiro = math.floor(nota)
    decimal = round((nota - inteiro) * 10)
    
    if decimal in [0, 1]:
        return float(inteiro)
    elif decimal in [2, 3, 4, 5, 6]:
        return float(inteiro + 0.5)
    else: # 7, 8, 9, 10
        return float(inteiro + 1)

def limpar_html(html):
    """Remove tags HTML e limpa o texto para exibição pura."""
    if not html:
        return ""
    texto_limpo = re.sub(r'<[^>]+>', '', str(html))
    return texto_limpo.strip()

def extrair_texto_alternativa(conteudo):
    """Descasca o dicionário do banco para pegar só o texto limpo da alternativa"""
    if isinstance(conteudo, dict):
        return str(conteudo.get('texto', conteudo))
    
    if isinstance(conteudo, str):
        conteudo = conteudo.strip()
        if conteudo.startswith("{") and "'texto'" in conteudo:
            try:
                dict_convertido = ast.literal_eval(conteudo)
                if isinstance(dict_convertido, dict):
                    return str(dict_convertido.get('texto', ''))
            except Exception:
                pass
    return str(conteudo)

def converter_data_prova(data_val):
    if not data_val or str(data_val).lower() == "none":
        return None
    try:
        return datetime.strptime(str(data_val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

def converter_hora_prova(hora_val):
    if not hora_val or str(hora_val).lower() == "none":
        return None
    for formato in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(str(hora_val)[:8], formato).time()
        except Exception:
            pass
    return None

def campo_hora_prova(prova, candidatos):
    for campo in candidatos:
        if campo in prova:
            return campo
    return None

def prova_disponivel_agora(prova):
    if not prova.get("ativa", True):
        return False

    agora = datetime.now()
    data_inicio = converter_data_prova(prova.get("data_inicio"))
    data_fim = converter_data_prova(prova.get("data_limite"))
    campo_inicio = campo_hora_prova(prova, ["hora_inicio", "horario_inicio"])
    campo_fim = campo_hora_prova(
        prova,
        ["hora_limite", "horario_limite", "hora_fim", "horario_fim", "hora_termino", "horario_termino"]
    )
    hora_inicio = converter_hora_prova(prova.get(campo_inicio)) if campo_inicio else dt_time(0, 0)
    hora_fim = converter_hora_prova(prova.get(campo_fim)) if campo_fim else dt_time(23, 59, 59)

    if data_inicio and agora < datetime.combine(data_inicio, hora_inicio):
        return False
    if data_fim and agora > datetime.combine(data_fim, hora_fim):
        return False
    return True

def render_instrucoes(supabase):
    """Tela de orientações antes do início da prova com barreira de nota."""
    prova = st.session_state.get('prova_config')
    aluno = st.session_state.get('aluno')

    if not prova or not aluno:
        st.error("⚠️ Erro ao carregar configurações da prova ou dados do aluno.")
        if st.button("Voltar"):
            st.session_state.etapa = "ante_sala"
            st.rerun()
        return

    try:
        res_prova_atual = supabase.table("modelos_prova").select("*").eq("id", prova["id"]).limit(1).execute()
        if res_prova_atual.data:
            prova = res_prova_atual.data[0]
            st.session_state.prova_config = prova
    except Exception:
        pass

    if not prova_disponivel_agora(prova):
        st.error("### 🔒 Prova indisponível")
        st.warning("Esta prova foi desativada ou o horário programado para acesso já encerrou.")
        if st.button("⬅️ Voltar para a Lista de Atividades", use_container_width=True):
            st.session_state.prova_config = None
            st.session_state.etapa = "ante_sala"
            st.rerun()
        return

    # ==========================================================
    # 🛡️ TRAVA DE REEXECUÇÃO CORRIGIDA E BLINDADA
    # ==========================================================
    aluno_id = str(aluno['id'])
    prova_id = str(prova['id'])
    
    with st.spinner("Verificando se você já realizou esta atividade..."):
        # Selecionamos a coluna 'aluno_id' que sabemos com 100% de certeza que existe na tabela
        res_check = supabase.table("resultados_provas")\
            .select("aluno_id")\
            .eq("aluno_id", aluno_id)\
            .eq("prova_id", prova_id)\
            .limit(1).execute()

    if res_check.data:
        st.error("### 🛑 Avaliação já Concluída")
        st.warning("Você já realizou esta prova e suas respostas foram salvas no sistema. Não é permitido refazer a avaliação.")
        if st.button("⬅️ Voltar para a Lista de Atividades", use_container_width=True):
            st.session_state.etapa = "ante_sala"
            st.rerun()
        return # Trava completamente a renderização e o botão de iniciar abaixo
    # ==========================================================

    st.title(f"📝 {prova['titulo']}")

    # --- 🛡️ BARREIRA DE ACESSO POR MÉDIA (EXCLUSIVO PARA RECUPERAÇÃO) ---
    if prova.get('recuperacao') == True:
        with st.spinner("Validando sua média para esta recuperação..."):
            res_notas = supabase.table("notas_atividades").select("*").eq("aluno_id", aluno_id).execute()
            
            media_atual = 0.0
            if res_notas.data:
                n = res_notas.data[0]
                at_soma = sum([float(n.get(f'at{i}', 0) or 0) for i in range(1, 6)])
                n1 = arredondar_siepe(at_soma)
                n2 = float(n.get('prova', 0) or 0)
                media_atual = arredondar_siepe((n1 + n2) / 2)

            if media_atual >= 6.0:
                st.error("### 🔒 Acesso Restrito")
                st.warning(f"Olá {aluno['nome']}, sua média atual é **{media_atual:.1f}**. "
                           "Esta atividade é exclusiva para estudantes com média inferior a 6.0.")
                
                if st.button("⬅️ Voltar para Atividades"):
                    st.session_state.etapa = "ante_sala"
                    st.rerun()
                st.stop()
            else:
                st.success(f"✅ Recuperação Liberada! (Sua média atual é: {media_atual:.1f})")

    # --- INSTRUÇÕES PADRÃO ---
    st.info("Por favor, leia as instruções abaixo antes de começar.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        **Detalhes da Avaliação:**
        - 🧩 **Total de Questões:** {len(prova.get('questoes_ids', []))}
        - 💎 **Valor por Questão:** {prova.get('valor_questao', 0.5)}
        - ⏱️ **Duração Máxima:** {prova.get('tempo_duracao', 60)} minutos
        """)
    
    with col2:
        st.markdown("""
        **Orientações Importantes:**
        - Não atualize a página durante a prova.
        - O cronômetro inicia ao clicar no botão abaixo.
        - Verifique sua conexão com a internet.
        """)

    st.divider()
    
    if st.button("🚀 INICIAR PROVA AGORA", type="primary", use_container_width=True):
        st.session_state.etapa = "em_prova"
        st.session_state.inicio_prova = datetime.now().isoformat()
        if 'respostas_aluno' not in st.session_state:
            st.session_state.respostas_aluno = {}
        st.rerun()

def render_prova(supabase):
    """Tela de execução da prova com questões e cronômetro."""
    prova = st.session_state.get('prova_config')
    aluno = st.session_state.get('aluno')
    
    if not prova or 'inicio_prova' not in st.session_state:
        st.error("Sessão de prova inválida.")
        st.session_state.etapa = "ante_sala"
        st.rerun()
        return

    inicio = datetime.fromisoformat(st.session_state.inicio_prova)
    tempo_passado = (datetime.now() - inicio).total_seconds() / 60
    tempo_restante = int(prova['tempo_duracao'] - tempo_passado)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.title(f"📖 {prova['titulo']}")
    with c2:
        if tempo_restante <= 5:
            st.error(f"⏱️ {tempo_restante} min")
        else:
            st.info(f"⏱️ {tempo_restante} min")

    if tempo_restante <= 0:
        st.warning("⚠️ O tempo acabou! Suas respostas serão enviadas automaticamente.")
        finalizar_prova(supabase)
        return

    questoes = st.session_state.get('questoes_carregadas', [])
    
    if not questoes:
        with st.spinner("Carregando questões..."):
            res_q = supabase.table("questoes").select("*").in_("id", prova['questoes_ids']).execute()
            questoes = res_q.data
            random.shuffle(questoes)
            st.session_state.questoes_carregadas = questoes

    for i, q in enumerate(questoes):
        with st.container(border=True):
            st.markdown(f"**Questão {i+1}**")
            st.write(limpar_html(q['enunciado']))
            
            alts = q.get('alternativas', {})
            if isinstance(alts, str):
                try: alts = ast.literal_eval(alts)
                except: alts = {}
            
            opcoes = []
            mapeamento = {}
            for letra in ['A', 'B', 'C', 'D', 'E']:
                if letra in alts:
                    texto = extrair_texto_alternativa(alts[letra])
                    label = f"({letra}) {texto}"
                    opcoes.append(label)
                    mapeamento[label] = letra
            
            idx_anterior = None
            resp_salva = st.session_state.respostas_aluno.get(str(q['id']))
            if resp_salva:
                for idx, texto_opcao in enumerate(opcoes):
                    if texto_opcao.startswith(f"({resp_salva})"):
                        idx_anterior = idx
            
            escolha = st.radio(
                f"Selecione a resposta para a questão {i+1}:",
                options=opcoes,
                index=idx_anterior,
                key=f"q_{q['id']}",
                label_visibility="collapsed"
            )
            
            if escolha:
                st.session_state.respostas_aluno[str(q['id'])] = mapeamento[escolha]

    st.divider()
    if st.button("📥 FINALIZAR E ENVIAR AVALIAÇÃO", type="primary", use_container_width=True):
        finalizar_prova(supabase)

def finalizar_prova(supabase):
    """Processa as respostas e salva no banco de dados com segurança cirúrgica."""
    prova = st.session_state.prova_config
    aluno = st.session_state.aluno
    questoes = st.session_state.questoes_carregadas
    
    dados_insercao = []
    
    with st.spinner("Enviando suas respostas..."):
        for q in questoes:
            id_q = str(q['id'])
            letra_aluno = st.session_state.respostas_aluno.get(id_q)
            gabarito = q.get('resposta_correta') or q.get('gabarito') or q.get('resposta')
            
            acertou = False
            if letra_aluno and gabarito:
                if str(letra_aluno).strip().upper() == str(gabarito).strip().upper():
                    acertou = True
            
            dados_insercao.append({
                "aluno_id": str(aluno['id']),
                "prova_id": str(prova['id']),
                "questao_id": id_q,
                "resposta_aluno": letra_aluno,
                "acertou": acertou
            })
        
        try:
            # 1. Salva os resultados das questões individuais
            supabase.table("resultados_provas").insert(dados_insercao).execute()
            
            # =========================================================================
            # 🚀 PROCESSAMENTO INTEGRAL E ULTRA PROTEGIDO DA RECUPERAÇÃO
            # =========================================================================
            if prova.get('recuperacao') == True:
                acertos = sum(1 for d in dados_insercao if d.get("acertou") == True)
                valor_q = float(prova.get('valor_questao') or 0.5)
                nota_rec = arredondar_siepe(acertos * valor_q)
                
                unidade_nota = prova.get('unidade')
                if not unidade_nota:
                    unidade_nota = "1º Bimestre"
                    titulo_prova = str(prova.get('titulo', '')).upper()
                    if "2º" in titulo_prova:
                        unidade_nota = "2º Bimestre"
                    elif "3º" in titulo_prova:
                        unidade_nota = "3º Bimestre"
                    elif "4º" in titulo_prova:
                        unidade_nota = "4º Bimestre"
                
                # 🛡️ CHECAGEM CIRÚRGICA: Vê se o aluno já tem registro de nota neste bimestre
                chk_nota = supabase.table("notas_atividades")\
                    .select("aluno_id")\
                    .eq("aluno_id", str(aluno['id']))\
                    .eq("unidade", unidade_nota)\
                    .execute()
                
                if chk_nota.data:
                    # O aluno JÁ POSSUI notas gravadas. Usamos UPDATE para alterar APENAS o campo 'rec'
                    # e garantir que 'at1', 'at2', 'at3', 'at4', 'at5' e 'prova' fiquem INTOCADOS!
                    supabase.table("notas_atividades")\
                        .update({"rec": nota_rec})\
                        .eq("aluno_id", str(aluno['id']))\
                        .eq("unidade", unidade_nota)\
                        .execute()
                else:
                    # Se o aluno estranhamente não possuir linha nenhuma, insere o registro base
                    dados_inserir = {
                        "aluno_id": str(aluno['id']),
                        "unidade": unidade_nota,
                        "rec": nota_rec
                    }
                    if 'turma' in aluno:
                        dados_inserir["turma"] = str(aluno['turma'])
                    supabase.table("notas_atividades").insert(dados_inserir).execute()
            # =========================================================================
            
            # Limpa dados da prova da sessão
            keys_to_clear = ['questoes_carregadas', 'respostas_aluno', 'inicio_prova', 'prova_config']
            for k in keys_to_clear:
                if k in st.session_state: del st.session_state[k]
                
            st.session_state.etapa = "resultado_final"
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar resultados: {e}")
