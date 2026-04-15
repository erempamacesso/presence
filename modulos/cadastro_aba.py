import streamlit as st
import pandas as pd
import unicodedata
import time
import re
from datetime import datetime

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
            # Ajustei a largura das colunas para caber a Matrícula
            h1, h2, h3, h4, h5, h6 = st.columns([1, 2, 1.5, 1.5, 1.5, 0.5])
            h1.write("**Foto**")
            h2.write("**Nome**")
            h3.write("**Matrícula (SIEPE)**")
            h4.write("**Turma**")
            h5.write("**Nova Foto**")
            h6.write("**Del**")

            for aluno in alunos:
                c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 1.5, 1.5, 1.5, 0.5])
                
                # C1: Visualização da Foto
                with c1:
                    chave = limpar_texto(aluno['nome'])
                    url = mapa_fotos.get(chave)
                    if url:
                        st.image(url, width=60)
                    else:
                        st.warning("⚠️") 
                
                # C2: Identificação (Nome + Data de Nascimento)
                with c2:
                    st.write(f"**{aluno['nome']}**")
                    dt_nasc = aluno.get('data_nascimento', 'Não informada')
                    st.caption(f"🎂 Nasc: {dt_nasc}")
                
                # C3: Inserção/Edição de Matrícula (SIEPE)
                with c3:
                    mat_atual = aluno.get('matricula') or ""
                    # O campo carrega vazio se não tiver, ou com o número atual se já tiver
                    nova_mat = st.text_input(
                        "Matrícula", value=mat_atual, 
                        key=f"mat_{aluno['id']}", label_visibility="collapsed", placeholder="Nº SIEPE"
                    )
                    # Só exibe o botão de salvar se o usuário digitar algo diferente do que está no banco
                    if nova_mat != mat_atual and nova_mat.strip() != "":
                        if st.button("💾 Salvar Matrícula", key=f"btn_mat_{aluno['id']}", use_container_width=True):
                            supabase.table("alunos").update({"matricula": nova_mat.strip()}).eq("id", aluno['id']).execute()
                            st.toast(f"Matrícula de {aluno['nome']} atualizada!")
                            time.sleep(0.5)
                            st.rerun()

                # C4: Troca de Turma
                with c4:
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
                
                # C5: Upload para GitHub
                with c5:
                    foto_up = st.file_uploader(
                        "Upload", type=['jpg', 'jpeg', 'png'], 
                        key=f"up_{aluno['id']}", label_visibility="collapsed"
                    )
                    if foto_up:
                        if st.button("💾 Enviar", key=f"btn_s_{aluno['id']}", use_container_width=True):
                            if salvar_foto_github(foto_up, aluno['nome']):
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                
                # C6: Exclusão (Delete)
                with c6:
                    with st.popover("🗑️"):
                        st.write("Confirmar exclusão?")
                        if st.button("Apagar", key=f"del_{aluno['id']}", type="primary"):
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
            
            # Novo campo para Data de Nascimento
            col_dt, col_mat = st.columns(2)
            with col_dt:
                dt_nascimento = st.date_input(
                    "Data de Nascimento", 
                    value=None, 
                    min_value=datetime(1980, 1, 1), 
                    max_value=datetime.today(),
                    format="DD/MM/YYYY"
                )
            with col_mat:
                matricula = st.text_input("Matrícula SIEPE (Opcional por agora)")

            if st.form_submit_button("Salvar Aluno"):
                if nome and turma:
                    # Prepara os dados para envio
                    dados_insert = {
                        "nome": nome.upper().strip(), 
                        "turma": turma.upper().strip()
                    }
                    # Adiciona os campos opcionais se foram preenchidos
                    if dt_nascimento:
                        dados_insert["data_nascimento"] = dt_nascimento.strftime('%Y-%m-%d')
                    if matricula:
                        dados_insert["matricula"] = matricula.strip()

                    try:
                        supabase.table("alunos").insert(dados_insert).execute()
                        st.success(f"Estudante {nome.upper()} salvo com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                else:
                    st.warning("Preencha pelo menos o Nome e a Turma.")

    # --- ABA: CONSULTA RÁPIDA ---
    elif st.session_state.aba_cadastro_ativa == "🔍 Consulta Rápida":
        st.subheader("Busca Geral")
        busca = st.text_input("Digite o nome do aluno ou matrícula:")
        
        if busca:
            res = None
            try:
                # 1ª Tentativa: Busca no nome e na matrícula (assumindo que matrícula é texto/string)
                res = supabase.table("alunos").select("*").or_(f"nome.ilike.%{busca}%,matricula.ilike.%{busca}%").execute()
            except Exception:
                # 2ª Tentativa: Se der erro (ex: matrícula é número ou não existe), busca SÓ pelo nome
                try:
                    res = supabase.table("alunos").select("*").ilike("nome", f"%{busca}%").execute()
                except Exception as e:
                    st.error(f"Erro interno de banco de dados. Verifique a tabela 'alunos'.")
            
           # Se conseguiu buscar com sucesso e tem dados
            if res and res.data:
                df = pd.DataFrame(res.data)
                
                # 1. Garante que as colunas existam
                if 'matricula' not in df.columns: df['matricula'] = "---"
                if 'data_nascimento' not in df.columns: df['data_nascimento'] = None
                
                # 2. CONVERSÃO DA DATA (Brasileira)
                # Transformamos em data e depois em texto formatado
                try:
                    df['data_nascimento'] = pd.to_datetime(df['data_nascimento']).dt.strftime('%d/%m/%Y')
                    # Se a data for nula, o pandas coloca 'NaT', vamos trocar por um traço
                    df['data_nascimento'] = df['data_nascimento'].replace('NaT/NaT/NaT', '---').fillna('---')
                except:
                    pass # Se falhar, mantém como está para não quebrar o app

                # 3. Exibe a tabela com as colunas na ordem certa
                st.dataframe(
                    df[['id', 'nome', 'matricula', 'turma', 'data_nascimento']], 
                    use_container_width=True, 
                    hide_index=True
                )
           

if __name__ == "__main__":
    pass