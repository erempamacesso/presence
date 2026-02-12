import streamlit as st
import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv
import unicodedata
import time

# ==================================================
# 1. CONFIGURAÇÃO
# ==================================================
st.set_page_config(page_title="Gestão Escolar", layout="wide")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("ERRO: Credenciais não encontradas.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==================================================
# 2. FUNÇÕES INTELIGENTES
# ==================================================
def limpar_texto(texto):
    """
    Limpa o texto para comparação agressiva.
    Ex: "João da Silva.png" -> "joaodasilva"
    Ex: "Joao_Silva" -> "joaodasilva"
    """
    if not texto: return ""
    # Remove extensão se houver (para processar nomes de arquivos)
    if "." in texto:
        texto = texto.rsplit(".", 1)[0]
    
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Remove espaços, underlines e deixa minúsculo
    return sem_acento.lower().replace(" ", "").replace("_", "").strip()

def listar_arquivos_bucket():
    """
    Lista TODOS os arquivos do bucket e cria um dicionário
    Chave: nome limpo (joaodasilva) -> Valor: nome real do arquivo (Joao Silva.jpg)
    """
    try:
        # Pega a lista de arquivos no bucket
        arquivos = supabase.storage.from_('fotos-alunos').list()
        mapa = {}
        for arq in arquivos:
            nome_real = arq['name']
            # Cria uma chave simplificada para facilitar o encontro
            chave = limpar_texto(nome_real)
            mapa[chave] = nome_real
        return mapa
    except Exception as e:
        st.error(f"Erro ao ler bucket: {e}")
        return {}

def get_foto_url(nome_real_arquivo):
    """Gera a URL pública baseada no nome REAL do arquivo encontrado"""
    try:
        url = supabase.storage.from_('fotos-alunos').get_public_url(nome_real_arquivo)
        return f"{url}?t={int(time.time())}" 
    except:
        return None

# ==================================================
# 3. INTERFACE
# ==================================================
st.title("🏫 Sistema de Gestão Escolar")

aba1, aba2, aba3 = st.tabs(["📤 Importação", "👤 Cadastro Manual", "📸 Turmas e Fotos"])

# --- ABA 1 (MANTIDA IGUAL) ---
with aba1:
    st.write("Importar planilha Excel ou CSV.")
    arquivo = st.file_uploader("Upload Arquivo", type=["csv", "xlsx"])
    if arquivo:
        if st.button("Processar Arquivo"):
            try:
                if arquivo.name.endswith('.csv'): df = pd.read_csv(arquivo)
                else: df = pd.read_excel(arquivo)
                df.columns = [c.lower().strip() for c in df.columns]
                count = 0
                for index, row in df.iterrows():
                    try:
                        nome = str(row['nome']).upper().strip()
                        turma = f"{row['serie']} {row['turma']}".strip()
                        existe = supabase.table("alunos").select("id").eq("nome", nome).execute()
                        if not existe.data:
                            supabase.table("alunos").insert({"nome": nome, "turma": turma}).execute()
                            count += 1
                    except: pass
                st.success(f"Processados: {count}")
            except Exception as e: st.error(f"Erro: {e}")

# --- ABA 2 (MANTIDA IGUAL) ---
with aba2:
    with st.form("form_manual", clear_on_submit=True):
        nome_man = st.text_input("Nome")
        turma_man = st.text_input("Turma")
        if st.form_submit_button("Cadastrar"):
            if nome_man and turma_man:
                supabase.table("alunos").insert({"nome": nome_man.upper(), "turma": turma_man.upper()}).execute()
                st.success("Salvo!")

# --- ABA 3: GESTÃO VISUAL INTELIGENTE ---
with aba3:
    st.header("Turmas e Alunos")

    # 1. Preparação
    res = supabase.table("alunos").select("turma").execute()
    lista_turmas = sorted(list(set([x['turma'] for x in res.data if x['turma']])))
    
    if not lista_turmas:
        st.warning("Sem turmas.")
        st.stop()

    turma_escolhida = st.selectbox("Selecione a Turma:", lista_turmas)
    
    # 2. Carrega Dados
    res_alunos = supabase.table("alunos").select("*").eq("turma", turma_escolhida).order("nome").execute()
    alunos = res_alunos.data

    # >>> A MÁGICA ACONTECE AQUI <<<
    # Carregamos a lista de arquivos REAIS do bucket uma única vez
    mapa_arquivos = listar_arquivos_bucket()

    st.markdown("---")
    c_h1, c_h2, c_h3 = st.columns([1, 4, 2])
    c_h1.write("**FOTO**")
    c_h2.write("**NOME**")
    c_h3.write("**MUDAR TURMA**")

    for aluno in alunos:
        st.divider()
        c1, c2, c3 = st.columns([1, 4, 2])
        uid = aluno['id']

        # --- COLUNA 1: FOTO INTELIGENTE ---
        with c1:
            # Limpa o nome do aluno para buscar no mapa
            # Ex: "Kaio Vinícius..." vira "kaiovinicius..."
            chave_busca = limpar_texto(aluno['nome'])
            
            # Verifica se existe algum arquivo com esse nome (seja jpg, png, jpeg...)
            nome_arquivo_real = mapa_arquivos.get(chave_busca)

            if nome_arquivo_real:
                url_img = get_foto_url(nome_arquivo_real)
                st.image(url_img, width=50)
            else:
                # Se não achou arquivo correspondente
                st.markdown("👤")

        # --- COLUNA 2 ---
        with c2:
            st.write("")
            st.write(f"**{aluno['nome']}**")
            # Debug opcional: descomente abaixo se ainda tiver erro para ver o que ele buscou
            # st.caption(f"Buscou por: {chave_busca}")

        # --- COLUNA 3 ---
        with c3:
            try: idx = lista_turmas.index(aluno['turma'])
            except: idx = 0
            
            nova = st.selectbox("Mudar", lista_turmas, index=idx, key=f"s_{uid}", label_visibility="collapsed")
            if nova != aluno['turma']:
                supabase.table("alunos").update({"turma": nova}).eq("id", uid).execute()
                st.toast("Atualizado!")
                time.sleep(1)
                st.rerun()