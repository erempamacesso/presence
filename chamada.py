import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import time  # <--- FALTAVA ISSO PARA O ERRO DE SALVAMENTO

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
SENHAS_TURMAS = {
    # 1º ANO
    "1A": "1010", "1B": "1020", "1C": "1030", "1D": "1040", "1E": "1050",
    # 2º ANO
    "2A": "2010", "2B": "2020", "2C": "2030", "2D": "2040",
    # 3º ANO
    "3A": "3010", "3B": "3020", "3C": "3030", "3D": "3040"
}

# 3. Pega a turma pelo Link
params = st.query_params
turma_url = params.get("turma", None)

st.title("📝 Chamada Digital")

if not turma_url:
    st.error("Link inválido. Acesse através do Painel Administrativo.")
    st.stop()

# Limpa a turma para validar a senha (ex: transforma "1A" ou "1 a" em "1A")
turma_limpa = turma_url.upper().replace(" ", "").strip()
# Remove o símbolo 'º' se vier no link, para garantir a chave da senha correta
turma_chave_senha = turma_limpa.replace("º", "")

st.info(f"Turma detectada: {turma_chave_senha}")

# Campo de Senha
senha_digitada = st.text_input("Digite o PIN da Turma:", type="password")

# Verifica se a turma existe na lista de senhas
if turma_chave_senha not in SENHAS_TURMAS:
    st.error(f"A turma '{turma_chave_senha}' não está configurada no sistema de senhas.")
    st.stop()

# Verifica a senha
if senha_digitada == SENHAS_TURMAS.get(turma_chave_senha):
    st.success("🔓 Acesso Liberado!")
    
    # =======================================================
    # 5. BUSCA INTELIGENTE DE ALUNOS (CORREÇÃO AQUI)
    # =======================================================
    try:
        # Tenta extrair número e letra (ex: 1A -> num=1, letra=A)
        # Isso serve para construir o formato "1º A" que está no seu banco
        numero = turma_chave_senha[0]
        letra = turma_chave_senha[1:]

        # Lista de formatos possíveis para tentar buscar no banco
        # O sistema vai tentar um por um até achar os alunos
        formatos_tentativa = [
            f"{numero}º {letra}",  # Formato do seu print: "1º A"
            f"{numero}º{letra}",   # Formato "1ºA"
            f"{numero} {letra}",   # Formato "1 A"
            turma_chave_senha      # Formato "1A"
        ]
        
        alunos = []
        turma_encontrada_db = ""

        for formato in formatos_tentativa:
            response = supabase.table("alunos").select("nome, id, turma").eq("turma", formato).order("nome").execute()
            if response.data:
                alunos = response.data
                turma_encontrada_db = formato # Guarda qual formato funcionou para salvar depois
                break # Encontrou? Para de procurar.
        
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        alunos = []
    
    if not alunos:
        st.warning(f"Nenhum aluno encontrado. O sistema tentou buscar por: {', '.join(formatos_tentativa)}")
        st.info("Dica: Verifique se no banco de dados a coluna 'turma' está preenchida exatamente como '1º A'.")
    else:
        with st.form("form_chamada"):
            st.markdown(f"**Turma no Banco:** {turma_encontrada_db}")
            st.markdown(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}")
            st.markdown("### 📢 Lista de Presença")
            st.caption("Desmarque quem faltou. (Caixa marcada = Presente)")
            
            presencas = {}
            
            # Layout responsivo (2 colunas)
            cols = st.columns(2)
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    presencas[aluno['id']] = st.checkbox(aluno['nome'], value=True, key=aluno['id'])
            
            st.divider()
            obs = st.text_area("Observações (Opcional):", placeholder="Conteúdo dado, ocorrências, etc.")
            enviar = st.form_submit_button("🚀 Enviar Chamada", type="primary", use_container_width=True)
            
            if enviar:
                fuso = pytz.timezone('America/Recife')
                data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
                
                dados_para_enviar = []
                for aluno in alunos:
                    presente = presencas[aluno['id']]
                    status = "P" if presente else "F"
                    
                    dados_para_enviar.append({
                        "turma": turma_encontrada_db, # Usa o nome exato que está no banco (ex: 1º A)
                        "aluno_nome": aluno['nome'],
                        "status": status,
                        "data_chamada": data_hoje,
                        "obs": obs
                    })
                
                try:
                    # 1. Remove chamada anterior do mesmo dia para essa turma específica
                    supabase.table("frequencia").delete().match({
                        "turma": turma_encontrada_db, 
                        "data_chamada": data_hoje
                    }).execute()
                    
                    # 2. Insere a nova
                    supabase.table("frequencia").insert(dados_para_enviar).execute()
                    
                    st.success(f"✅ Chamada da turma {turma_encontrada_db} realizada com sucesso!")
                    time.sleep(2) # Pausa para ler a mensagem
                    st.rerun()    # Recarrega a página
                    
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")

elif senha_digitada:
    st.error("🚫 PIN incorreto para esta turma.")
