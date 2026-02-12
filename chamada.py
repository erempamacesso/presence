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
    st.error("Erro: Credenciais não encontradas.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. SENHAS (PIN)
# A chave aqui é a versão SIMPLIFICADA (o que vem no link)
SENHAS_TURMAS = {
    "1A": "1010",
    "1B": "1020",
    "2A": "2010",
    "2B": "2020",
    "3A": "3010",
    "3B": "3020"
}

# 3. TRADUTOR (O Pulo do Gato 😺)
# Converte o link SIMPLES para o nome REAL no banco
MAPA_NOMES_BANCO = {
    "1A": "1º A",  # Link 1A -> Busca 1º A
    "1B": "1º B",
    "2A": "2º A",
    "2B": "2º B",
    "3A": "3º A",
    "3B": "3º B"
}

# 4. Pega a turma pelo Link
params = st.query_params
turma_url = params.get("turma", None)

st.title("📝 Chamada Digital")

if not turma_url:
    st.error("Link inválido. Informe a turma no link (ex: ?turma=1A).")
    st.stop()

# Limpeza: Transforma "1 A", "1a", "1 A " em "1A"
turma_limpa = turma_url.upper().replace(" ", "").replace("º", "").replace("°", "").strip()

# Descobre o nome oficial no banco (com a bolinha)
nome_oficial_banco = MAPA_NOMES_BANCO.get(turma_limpa, turma_limpa)

st.info(f"Turma: {nome_oficial_banco}") # Mostra o nome bonito pro usuário

senha_digitada = st.text_input("Digite o PIN da Turma:", type="password")

if senha_digitada == SENHAS_TURMAS.get(turma_limpa):
    st.success("Acesso Liberado!")
    
    # 5. Busca alunos usando o NOME OFICIAL (Com a bolinha)
    try:
        response = supabase.table("alunos").select("nome").eq("turma", nome_oficial_banco).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error(f"Erro ao buscar alunos: {e}")
        alunos = []
    
    if not alunos:
        st.warning(f"Nenhum aluno encontrado na turma '{nome_oficial_banco}'.")
    else:
        with st.form("form_chamada"):
            st.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}")
            st.write("Marque quem está **PRESENTE**:")
            
            presencas = {}
            cols = st.columns(2)
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
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
                        "turma": nome_oficial_banco, # Salva com o nome oficial
                        "aluno_nome": nome,
                        "status": status,
                        "data_chamada": data_hoje
                    })
                
                try:
                    # Apaga anterior do mesmo dia usando o nome oficial
                    supabase.table("frequencia").delete().match({"turma": nome_oficial_banco, "data_chamada": data_hoje}).execute()
                    
                    # Insere novos
                    supabase.table("frequencia").insert(dados_para_enviar).execute()
                    st.success("✅ Chamada realizada com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

elif senha_digitada:
    st.error("🚫 Senha incorreta.")
