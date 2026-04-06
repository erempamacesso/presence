import streamlit as st
import pandas as pd
import unicodedata
import time
import re

# ==================================================
# 1. FUNÇÕES DE APOIO E FOTOS (GITHUB)
# ==================================================

def limpar_texto(texto):
    """Padronização idêntica ao Fotograma para bater com as fotos do GitHub"""
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    nfkd = unicodedata.normalize('NFKD', str(texto))
    texto_limpo = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    return "".join(filter(str.isalnum, texto_limpo))

@st.cache_data(ttl=3600)
def buscar_fotos_github_cadastro():
    """Busca as fotos no repositório GitHub (Mesma lógica do Fotograma)"""
    try:
        from github import Github, Auth
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("🚨 GITHUB_TOKEN não configurado nos Secrets!")
            return {}
        
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence") # Substitua pelo seu repo se for diferente
        contents = repo.get_contents("alunos_fotos")
        
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception as e:
        st.error(f"Erro ao carregar fotos do GitHub: {e}")
        return {}

# ==================================================
# 2. FUNÇÃO PRINCIPAL CHAMADA PELO APP.PY
# ==================================================
def exibir_cadastro(supabase):
    
    # Gerenciamento de estado da aba para evitar o loop/reset
    if 'aba_cadastro_ativa' not in st.session_state:
        st.session_state.aba_cadastro_ativa = "📸 Fotos e Turmas"

    st.title("👤 Gestão de Estudantes")

    # Menu de navegação interno (Substitui o st.tabs para não resetar)
    opcoes = ["📸 Fotos e Turmas", "➕ Cadastro Manual", "🔍 Consulta Rápida"]
    escolha = st.segmented_control(
        "Selecione a funcionalidade:", 
        opcoes, 
        default=st.session_state.aba_cadastro_ativa,
        key="nav_interna_cadastro"
    )
    
    # Atualiza o estado quando o usuário clica
    st.session_state.aba_cadastro_ativa = escolha
    st.divider()

    # --- ABA: FOTOS E TURMAS (ONDE ESTAVA O PROBLEMA) ---
    if st.session_state.aba_cadastro_ativa == "📸 Fotos e Turmas":
        st.subheader("Gestão Visual de Turmas")
        
        # 1. Obter turmas existentes
        res_t = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
        
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            turma_sel = st.selectbox("Selecione a Turma para filtrar:", lista_turmas)
        with col_t2:
            if st.button("🔄 Atualizar Fotos"):
                st.cache_data.clear()
                st.rerun()

        # 2. Buscar Alunos e Fotos
        mapa_fotos = buscar_fotos_github_cadastro()
        res_alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute()
        alunos = res_alunos.data

        # Cabeçalho da Lista
        st.markdown("---")
        c_h1, c_h2, c_h3 = st.columns([1, 3, 2])
        c_h1.write("**Foto**")
        c_h2.write("**Estudante**")
        c_h3.write("**Mudar Turma**")

        for aluno in alunos:
            c1, c2, c3 = st.columns([1, 3, 2])
            
            # Coluna 1: Foto
            with c1:
                chave = limpar_texto(aluno['nome'])
                url = mapa_fotos.get(chave)
                if url:
                    st.image(url, width=60)
                else:
                    st.write("👤")
            
            # Coluna 2: Nome
            with c2:
                st.write(f"**{aluno['nome']}**")
                st.caption(f"ID: {aluno['id']}")
            
            # Coluna 3: Troca de Turma (O gatilho do loop)
            with c3:
                try: idx_atual = lista_turmas.index(aluno['turma'])
                except: idx_atual = 0
                
                nova_t = st.selectbox(
                    "Trocar", 
                    lista_turmas, 
                    index=idx_atual, 
                    key=f"alt_{aluno['id']}",
                    label_visibility="collapsed"
                )
                
                if nova_t != aluno['turma']:
                    supabase.table("alunos").update({"turma": nova_t}).eq("id", aluno['id']).execute()
                    st.toast(f"{aluno['nome']} movido para {nova_t}!")
                    time.sleep(0.5)
                    # Como salvamos st.session_state.aba_cadastro_ativa, ele voltará para cá!
                    st.rerun()
            st.divider()

    # --- ABA: CADASTRO MANUAL ---
    elif st.session_state.aba_cadastro_ativa == "➕ Cadastro Manual":
        st.subheader("Cadastrar Novo Aluno")
        with st.form("novo_aluno"):
            nome = st.text_input("Nome Completo")
            turma = st.text_input("Turma (Ex: 1º A)")
            if st.form_submit_button("Salvar Aluno"):
                if nome and turma:
                    supabase.table("alunos").insert({"nome": nome.upper(), "turma": turma.upper()}).execute()
                    st.success("Salvo com sucesso!")
                else:
                    st.warning("Preencha todos os campos.")

    # --- ABA: CONSULTA RÁPIDA ---
    elif st.session_state.aba_cadastro_ativa == "🔍 Consulta Rápida":
        st.subheader("Busca Geral")
        busca = st.text_input("Digite o nome do aluno:")
        if busca:
            res = supabase.table("alunos").select("*").ilike("nome", f"%{busca}%").execute()
            if res.data:
                st.dataframe(pd.DataFrame(res.data), use_container_width=True)
            else:
                st.info("Nenhum aluno encontrado.")