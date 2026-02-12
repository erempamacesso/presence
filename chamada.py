import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import time # <--- O QUE ESTAVA FALTANDO

# Configuração da Página (Mobile First)
st.set_page_config(page_title="Chamada", page_icon="📝", layout="centered")

# --- CSS PARA ESTILO "REACT/APP" E CORREÇÕES ---
st.markdown("""
    <style>
        /* --- GERAL --- */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 3rem !important;
        }
        div[data-testid="column"] {
            padding: 0px !important;
        }

        /* --- AVATAR --- */
        .avatar-circle {
            width: 38px;
            height: 38px;
            background-color: #e9ecef;
            color: #495057;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: 700;
            font-size: 14px;
            border: 2px solid #dee2e6;
            margin-left: 5px;
        }

        /* --- NOME --- */
        .aluno-nome {
            font-size: 15px !important;
            font-weight: 600 !important;
            color: #212529;
            margin: 0;
            line-height: 1.1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        hr {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
            border-top: 1px solid #e9ecef;
        }

        /* --- CORES DO TOGGLE --- */
        div[data-testid="stToggleButton"] span[aria-checked="true"] {
            background-color: #28a745 !important; 
        }
        div[data-testid="stToggleButton"] span[aria-checked="false"] {
             background-color: #dc3545 !important; 
        }
        .stToggle {
            margin-top: -2px;
        }
    </style>
""", unsafe_allow_html=True)

# 1. Configuração e Conexão
load_dotenv()

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    st.error("Erro: Credenciais não encontradas.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. SENHAS (PIN)
SENHAS_TURMAS = {
    "1A": "1010", "1B": "1020",
    "2A": "2010", "2B": "2020",
    "3A": "3010", "3B": "3020"
}

# 3. TRADUTOR (Link -> Banco)
MAPA_NOMES_BANCO = {
    "1A": "1º A", "1B": "1º B",
    "2A": "2º A", "2B": "2º B",
    "3A": "3º A", "3B": "3º B"
}

# 4. Pega a turma pelo Link
params = st.query_params
turma_url = params.get("turma", None)

if not turma_url:
    st.warning("⚠️ Abra este link pelo QR Code da sala.")
    st.stop()

# Limpeza e Tradução
turma_limpa = turma_url.upper().replace(" ", "").replace("º", "").replace("°", "").strip()
nome_oficial_banco = MAPA_NOMES_BANCO.get(turma_limpa, turma_limpa)

# --- CABEÇALHO ---
st.markdown(f"<h4 style='margin:0; padding-top:10px; text-align:center;'>{nome_oficial_banco}</h4>", unsafe_allow_html=True)
st.caption(f"Data: {datetime.now().strftime('%d/%m/%Y')}", unsafe_allow_html=True)

# --- LOGIN ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.markdown("---")
    senha_digitada = st.text_input("PIN do Líder:", type="password", placeholder="Digite o PIN...", label_visibility="collapsed")
    if senha_digitada == SENHAS_TURMAS.get(turma_limpa):
        st.session_state["logado"] = True
        st.rerun()
    elif senha_digitada:
        st.error("Senha incorreta.")
    st.stop()

# --- ÁREA DA CHAMADA ---

try:
    response = supabase.table("alunos").select("id, nome").eq("turma", nome_oficial_banco).order("nome").execute()
    alunos = response.data
except Exception as e:
    st.error("Erro de conexão.")
    alunos = []

if not alunos:
    st.info("Nenhum aluno nesta turma.")
else:
    with st.container():
        presencas = {}
        
        for aluno in alunos:
            nome = aluno['nome']
            aluno_id = aluno.get('id', nome)
            
            st.markdown("---") 
            c1, c2, c3 = st.columns([1.2, 5, 1.8], vertical_alignment="center")
            
            with c1:
                partes = nome.split()
                iniciais = ""
                if len(partes) >= 2:
                    iniciais = partes[0][0] + partes[1][0]
                elif len(partes) == 1:
                     iniciais = partes[0][:2]
                iniciais = iniciais.upper()
                st.markdown(f"<div class='avatar-circle'>{iniciais}</div>", unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"<div class='aluno-nome' title='{nome}'>{nome}</div>", unsafe_allow_html=True)
            
            with c3:
                presencas[nome] = st.toggle("P/F", value=True, key=f"t_{aluno_id}", label_visibility="collapsed")

        st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True)
        enviar = st.button("🚀 CONFIRMAR CHAMADA", type="primary", use_container_width=True)
        
        if enviar:
            dados_para_enviar = []
            fuso = pytz.timezone('America/Recife')
            data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
            total_presentes = 0
            
            for nome_aluno, is_presente in presencas.items():
                status = "P" if is_presente else "F"
                if is_presente: total_presentes += 1
                dados_para_enviar.append({
                    "turma": nome_oficial_banco,
                    "aluno_nome": nome_aluno,
                    "status": status,
                    "data_chamada": data_hoje
                })
            
            try:
                # ⚠️ ATENÇÃO: Salvando na tabela 'frequencia'.
                # Se quiser na tabela 'presenca', mude o nome abaixo.
                supabase.table("frequencia").delete().match({"turma": nome_oficial_banco, "data_chamada": data_hoje}).execute()
                supabase.table("frequencia").insert(dados_para_enviar).execute()
                
                st.toast(f"✅ Chamada Salva! {total_presentes} presentes.", icon="🎉")
                time.sleep(2) # Agora vai funcionar porque importamos o time!
                 
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
