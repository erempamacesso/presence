import streamlit as st
from supabase import create_client
import pandas as pd

# --- 1. CONFIGURAÇÃO E CONEXÃO ---
st.set_page_config(page_title="EREMPAM - Avaliação", layout="centered")

URL = st.secrets["SUPABASE_URL_PROVAS"]
KEY = st.secrets["SUPABASE_KEY_PROVAS"]
supabase = create_client(URL, KEY)

st.title("📝 Portal de Avaliações - EREMPAM")

# --- 2. BUSCAR PROVAS ATIVAS ---
# Puxa os modelos de prova que estão com status ativa = True
res_provas = supabase.table("modelos_prova").select("*").eq("ativa", True).execute()
provas = res_provas.data

if not provas:
    st.info("Nenhuma prova ativa no momento. Aguarde o professor publicar.")
    st.stop()

# --- 3. SELEÇÃO DA PROVA ---
# Cria um dicionário para o selectbox ficar bonito (Título - Série)
opcoes_provas = {p['id']: f"{p['titulo']} ({p['serie']})" for p in provas}

prova_selecionada_id = st.selectbox(
    "Selecione a prova que deseja realizar:", 
    options=list(opcoes_provas.keys()), 
    format_func=lambda x: opcoes_provas[x]
)

st.divider()

# --- 4. RENDERIZAR A PROVA SELECIONADA ---
if prova_selecionada_id:
    # Pega os dados da prova escolhida
    prova_atual = next(p for p in provas if p['id'] == prova_selecionada_id)
    ids_questoes = prova_atual['questoes_ids']
    
    st.subheader(f"📄 {prova_atual['titulo']}")
    st.caption(f"Série: {prova_atual['serie']} | Total de questões: {len(ids_questoes)}")
    
    # Busca as questões no banco usando a lista de IDs
    # O comando in_ busca todos os IDs de uma vez só!
    res_questoes = supabase.table("questoes").select("*").in_("id", ids_questoes).execute()
    questoes = res_questoes.data
    
    # Ordena as questões para aparecerem na mesma ordem que o professor selecionou
    questoes_ordenadas = sorted(questoes, key=lambda q: ids_questoes.index(q['id']))
    
    # Variável para guardar as respostas do aluno
    respostas_aluno = {}
    
    with st.form("form_prova"):
        for i, q in enumerate(questoes_ordenadas):
            st.markdown(f"### Questão {i + 1}")
            # Mostra o enunciado (renderiza o HTML do Quill)
            st.markdown(q['enunciado'], unsafe_allow_html=True)
            
            # Monta as alternativas
            alts = q.get('alternativas', {})
            opcoes_radio = []
            for letra in ["A", "B", "C", "D"]:
                texto_alt = alts.get(letra, "")
                if texto_alt:
                    opcoes_radio.append(f"{letra}) {texto_alt}")
            
            # Coleta a resposta
            escolha = st.radio("Selecione sua resposta:", options=opcoes_radio, index=None, key=f"resp_{q['id']}")
            
            if escolha:
                # Salva apenas a letra (A, B, C ou D)
                respostas_aluno[q['id']] = escolha[0]
                
            st.divider()
            
        # Botão de Envio
        enviado = st.form_submit_button("✅ Finalizar e Enviar Prova", type="primary", use_container_width=True)
        
        if enviado:
            if len(respostas_aluno) < len(questoes_ordenadas):
                st.warning("⚠️ Você precisa responder todas as questões antes de enviar!")
            else:
                st.success("🎉 Prova enviada com sucesso! (A lógica de salvar a nota entra aqui)")
                st.balloons()