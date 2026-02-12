import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

st.set_page_config(page_title="Chamada Rápida", page_icon="📝")

# 1. Configuração e Conexão
load_dotenv()

SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    st.error("Erro: Credenciais do Supabase não encontradas.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. LISTA DE SENHAS (PINS) DAS TURMAS
# ==========================================
# Padrão criado:
# 1º Ano: 1010, 1020, 1030...
# 2º Ano: 2010, 2020...
# 3º Ano: 3010, 3020...
SENHAS_TURMAS = {
    # 1º ANO
    "1A": "1010",
    "1B": "1020",
    "1C": "1030",
    "1D": "1040",
    "1E": "1050",
    
    # 2º ANO
    "2A": "2010",
    "2B": "2020",
    "2C": "2030",
    "2D": "2040",
    
    # 3º ANO
    "3A": "3010",
    "3B": "3020",
    "3C": "3030",
    "3D": "3040"
}

# 3. Pega a turma pelo Link
params = st.query_params
turma_url = params.get("turma", None)

st.title("📝 Chamada Digital")

if not turma_url:
    st.error("Link inválido. Acesse através do Painel Administrativo.")
    st.stop()

# 4. Tratamento do nome da turma (Remove espaços e deixa maiúsculo)
# Isso garante que se o link for "...?turma=1 a", o sistema entenda "1A"
turma_limpa = turma_url.upper().replace(" ", "").strip()

st.info(f"Turma detectada: {turma_limpa}")

# Campo de Senha
senha_digitada = st.text_input("Digite o PIN da Turma:", type="password")

# Verifica se a turma existe na lista de senhas
if turma_limpa not in SENHAS_TURMAS:
    st.error(f"A turma '{turma_limpa}' não está configurada no sistema de senhas.")
    st.stop()

# Verifica a senha
if senha_digitada == SENHAS_TURMAS.get(turma_limpa):
    st.success("🔓 Acesso Liberado!")
    
    # 5. Busca alunos
    try:
        # Busca tanto pela turma limpa ("1A") quanto pela original ("1 A") para garantir
        response = supabase.table("alunos").select("nome, id").eq("turma", turma_limpa).order("nome").execute()
        
        # Se não achar com "1A", tenta com "1 A" (caso no banco esteja separado)
        if not response.data:
            turma_espaco = f"{turma_limpa[0]} {turma_limpa[1:]}" # Transforma 1A em "1 A"
            response = supabase.table("alunos").select("nome, id").eq("turma", turma_espaco).order("nome").execute()
            
        alunos = response.data
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        alunos = []
    
    if not alunos:
        st.warning(f"Nenhum aluno encontrado para a turma {turma_limpa}.")
    else:
        with st.form("form_chamada"):
            st.markdown(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}")
            st.markdown("### 📢 Lista de Presença")
            st.caption("Desmarque quem faltou. (Caixa marcada = Presente)")
            
            presencas = {}
            
            # Layout responsivo (2 colunas)
            cols = st.columns(2)
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    # O ID único do aluno é usado na chave para evitar conflitos de nomes iguais
                    presencas[aluno['id']] = st.checkbox(aluno['nome'], value=True, key=aluno['id'])
            
            st.divider()
            obs = st.text_area("Observações (Opcional):", placeholder="Conteúdo dado, ocorrências, etc.")
            enviar = st.form_submit_button("🚀 Enviar Chamada", type="primary", use_container_width=True)
            
            if enviar:
                fuso = pytz.timezone('America/Recife')
                data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
                
                dados_para_enviar = []
                for aluno in alunos:
                    # Pega o status baseado no ID do aluno
                    presente = presencas[aluno['id']]
                    status = "P" if presente else "F"
                    
                    dados_para_enviar.append({
                        "turma": turma_limpa,
                        "aluno_nome": aluno['nome'],
                        "status": status,
                        "data_chamada": data_hoje,
                        "obs": obs
                    })
                
                try:
                    # 1. Remove chamada anterior do mesmo dia (para permitir correção)
                    supabase.table("frequencia").delete().match({
                        "turma": turma_limpa, 
                        "data_chamada": data_hoje
                    }).execute()
                    
                    # 2. Insere a nova
                    supabase.table("frequencia").insert(dados_para_enviar).execute()
                    
                    st.success("✅ Chamada registrada com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")

elif senha_digitada:
    st.error("🚫 PIN incorreto para esta turma.")
