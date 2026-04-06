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
    """Busca as fotos no repositório GitHub"""
    try:
        from github import Github, Auth
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("🚨 GITHUB_TOKEN não configurado nos Secrets!")
            return {}
        
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence") 
        contents = repo.get_contents("alunos_fotos")
        
        return {limpar_texto(arq.name): arq.download_url for arq in contents}
    except Exception as e:
        st.error(f"Erro ao carregar fotos do GitHub: {e}")
        return {}

def salvar_foto_github(arquivo_upload, nome_aluno):
    """Faz o upload ou atualização da foto diretamente no repositório GitHub"""
    try:
        from github import Github, Auth
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        
        # Padroniza o nome do arquivo (ex: joaosilva.jpg)
        extensao = arquivo_upload.name.split('.')[-1]
        nome_arquivo = f"{limpar_texto(nome_aluno)}.{extensao}"
        caminho_github = f"alunos_fotos/{nome_arquivo}"
        conteudo = arquivo_upload.getvalue()
        
        try:
            # Tenta encontrar o arquivo para atualizar
            contents = repo.get_contents(caminho_github)
            repo.update_file(contents.path, f"📸 Atualizando foto: {nome_aluno}", conteudo, contents.sha)
            st.toast(f"Foto de {nome_aluno} atualizada!")
        except:
            # Se não existir, cria um novo
            repo.create_file(caminho_github, f"📸 Nova foto: {nome_aluno}", conteudo)
            st.toast(f"Nova foto de {nome_aluno} salva!")
        
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no GitHub: {e}")
        return False

# ==================================================
# 2. FUNÇÃO PRINCIPAL
# ==================================================
def exibir_cadastro(supabase):
    
    if 'aba_cadastro_ativa' not in st.session_state:
        st.session_state.aba_cadastro_ativa = "📸 Fotos e Turmas"

    st.title("👤 Gestão de Estudantes")

    opcoes = ["📸 Fotos e Turmas", "➕ Cadastro Manual", "🔍 Consulta Rápida"]
    escolha = st.segmented_control(
        "Selecione a funcionalidade:", 
        opcoes, 
        default=st.session_state.aba_cadastro_ativa,
        key="nav_interna_cadastro"
    )
    
    st.session_state.aba_cadastro_ativa = escolha
    st.divider()

    # --- ABA: FOTOS E TURMAS (GESTÃO COMPLETA) ---
    if st.session_state.aba_cadastro_ativa == "📸 Fotos e Turmas":
        st.subheader("Gestão Visual e Atualização")
        
        # 1. Obter turmas
        res_t = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([x['turma'] for x in res_t.data if x['turma']])))
        
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            turma_sel = st.selectbox("Filtrar por Turma:", lista_turmas)
        with col_t2:
            if st.button("🔄 Atualizar Dados/Fotos", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        # 2. Buscar Alunos e Mapa de Fotos
        mapa_fotos = buscar_fotos_github_cadastro()
        res_alunos = supabase.table("alunos").select("*").eq("turma", turma_sel).order("nome").execute()
        alunos = res_alunos.data

        if not alunos:
            st.info("Nenhum aluno encontrado nesta turma.")
        else:
            # Cabeçalho da Tabela
            st.markdown("---")
            h1, h2, h3, h4, h5 = st.columns([1, 2.5, 1.5, 2, 0.5])
            h1.write("**Foto**")
            h2.write("**Nome**")
            h3.write("**Turma**")
            h4.write("**Nova Foto**")
            h5.write("**Excluir**")

            for aluno in alunos:
                c1, c2, c3, c4, c5 = st.columns([1, 2.5, 1.5, 2, 0.5])
                
                # C1: Visualização da Foto
                with c1:
                    chave = limpar_texto(aluno['nome'])
                    url = mapa_fotos.get(chave)
                    if url:
                        st.image(url, width=60)
                    else:
                        st.warning("⚠️") # Alerta visual de falta de foto
                
                # C2: Identificação
                with c2:
                    st.write(f"**{aluno['nome']}**")
                    st.caption(f"ID: {aluno['id']}")
                
                # C3: Troca de Turma
                with c3:
                    try: idx_atual = lista_turmas.index(aluno['turma'])
                    except: idx_atual = 0
                    
                    nova_t = st.selectbox(
                        "Mudar", lista_turmas, index=idx_atual, 
                        key=f"t_{aluno['id']}", label_visibility="collapsed"
                    )
                    
                    if nova_t != aluno['turma']:
                        supabase.table("alunos").update({"turma": nova_t}).eq("id", aluno['id']).execute()
                        st.toast(f"Turma de {aluno['nome']} alterada!")
                        time.sleep(0.5)
                        st.rerun()
                
                # C4: Upload para GitHub
                with c4:
                    foto_up = st.file_uploader(
                        "Upload", type=['jpg', 'jpeg', 'png'], 
                        key=f"up_{aluno['id']}", label_visibility="collapsed"
                    )
                    if foto_up:
                        if st.button("💾 Salvar", key=f"btn_s_{aluno['id']}", use_container_width=True):
                            if salvar_foto_github(foto_up, aluno['nome']):
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                
                # C5: Exclusão (Delete)
                with c5:
                    with st.popover("🗑️"):
                        st.write("Confirmar exclusão?")
                        if st.button("Sim, apagar", key=f"del_{aluno['id']}", type="primary"):
                            supabase.table("alunos").delete().eq("id", aluno['id']).execute()
                            st.toast("Aluno removido!")
                            time.sleep(0.5)
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
                    st.cache_data.clear()
                else:
                    st.warning("Preencha todos os campos.")

    # --- ABA: CONSULTA RÁPIDA ---
    elif st.session_state.aba_cadastro_ativa == "🔍 Consulta Rápida":
        st.subheader("Busca Geral")
        busca = st.text_input("Digite o nome do aluno:")
        if busca:
            res = supabase.table("alunos").select("*").ilike("nome", f"%{busca}%").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df[['id', 'nome', 'turma']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum aluno encontrado.")