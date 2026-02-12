import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import time
import unicodedata
from urllib.parse import quote

# ==================================================
# 1. CONFIGURAÇÃO VISUAL (APP MODE)
# ==================================================
st.set_page_config(page_title="Chamada", page_icon="📱", layout="centered")

# CSS PERSONALIZADO PARA ESTILO "MOBILE REACT"
st.markdown("""
    <style>
        /* Remove padding do topo para ganhar espaço */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Estilo do Card do Aluno (Linha) */
        .aluno-row {
            display: flex;
            align-items: center;
            background-color: white;
            padding: 8px 10px;
            border-bottom: 1px solid #f0f0f0;
            margin-bottom: 2px;
            border-radius: 8px;
        }
        
        /* Foto redonda pequena */
        .profile-pic {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #e0e0e0;
            margin-right: 12px;
        }
        
        /* Nome do aluno */
        .aluno-name {
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: #333;
            flex-grow: 1; /* Empurra o botão para a direita */
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis; /* Três pontinhos se nome for longo */
            margin-right: 10px;
        }
        
        /* Ajuste fino nos botões do Streamlit para parecerem Tags */
        .stButton > button {
            border-radius: 20px !important;
            padding: 4px 12px !important;
            font-size: 12px !important;
            font-weight: bold !important;
            border: none !important;
            height: auto !important;
            min-height: 0px !important;
            line-height: 1.5 !important;
        }
        
        /* Esconde elementos desnecessários */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Botão Flutuante de Salvar (Sticky Footer) */
        .floating-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background-color: white;
            padding: 10px 20px;
            box-shadow: 0px -4px 10px rgba(0,0,0,0.1);
            z-index: 999;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# ==================================================
# 2. CONEXÃO E FUNÇÕES
# ==================================================
load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL: st.stop()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funções de Imagem (Copiadas do app.py para funcionar aqui) ---
def limpar_texto(texto):
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=3600) # Cache para não ficar lento carregando fotos
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        mapa = {}
        if arquivos:
            for arq in arquivos:
                nome_real = arq.get('name') if isinstance(arq, dict) else getattr(arq, 'name', '')
                if not nome_real or nome_real == ".emptyFolderPlaceholder": continue
                chave = limpar_texto(nome_real)
                mapa[chave] = nome_real
        return mapa
    except: return {}

def get_foto_url(nome_real_arquivo):
    try:
        path_seguro = quote(nome_real_arquivo)
        url_base = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{path_seguro}"
        return f"{url_base}?t={int(time.time())}"
    except: return "https://cdn-icons-png.flaticon.com/512/847/847969.png" # Avatar padrão

# ==================================================
# 3. LÓGICA DE SENHAS
# ==================================================
SENHAS_TURMAS = {
    "1A": "1010", "1B": "1020", "1C": "1030", "1D": "1040", "1E": "1050",
    "2A": "2010", "2B": "2020", "2C": "2030", "2D": "2040",
    "3A": "3010", "3B": "3020", "3C": "3030", "3D": "3040"
}

# ==================================================
# 4. INÍCIO DA INTERFACE
# ==================================================
params = st.query_params
turma_url = params.get("turma", None)

if not turma_url:
    st.error("Link inválido.")
    st.stop()

turma_limpa = turma_url.upper().replace(" ", "").strip()
turma_chave_senha = turma_limpa.replace("º", "")

# --- Tela de Login Simples ---
if 'acesso_liberado' not in st.session_state:
    st.session_state['acesso_liberado'] = False

if not st.session_state['acesso_liberado']:
    st.markdown(f"<h3 style='text-align:center'>🔐 Turma {turma_chave_senha}</h3>", unsafe_allow_html=True)
    senha = st.text_input("PIN de Acesso", type="password", label_visibility="collapsed", placeholder="Digite o PIN da turma")
    
    if len(senha) == 4:
        if senha == SENHAS_TURMAS.get(turma_chave_senha):
            st.session_state['acesso_liberado'] = True
            st.rerun()
        else:
            st.toast("PIN Incorreto!", icon="🚫")
    st.stop()

# ==================================================
# 5. TELA DE CHAMADA (ESTILO MOBILE)
# ==================================================

# --- Busca Dados (Cacheado) ---
@st.cache_data(ttl=60)
def buscar_alunos(turma_chave):
    numero = turma_chave[0]
    letra = turma_chave[1:]
    formatos = [f"{numero}º {letra}", f"{numero}º{letra}", f"{numero} {letra}", turma_chave]
    
    for fmt in formatos:
        res = supabase.table("alunos").select("id, nome, turma").eq("turma", fmt).order("nome").execute()
        if res.data: return res.data, fmt
    return [], ""

alunos_data, turma_db = buscar_alunos(turma_chave_senha)
mapa_fotos = listar_arquivos_bucket()

if not alunos_data:
    st.warning("Nenhum aluno encontrado.")
    st.stop()

# --- Cabeçalho Compacto ---
col_head1, col_head2 = st.columns([4,1])
with col_head1:
    st.markdown(f"**{turma_db}** • {datetime.now().strftime('%d/%m')}", unsafe_allow_html=True)
with col_head2:
    if st.button("Sair"):
        st.session_state['acesso_liberado'] = False
        st.rerun()

st.progress(100) # Linha decorativa

# --- Inicializa Estado da Chamada ---
if 'chamada_state' not in st.session_state:
    st.session_state['chamada_state'] = {aluno['id']: True for aluno in alunos_data} # True = Presente

# --- LISTA DE ALUNOS (LAYOUT REACT-LIKE) ---
# Aqui usamos colunas nativas do Streamlit com CSS injetado para ficar compacto
with st.container():
    for aluno in alunos_data:
        # Define cor e texto baseado no estado
        is_presente = st.session_state['chamada_state'][aluno['id']]
        
        # URL da Foto
        chave_foto = limpar_texto(aluno['nome'])
        url_foto = get_foto_url(mapa_fotos.get(chave_foto)) if mapa_fotos.get(chave_foto) else "https://cdn-icons-png.flaticon.com/512/1077/1077114.png"
        
        # CRIAÇÃO DA LINHA VISUAL
        # Usamos colunas: [Foto] [Nome] [Botão]
        c1, c2, c3 = st.columns([1.2, 5, 2.5], gap="small", vertical_alignment="center")
        
        with c1:
            st.markdown(f'<img src="{url_foto}" class="profile-pic">', unsafe_allow_html=True)
        
        with c2:
            # Nome com cor diferente se faltou
            cor_nome = "#000" if is_presente else "#999"
            st.markdown(f"<span style='color:{cor_nome}; font-weight:600; font-size:14px;'>{aluno['nome']}</span>", unsafe_allow_html=True)
        
        with c3:
            # Lógica do Botão Toggle
            # Se apertar, inverte o estado e dá rerun
            label_btn = "PRESENTE" if is_presente else "AUSENTE"
            type_btn = "primary" if not is_presente else "secondary" # Primary geralmente é vermelho no tema padrao
            
            # Truque visual: Botão verde vs vermelho
            # Streamlit não deixa mudar cor hex do botão fácil, então usamos Emojis e Texto
            texto_botao = "✅ PRESENTE" if is_presente else "🔻 AUSENTE"
            
            if st.button(texto_botao, key=f"btn_{aluno['id']}", use_container_width=True):
                st.session_state['chamada_state'][aluno['id']] = not st.session_state['chamada_state'][aluno['id']]
                st.rerun()
        
        # Divisor fino
        st.markdown("<div style='border-bottom: 1px solid #eee; margin-bottom: 4px;'></div>", unsafe_allow_html=True)

# --- ESPAÇO EXTRA PARA O FOOTER NÃO COBRIR O ÚLTIMO ALUNO ---
st.write("")
st.write("")
st.write("")

# --- BARRA FLUTUANTE DE SALVAR (FIXA NO RODAPÉ) ---
# Usamos um container vazio para injetar HTML ou um form fixo
with st.container():
    st.markdown('<div class="floating-footer">', unsafe_allow_html=True)
    
    # Botão de Salvar Real
    if st.button("🚀 ENVIAR CHAMADA", type="primary", use_container_width=True):
        fuso = pytz.timezone('America/Recife')
        data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
        
        lista_envio = []
        qtd_p = 0
        qtd_f = 0
        
        for aluno in alunos_data:
            status_bool = st.session_state['chamada_state'][aluno['id']]
            status_str = "P" if status_bool else "F"
            if status_bool: qtd_p += 1
            else: qtd_f += 1
            
            lista_envio.append({
                "turma": turma_db,
                "aluno_nome": aluno['nome'],
                "status": status_str,
                "data_chamada": data_hoje
            })
            
        try:
            supabase.table("frequencia").delete().match({"turma": turma_db, "data_chamada": data_hoje}).execute()
            supabase.table("frequencia").insert(lista_envio).execute()
            st.toast(f"Sucesso! {qtd_p} Presentes / {qtd_f} Faltas", icon="✅")
            time.sleep(2)
        except Exception as e:
            st.error(f"Erro: {e}")
            
    st.markdown('</div>', unsafe_allow_html=True)
