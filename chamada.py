import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime, time as dt_time
import pytz
import unicodedata
import time
from urllib.parse import quote

# ==========================================
# 1. CONFIGURAÇÃO, CONEXÃO E CSS
# ==========================================
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="centered")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ESTILIZAÇÃO PARA LISTA HORIZONTAL ---
st.markdown("""
    <style>
        .aluno-row {
            display: flex;
            align-items: center;
            background-color: white;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #eee;
            margin-bottom: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .foto-container { flex: 0 0 60px; margin-right: 15px; }
        .foto-container img { width: 60px; height: 60px; border-radius: 50%; object-fit: cover; border: 2px solid #ff4b4b; }
        .info-container { flex-grow: 1; }
        .nome-aluno { font-weight: bold; font-size: 14px; color: #333; text-transform: uppercase; }
        /* Ajuste para o Checkbox parecer um botão */
        .stCheckbox { background-color: #e8f5e9; padding: 5px 10px; border-radius: 8px; border: 1px solid #2e7d32; }
    </style>
""", unsafe_allow_html=True)

MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

def limpar_texto_absoluto(texto):
    if not texto: return ""
    texto = str(texto)
    if "." in texto: texto = texto.rsplit(".", 1)[0]
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return sem_acento.lower().replace(" ", "").replace("_", "").replace("-", "").strip()

@st.cache_data(ttl=300)
def listar_arquivos_bucket():
    try:
        arquivos = supabase.storage.from_('fotos-alunos').list(path=None, options={'limit': 5000})
        return {limpar_texto_absoluto(arq.get('name')): arq.get('name') for arq in arquivos if arq.get('name')}
    except: return {}

# ==========================================
# 2. FUNÇÃO DE DETECÇÃO DE HORÁRIOS
# ==========================================
def descobrir_aula_atual(hora_agora):
    """Lógica de horários com uma aula noturna para testes"""
    if hora_agora < dt_time(7, 30): return "Pré-aula"
    elif hora_agora < dt_time(8, 20): return "1º Aula"
    elif hora_agora < dt_time(9, 10): return "2º Aula"
    elif hora_agora < dt_time(9, 30): return "Intervalo (Manhã)"
    elif hora_agora < dt_time(10, 20): return "3º Aula"
    elif hora_agora < dt_time(11, 10): return "4º Aula"
    elif hora_agora < dt_time(12, 00): return "5º Aula"
    elif hora_agora < dt_time(13, 20): return "Intervalo (Almoço)"
    elif hora_agora < dt_time(14, 10): return "6º Aula"
    elif hora_agora < dt_time(15, 00): return "7º Aula"
    elif hora_agora < dt_time(15, 20): return "Intervalo (Tarde)"
    elif hora_agora < dt_time(16, 00): return "8º Aula"
    elif hora_agora < dt_time(16, 40): return "9º Aula"
    # --- HORÁRIO FAKE PARA TESTE AGORA (DAS 19H ÀS 23H) ---
    elif hora_agora < dt_time(23, 00): return "Aula Noturna (Teste)" 
    else: return "Encerrado"

# ==========================================
# 3. CAPTURA DO LINK (BLINDADA)
# ==========================================
token_url = None

try:
    if "t" in st.query_params:
        raw_token = st.query_params["t"]
        if isinstance(raw_token, list): token_url = str(raw_token[0]).lower().strip()
        else: token_url = str(raw_token).lower().strip()
except Exception as e:
    try:
        params = st.experimental_get_query_params()
        if "t" in params: token_url = str(params["t"][0]).lower().strip()
    except: pass

# ==========================================
# 4. APLICATIVO PRINCIPAL E ABAS
# ==========================================
if token_url and token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📱 Painel: {turma_real}")
    
    mapa_fotos = listar_arquivos_bucket()
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    data_hoje = agora.strftime('%Y-%m-%d')
    hora_atual = agora.time()
    
    st.caption(f"📅 {agora.strftime('%d/%m/%Y')} | ⏰ {agora.strftime('%H:%M')}")
    
    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except:
        st.error("Erro no banco."); st.stop()

    if alunos:
        # CRIAÇÃO DAS ABAS
        tab1, tab2 = st.tabs(["📝 Chamada Manhã", "🏃 Registro de Evasão"])
        cache_buster = int(time.time())

        # ====================================================================
        # BLOCO INÍCIO - ABA 1: CHAMADA MATINAL (SEU CÓDIGO ORIGINAL INTACTO)
        # ====================================================================
        with tab1:
            presencas_salvas = {}
            try:
                res_chamada_hoje = supabase.table("frequencia").select("aluno_nome, status").eq("turma", turma_real).eq("data_chamada", data_hoje).execute()
                if res_chamada_hoje.data:
                    presencas_salvas = {registro['aluno_nome']: registro['status'] for registro in res_chamada_hoje.data}
            except: pass

            with st.form("form_chamada"):
                presencas = {}
                
                for i, aluno in enumerate(alunos):
                    col_foto, col_nome, col_check = st.columns([1, 3, 2])
                    
                    chave_aluno = limpar_texto_absoluto(aluno['nome'])
                    nome_arq = mapa_fotos.get(chave_aluno)
                    
                    with col_foto:
                        if nome_arq:
                            url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cache_buster}"
                            st.image(url_foto, width=60)
                        else:
                            st.image("https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png", width=60)
                    
                    with col_nome:
                        st.markdown(f"<div style='padding-top:15px'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                    
                    with col_check:
                        st.write("") # Espaçador
                        status_atual = presencas_salvas.get(aluno['nome'])
                        marcado = False if status_atual == "F" else True
                        presencas[aluno['nome']] = st.checkbox("Presente", value=marcado, key=f"c_{i}")

                st.markdown("---")
                if st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True):
                    dados = [{"turma": turma_real, "aluno_nome": n, "status": "P" if p else "F", "data_chamada": data_hoje} for n, p in presencas.items()]
                    try:
                        supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                        supabase.table("frequencia").insert(dados).execute()
                        st.success("Chamada salva/atualizada com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
        # ====================================================================
        # BLOCO FIM - ABA 1
        # ====================================================================


        # ====================================================================
        # BLOCO INÍCIO - ABA 2: REGISTRO DE EVASÃO
        # ====================================================================
        with tab2:
            st.write("Registre os alunos que saíram de sala sem autorização.")
            aula_sug = descobrir_aula_atual(hora_atual)
            
            # Adicionei a Aula Teste na lista para o Selectbox não dar erro
            lista_aulas = ["1º Aula", "2º Aula", "3º Aula", "4º Aula", "5º Aula", "6º Aula", "7º Aula", "8º Aula", "9º Aula", "Aula Noturna (Teste)"]
            
            if "Intervalo" in aula_sug or "Encerrado" in aula_sug:
                st.warning(f"⏰ Status atual: {aula_sug}.")
                idx_aula = 0
            else:
                idx_aula = lista_aulas.index(aula_sug) if aula_sug in lista_aulas else 0

            aula_sel = st.selectbox("Selecione a Aula:", lista_aulas, index=idx_aula)
            
            # Busca quem já foi marcado nesta aula hoje
            try:
                res_evasoes = supabase.table("evasoes").select("aluno_nome").eq("data_registro", data_hoje).eq("aula_periodo", aula_sel).eq("turma", turma_real).execute()
                fugoes = [r['aluno_nome'] for r in res_evasoes.data] if res_evasoes.data else []
            except: fugoes = []

            for i, aluno in enumerate(alunos):
                c1, c2, c3 = st.columns([1, 3, 2])
                
                # Mesma lógica exata de imagem da Aba 1
                chave_aluno = limpar_texto_absoluto(aluno['nome'])
                nome_arq = mapa_fotos.get(chave_aluno)
                
                with c1: 
                    if nome_arq:
                        url_foto = f"{SUPABASE_URL}/storage/v1/object/public/fotos-alunos/{quote(nome_arq)}?t={cache_buster}"
                        st.image(url_foto, width=50)
                    else:
                        st.image("https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png", width=50)

                with c2: 
                    st.markdown(f"<div style='padding-top:10px'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                
                with c3:
                    if aluno['nome'] in fugoes:
                        st.error("🚨 Ausente")
                    else:
                        if st.button("🏃 Registrar", key=f"fuga_{i}", use_container_width=True):
                            try:
                                supabase.table("evasoes").insert({
                                    "data_registro": data_hoje, 
                                    "turma": turma_real, 
                                    "aluno_nome": aluno['nome'], 
                                    "aula_periodo": aula_sel
                                }).execute()
                                st.toast(f"Registro efetuado para {aluno['nome']}")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error("Erro ao registrar no banco.")
        # ====================================================================
        # BLOCO FIM - ABA 2
        # ====================================================================

    else:
        st.info(f"Nenhum aluno encontrado na turma {turma_real} no banco de dados.")
else:
    st.error("🚫 Use o QR Code da sala.")
    if token_url:
        st.warning(f"⚠️ Link não reconhecido: '{token_url}'")
