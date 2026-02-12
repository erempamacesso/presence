import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

# Configuração da Página (Mobile First)
st.set_page_config(page_title="Chamada", page_icon="📝", layout="centered")

# --- CSS PARA ESTILO "REACT/APP" ---
st.markdown("""
    <style>
        /* Remove espaços em branco gigantes do Streamlit */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }
        
        /* Estiliza a linha do aluno para parecer um Card */
        .aluno-row {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 8px;
            margin-bottom: 8px;
            border-left: 5px solid #00C851; /* Verde padrão */
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* Texto do nome mais bonito */
        .aluno-nome {
            font-size: 16px !important;
            font-weight: 600 !important;
            color: #333;
            margin: 0;
            line-height: 1.2;
        }
        
        /* Remove padding das colunas internas para compactar */
        div[data-testid="column"] {
            padding: 0px !important;
        }
        
        /* Ajuste fino para alinhar o toggle verticalmente */
        .stToggle {
            margin-top: -5px;
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
col_head1, col_head2 = st.columns([1, 4])
with col_head1:
    st.write("📝") # Pode ser sua logo aqui
with col_head2:
    st.markdown(f"**Chamada: {nome_oficial_banco}**")
    st.caption(datetime.now().strftime('%d/%m/%Y'))

# --- LOGIN ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    senha_digitada = st.text_input("PIN do Líder:", type="password", placeholder="Digite a senha...")
    if senha_digitada == SENHAS_TURMAS.get(turma_limpa):
        st.session_state["logado"] = True
        st.rerun()
    elif senha_digitada:
        st.error("Senha incorreta.")
    st.stop() # Para aqui se não estiver logado

# --- ÁREA DA CHAMADA (SÓ APARECE SE LOGADO) ---

# Busca alunos
try:
    response = supabase.table("alunos").select("nome").eq("turma", nome_oficial_banco).order("nome").execute()
    alunos = response.data
except Exception as e:
    st.error("Erro de conexão.")
    alunos = []

if not alunos:
    st.info("Nenhum aluno nesta turma.")
else:
    with st.form("form_chamada", border=False):
        st.markdown("### 📋 Lista de Presença")
        
        presencas = {}
        
        # Loop para criar as linhas dos alunos
        for aluno in alunos:
            nome = aluno['nome']
            
            # Container estilizado visualmente (truque visual)
            st.markdown("---") 
            # Layout: Foto (1) | Nome (5) | Botão (2)
            c1, c2, c3 = st.columns([1.2, 5, 2], vertical_alignment="center")
            
            with c1:
                # Avatar gerado com as iniciais do aluno (API DiceBear)
                iniciais = "".join([n[0] for n in nome.split()[:2]])
                avatar_url = f"https://api.dicebear.com/7.x/initials/svg?seed={iniciais}&backgroundColor=e6e6e6&textColor=333"
                st.image(avatar_url, width=40)
            
            with c2:
                # Nome em negrito e compacto
                st.markdown(f"<div class='aluno-nome'>{nome}</div>", unsafe_allow_html=True)
            
            with c3:
                # Toggle: Muito melhor que checkbox para mobile
                # Value=True significa que já vem marcado como Presente
                presencas[nome] = st.toggle("Pres.", value=True, key=f"t_{nome}")

        st.markdown("---")
        
        # Botão Flutuante de Enviar (Fixo ou Grande no final)
        st.markdown("<br>", unsafe_allow_html=True)
        enviar = st.form_submit_button("🚀 ENVIAR CHAMADA", type="primary", use_container_width=True)
        
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
            
            # Salvar no Banco
            try:
                # 1. Limpa chamada duplicada do dia (se houver)
                supabase.table("frequencia").delete().match({
                    "turma": nome_oficial_banco, 
                    "data_chamada": data_hoje
                }).execute()
                
                # 2. Salva nova
                supabase.table("frequencia").insert(dados_para_enviar).execute()
                
                st.success(f"✅ Chamada enviada! {total_presentes} presentes.")
                st.balloons()
                
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
