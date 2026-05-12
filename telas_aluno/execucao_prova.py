import streamlit as st
import time
from datetime import datetime
import re
import random
import ast
import math

# --- FUNÇÃO OFICIAL DE ARREDONDAMENTO SIEPE (Necessária para a barreira) ---
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

    st.title(f"📝 {prova['titulo']}")

    # --- 🛡️ BARREIRA DE ACESSO PARA RECUPERAÇÃO ---
    if prova.get('recuperacao') == True:
        aluno_id = str(aluno['id'])
        
        # 1. Busca as notas do aluno para calcular a média
        with st.spinner("Validando seu acesso para esta recuperação..."):
            res_notas = supabase.table("notas_atividades").select("*").eq("aluno_id", aluno_id).execute()
            
            media_atual = 0.0
            if res_notas.data:
                # Pegamos a primeira linha (ajuste conforme a unidade se necessário)
                n = res_notas.data[0]
                
                # Cálculo de N1 (AT1+AT2+AT3+AT4+AT5) e N2 (Prova)
                # Tratando nulos como 0.0
                at_soma = sum([float(n.get(f'at{i}', 0) or 0) for i in range(1, 6)])
                n1 = arredondar_siepe(at_soma)
                n2 = float(n.get('prova', 0) or 0)
                
                media_atual = arredondar_siepe((n1 + n2) / 2)

            # 2. Lógica de Bloqueio
            if media_atual >= 6.0:
                st.error("### 🔒 Acesso Restrito")
                st.warning(f"Olá {aluno['nome']}, sua média atual é **{media_atual:.1f}**. "
                           "Esta atividade é exclusiva para estudantes com média inferior a 6.0.")
                
                if st.button("⬅️ Voltar para Atividades"):
                    st.session_state.etapa = "ante_sala"
                    st.rerun()
                st.stop() # Impede a renderização do botão de iniciar
            else:
                st.success(f"✅ Recuperação Liberada! (Sua média: {media_atual:.1f})")

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
        # Inicializa o dicionário de respostas se não existir
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

    # --- CÁLCULO DO TEMPO RESTANTE ---
    inicio = datetime.fromisoformat(st.session_state.inicio_prova)
    tempo_passado = (datetime.now() - inicio).total_seconds() / 60
    tempo_restante = int(prova['tempo_duracao'] - tempo_passado)

    # Header da Prova com Cronômetro
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

    # --- RENDERIZAÇÃO DAS QUESTÕES ---
    questoes = st.session_state.get('questoes_carregadas', [])
    
    if not questoes:
        with st.spinner("Carregando questões..."):
            res_q = supabase.table("questoes").select("*").in_("id", prova['questoes_ids']).execute()
            questoes = res_q.data
            # Opcional: Randomizar ordem das questões
            random.shuffle(questoes)
            st.session_state.questoes_carregadas = questoes

    for i, q in enumerate(questoes):
        with st.container(border=True):
            st.markdown(f"**Questão {i+1}**")
            st.write(limpar_html(q['enunciado']))
            
            # Tratamento das alternativas
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
            
            # Recupera resposta anterior se houver
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
    """Processa as respostas e salva no banco de dados."""
    prova = st.session_state.prova_config
    aluno = st.session_state.aluno
    questoes = st.session_state.questoes_carregadas
    
    dados_insercao = []
    
    with st.spinner("Enviando suas respostas..."):
        for q in questoes:
            id_q = str(q['id'])
            letra_aluno = st.session_state.respostas_aluno.get(id_q)
            
            # Gabarito pode estar em diferentes campos dependendo do seu banco
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
            # Salva resultados
            supabase.table("resultados_provas").insert(dados_insercao).execute()
            
            # Limpa dados da prova da sessão
            keys_to_clear = ['questoes_carregadas', 'respostas_aluno', 'inicio_prova', 'prova_config']
            for k in keys_to_clear:
                if k in st.session_state: del st.session_state[k]
                
            st.session_state.etapa = "resultado_final"
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar resultados: {e}")