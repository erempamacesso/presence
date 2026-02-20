import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime
import pytz
import unicodedata
import time
from urllib.parse import quote

# 1. Configuração e Conexão
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="wide")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Estilização para fotos grandes e cards
st.markdown("""
    <style>
        .aluno-card {
            border: 1px solid #ddd; padding: 10px; border-radius: 15px;
            background-color: #fcfcfc; text-align: center; margin-bottom: 15px;
        }
        .stCheckbox { font-size: 18px; font-weight: bold; }
        img { border-radius: 10px; border: 2px solid #ff4b4b; object-fit: cover; }
        .nome-chamada { font-weight: bold; font-size: 1.1rem; color: #333; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. MAPA DE MÁSCARA (CORRIGIDO PARA O SEU BANCO) ---
# Aqui os códigos apontam para o nome exato da coluna 'turma' no seu Supabase
MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

# 3. Pega o Token pela URL (ex: ?t=9f1a)
params = st.query_params
token_url = params.get("t", None)

def limpar_texto(texto):
    if not texto: return ""
    # Remove extensão se houver e normaliza acentos
    nfkd = unicodedata.normalize('NFKD', str(texto).split(".")[0])
    # Remove espaços e caracteres especiais para bater com o padrão de fotos
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower().replace(" ", "").strip()

if token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📝 Chamada: {turma_real}")
    
    # 4. Busca alunos da turma
    try:
        # A busca agora usa o nome exato: "1º A", "1º B", etc.
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error("Erro ao conectar com o banco de dados."); st.stop()

    if not alunos:
        st.warning(f"Nenhuma lista encontrada para a turma '{turma_real}'. Verifique o nome no banco de dados.")
    else:
        with st.form("form_chamada", clear_on_submit=False):
            fuso = pytz.timezone('America/Recife')
            data_hoje = datetime.now(fuso).strftime('%Y-%m-%d')
            st.info(f"📅 **Data:** {datetime.now(fuso).strftime('%d/%m/%Y')}")
            
            presencas = {}
            cache_buster = int(time.time()) # Garante que a foto atualize
            
            # 5. LAYOUT DE FOTOS GRANDES (2 colunas para mobile)
            cols = st.columns(2)
            
            for i, aluno in enumerate(alunos):
                with cols[i % 2]:
                    st.markdown('<div class="aluno-card">', unsafe_allow_html=True)
                    
                    # Lógica da Foto: nome do aluno sem espaços e minúsculo
                    nome_limpo = limpar_texto(aluno['nome'])
                    url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_limpo)}.jpg?t={cache_buster}"
                    
                    # Mostra a foto (se não existir, mostra o padrão)
                    st.image(url_foto, use_container_width=True)
                    
                    st.markdown(f"<div class='nome-chamada'>{aluno['nome'].split()[0]}</div>", unsafe_allow_html=True)
                    
                    # Checkbox (Marcado por padrão = Presente)
                    presencas[aluno['nome']] = st.checkbox("Presente", value=True, key=f"check_{i}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)

            st.divider()
            enviar = st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True)
            
            if enviar:
                dados_enviar = []
                for nome, presente in presencas.items():
                    dados_enviar.append({
                        "turma": turma_real,
                        "aluno_nome": nome,
                        "status": "P" if presente else "F",
                        "data_chamada": data_hoje
                    })
                
                try:
                    # Deleta chamada antiga do dia e insere a nova
                    supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                    supabase.table("frequencia").insert(dados_enviar).execute()
                    st.success("✅ Chamada enviada com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar no banco: {e}")
else:
    st.error("🚫 Acesso não autorizado.")
    st.info("Por favor, utilize o QR Code oficial da sua turma para acessar a chamada.")
