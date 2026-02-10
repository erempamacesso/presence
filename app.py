import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time

# ==================================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==================================================
st.set_page_config(page_title="Gestão Escolar", layout="wide")

# Tenta carregar do arquivo .env (local) ou dos Segredos do Streamlit (nuvem)
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

# Trava de segurança se não tiver senha
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO CRÍTICO: Credenciais do Supabase não encontradas. Configure os 'Secrets' no Streamlit Cloud.")
    st.stop()

# Conecta ao banco
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Erro ao conectar no Supabase: {e}")
    st.stop()

# ==================================================
# 2. FUNÇÕES INTELIGENTES (Lógica de Arquivos)
# ==================================================
def limpar_texto(texto):
    """
    Remove acentos, espaços e deixa minúsculo para facilitar a busca.
    Ex: "João da Silva.jpg" -> "joaodasilva"
    """
    if not texto: return ""
    texto = str(texto)
    # Se tiver extensão de arquivo, remove
    if "." in texto:
        texto = texto.rsplit(".", 1)[0]
    
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

def listar_arquivos_bucket():
    """
    Busca TODOS os arquivos da pasta 'fotos-alunos' de uma vez.
    Retorna um dicionário: {'joaodasilva': 'Joao Da Silva.jpg'}
    Isso evita erros de extensão (png/jpg) e formatação.
    """
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list()
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq['name']
                # Ignora arquivos de sistema
                if nome_real == ".emptyFolderPlaceholder": continue
                
                chave = limpar_texto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except Exception as e:
        # Se der erro, retorna vazio mas não trava o app
        print(f"Erro bucket: {e}")
        return {}

def get_foto_url(nome_real_arquivo):
    """Gera o link público da foto"""
    try:
        url = supabase.storage.from_('fotos-alunos').get_public_url(nome_real_arquivo)
        # Adiciona timestamp para atualizar a imagem se ela mudar e evitar cache
        return f"{url}?t={int(time.time())}" 
    except:
        return None

# ==================================================
# 3. INTERFACE DO USUÁRIO
# ==================================================
st.title("🏫 Sistema de Gestão Escolar")

# Abas de navegação
aba1, aba2, aba3 = st.tabs(["📤 Importação em Massa", "👤 Cadastro Manual", "📸 Mapa de Sala (Gestão)"])

# --------------------------------------------------
# ABA 1: IMPORTAÇÃO
# --------------------------------------------------
with aba1:
    st.write("### Importar planilha (Excel ou CSV)")
    st.info("Colunas necessárias: **Nome**, **Turma** (ou Serie + Turma)")
    
    arquivo = st.file_uploader("Upload Arquivo", type=["csv", "xlsx"])
    
    if arquivo: 
        if st.button("Processar Arquivo"):
            try:
                if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo)
                else: df = pd.read_excel(arquivo)
                
                # Normaliza cabeçalhos para minúsculo
                df.columns = [str(c).lower().strip() for c in df.columns]
                
                count = 0
                # Barra de progresso visual
                barra = st.progress(0)
                total = len(df)
                
                for index, row in df.iterrows():
                    # Atualiza barra
                    if total > 0: barra.progress((index + 1) / total)
                    
                    try:
                        nome = str(row['nome']).upper().strip()
                        
                        # Tenta montar a turma de formas diferentes
                        turma_final = ""
                        if 'turma' in df.columns and 'serie' in df.columns:
                            turma_final = f"{row['serie']} {row['turma']}".strip()
                        elif 'turma' in df.columns:
                            turma_final = str(row['turma']).strip()
                        else:
                            turma_final = "SEM TURMA"

                        # Verifica se já existe para não duplicar
                        existe = supabase.table("alunos").select("id").eq("nome", nome).execute()
                        if not existe.data:
                            supabase.table("alunos").insert({
                                "nome": nome, 
                                "turma": turma_final
                            }).execute()
                            count += 1
                    except: pass
                
                st.success(f"✅ Processamento concluído! {count} novos alunos importados.")
                time.sleep(2)
                st.rerun() # Atualiza a tela
            except Exception as e: 
                st.error(f"Erro ao ler arquivo: {e}")

# --------------------------------------------------
# ABA 2: CADASTRO MANUAL
# --------------------------------------------------
with aba2:
    st.write("### Cadastro Individual")
    with st.form("form_manual", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            nome_man = st.text_input("Nome Completo")
        with col_b:
            turma_man = st.text_input("Turma (Ex: 1º A)")
            
        if st.form_submit_button("Cadastrar Aluno"):
            if nome_man and turma_man:
                try:
                    supabase.table("alunos").insert({
                        "nome": nome_man.upper(), 
                        "turma": turma_man.upper()
                    }).execute()
                    st.success(f"Aluno {nome_man} salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Preencha todos os campos.")

# --------------------------------------------------
# ABA 3: MAPA DE SALA (GESTÃO)
# --------------------------------------------------
with aba3:
    st.header("Visualização de Turmas")

    # 1. Carregar lista de turmas disponíveis
    try:
        res = supabase.table("alunos").select("turma").execute()
        # Cria lista única, remove vazios e ordena
        lista_turmas = sorted(list(set([x['turma'] for x in res.data if x.get('turma')])))
        
        if not lista_turmas:
            st.warning("Nenhuma turma encontrada. Cadastre alunos primeiro.")
            st.stop()
    except Exception as e:
        st.error("Erro ao buscar turmas. Verifique a conexão.")
        st.stop()

    # Dropdown de seleção
    turma_escolhida = st.selectbox("Selecione a Turma:", lista_turmas)
    
    # 2. Busca Alunos da turma
    res_alunos = supabase.table("alunos").select("*").eq("turma", turma_escolhida).order("nome").execute()
    alunos = res_alunos.data

    # 3. Carrega o mapa de arquivos (MÁGICA ACONTECE AQUI)
    mapa_arquivos = listar_arquivos_bucket()

    st.markdown("---")
    
    # Cabeçalho da Tabela Visual
    c_h1, c_h2, c_h3 = st.columns([1, 4, 2])
    c_h1.write("**FOTO**")
    c_h2.write("**NOME**")
    c_h3.write("**AÇÃO**")

    # Loop dos Alunos
    if not alunos:
        st.info("Nenhum aluno nesta turma.")
    else:
        for aluno in alunos:
            st.divider()
            c1, c2, c3 = st.columns([1, 4, 2])
            uid = aluno['id']

            # --- COLUNA FOTO ---
            with c1:
                # Cria a chave de busca (ex: kaio -> kaio)
                chave_busca = limpar_texto(aluno['nome'])
                # Tenta achar o nome real do arquivo no mapa
                nome_arquivo_real = mapa_arquivos.get(chave_busca)
                
                if nome_arquivo_real:
                    url_img = get_foto_url(nome_arquivo_real)
                    st.image(url_img, width=60)
                else:
                    # Se não achar foto, mostra um ícone
                    st.markdown("👤")

            # --- COLUNA NOME ---
            with c2:
                st.write("") # Espaço vertical
                st.write(f"**{aluno['nome']}**")

            # --- COLUNA AÇÃO (MUDAR TURMA) ---
            with c3:
                try: idx = lista_turmas.index(aluno['turma'])
                except: idx = 0
                
                # Dropdown para mudar de turma na hora
                nova_turma = st.selectbox(
                    "Mudar Turma", 
                    lista_turmas, 
                    index=idx, 
                    key=f"sel_{uid}", 
                    label_visibility="collapsed"
                )
                
                if nova_turma != aluno['turma']:
                    supabase.table("alunos").update({"turma": nova_turma}).eq("id", uid).execute()
                    st.toast(f"✅ {aluno['nome']} movido para {nova_turma}!")
                    time.sleep(1)
                    st.rerun()
