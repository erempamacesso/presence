import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz

st.set_page_config(page_title="Chamada Rápida", page_icon="📝")

# 1. Configuração e Conexão (CORRIGIDO)
load_dotenv() # Lê o arquivo .env

# O código abaixo procura primeiro nos Secrets (nuvem), se não achar, pega do .env (local)
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    st.error("Erro: Credenciais do Supabase não encontradas no .env")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Senhas das Turmas (Simples e eficiente)
SENHAS_TURMAS = {
    "1A": "1010", # Tirei os espaços para evitar erros (ex: "1 A" virou "1A")
    "1B": "1020",
    "2A": "2010",
    "3A": "3010"
}

# 3. Pega a turma pelo Link (ex: ?turma=1A)
params = st.query_params
turma_url = params.get("turma", None)

st.title("📝 Chamada Digital")

if not turma_url:
    st.error("Link inválido. Peça o link correto à coordenação.")
    st.info("Exemplo de link correto: .../?turma=1A")
    st.stop()

# 4. Validação de Segurança
# Remove espaços e deixa maiúsculo para garantir que "1 a" vire "1A"
turma_limpa = turma_url.upper().replace(" ", "").strip()
st.info(f"Turma detectada: {turma_limpa}")

senha_digitada = st.text_input("Digite o PIN da Turma:", type="password")

# Verifica se a senha bate com a turma
if senha_digitada == SENHAS_TURMAS.get(turma_limpa):
    st.success("Acesso Liberado!")
    
    # 5. Busca alunos da turma
    # Ajustei para buscar também onde a turma tem espaço ou não, por garantia
    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_url.upper().strip()).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error(f"Erro ao buscar alunos: {e}")
        alunos = []
    
    if not alunos:
        st.warning("Nenhum aluno encontrado nesta turma.")
    else:
        with st.form("form_chamada"):
            st.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}")
            st.write("Marque quem está **PRESENTE**:")
            
            presencas = {}
            
            # Layout em colunas para celular
            cols = st.columns(2)
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    # Checkbox começa marcado (True) = Presente
                    presencas[aluno['nome']] = st.checkbox(aluno['nome'], value=True) 
            
            st.divider()
            enviar = st.form_submit_button("🚀 Enviar Chamada", use_container_width=True)
            
            if enviar:
                dados_para_enviar = []
                fuso = pytz.timezone('America/Recife')
                data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
                
                for nome, presente in presencas.items():
                    status = "P" if presente else "F"
                    dados_para_enviar.append({
                        "turma": turma_limpa,
                        "aluno_nome": nome,
                        "status": status,
                        "data_chamada": data_hoje
                    })
                
                try:
                    # 1. Limpa chamada anterior do mesmo dia (evita duplicidade)
                    # Atenção: ajustei para deletar baseado na turma_limpa
                    supabase.table("frequencia").delete().match({"turma": turma_limpa, "data_chamada": data_hoje}).execute()
                    
                    # 2. Insere nova chamada
                    supabase.table("frequencia").insert(dados_para_enviar).execute()
                    
                    st.success("✅ Chamada realizada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

elif senha_digitada:
    st.error("🚫 Senha incorreta.")