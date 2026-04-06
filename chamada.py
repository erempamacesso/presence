import streamlit as st
from supabase import create_client, Client
from datetime import datetime, time as dt_time
import pytz
import unicodedata
import time

# ==========================================
# 1. CONFIGURAÇÃO E CONEXÃO
# ==========================================
st.set_page_config(page_title="Chamada Digital EREMPAM", layout="centered")

try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL_ALUNOS", st.secrets.get("SUPABASE_URL"))
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY_ALUNOS", st.secrets.get("SUPABASE_KEY"))
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("🚨 Chaves de conexão não encontradas no secrets.toml.")
        st.stop()
        
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"🚨 Erro de conexão: {e}")
    st.stop()

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
        .aluno-row { display: flex; align-items: center; background-color: white; padding: 10px; border-radius: 12px; margin-bottom: 8px; }
        .nome-aluno { font-weight: bold; font-size: 14px; color: #333; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

MAPA_TURMAS = {
    "9f1a": "1º A", "2b3c": "1º B", "m5n6": "1º C", "d4r1": "1º D", "e5s2": "1º E",
    "x7y8": "2º A", "j1k2": "2º B", "p7q8": "2º C", "z8x9": "2º D",
    "k4m2": "3º A", "w3v4": "3º B", "r9s0": "3º C", "y2w1": "3º D"
}

def limpar_texto_absoluto(texto):
    if not texto: return ""
    if "." in str(texto): texto = str(texto).rsplit('.', 1)[0]
    texto = str(texto).strip().lower()
    nfkd = unicodedata.normalize('NFKD', texto)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return "".join(filter(str.isalnum, sem_acento))

# 👇 A MESMA FUNÇÃO PERFEITA DO FOTOGRAMA
@st.cache_data(ttl=3600)
def listar_fotos_github():
    try:
        import github
        from github import Github, Auth
        
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("🚨 ERRO: 'GITHUB_TOKEN' não configurado nos secrets!")
            return {}
            
        auth = Auth.Token(st.secrets["GITHUB_TOKEN"])
        g = Github(auth=auth)
        repo = g.get_repo("erempamacesso/presence")
        contents = repo.get_contents("alunos_fotos")
        
        # Retorna um dicionário: {'nome_limpo': 'url_direta'}
        return {limpar_texto_absoluto(arq.name): arq.download_url for arq in contents}
        
    except ImportError:
        st.error("🚨 ERRO: A biblioteca 'PyGithub' não está instalada! Rode 'pip install PyGithub'.")
        return {}
    except Exception as e:
        st.error(f"🚨 ERRO na conexão com GitHub: {e}")
        return {}

def descobrir_aula_atual(hora_agora):
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
    else: return "Encerrado"

# ==========================================
# 2. LÓGICA DO APLICATIVO
# ==========================================
token_url = st.query_params.get("t", None)
if isinstance(token_url, list): token_url = token_url[0]

if token_url and token_url in MAPA_TURMAS:
    turma_real = MAPA_TURMAS[token_url]
    st.title(f"📱 Painel: {turma_real}")
    
    # --- BUSCA AS FOTOS COM A FUNÇÃO NOVA ---
    mapa_fotos = listar_fotos_github()  
    
    fuso = pytz.timezone('America/Recife')
    agora = datetime.now(fuso)
    data_hoje = agora.strftime('%Y-%m-%d')
    hora_atual = dt_time(agora.hour, agora.minute) 

    st.info(f"🕒 **Relógio do Sistema:** {agora.strftime('%H:%M')} | **Data:** {agora.strftime('%d/%m/%Y')}")

    try:
        response = supabase.table("alunos").select("nome").eq("turma", turma_real).order("nome").execute()
        alunos = response.data
    except Exception as e:
        st.error(f"Erro ao carregar alunos: {e}")
        st.stop()

    if alunos:
        tab1, tab2 = st.tabs(["📝 Chamada Manhã", "🏃 Registro de Evasão"])

        # ==========================================
        # ABA 1: CHAMADA DA MANHÃ
        # ==========================================
        with tab1:
            st.markdown("### 📋 Registro de Presença")
            st.caption("Desmarque os alunos ausentes e clique em Finalizar.")

            try:
                res_freq = supabase.table("frequencia").select("aluno_nome, status").eq("turma", turma_real).eq("data_chamada", data_hoje).execute()
                dados_freq_hoje = res_freq.data
                status_banco = {f['aluno_nome']: f['status'] for f in dados_freq_hoje}
            except Exception as e:
                st.warning(f"Aviso ao verificar chamada anterior: {e}")
                status_banco = {}

            if status_banco:
                st.success("✅ A chamada de hoje já foi registrada! Você pode alterá-la abaixo se necessário.")
            else:
                st.info("⚠️ A chamada de hoje ainda não foi feita.")

            with st.form("form_chamada"):
                presencas = {}
                
                for i, aluno in enumerate(alunos):
                    nome_aluno = aluno['nome']
                    col_foto, col_nome, col_check = st.columns([1, 3, 2])
                    
                    # --- APLICA A MESMA LÓGICA DO FOTOGRAMA PARA A IMAGEM ---
                    chave = limpar_texto_absoluto(nome_aluno)
                    url_img = mapa_fotos.get(chave)
                    
                    if not url_img:
                        url_img = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
                    
                    col_foto.image(url_img, width=60)
                    col_nome.markdown(f"<div style='padding-top:15px'><b>{nome_aluno}</b></div>", unsafe_allow_html=True)
                    
                    if status_banco:
                        valor_padrao = True if status_banco.get(nome_aluno) == "P" else False
                    else:
                        valor_padrao = True
                        
                    presencas[nome_aluno] = col_check.checkbox("Presente", value=valor_padrao, key=f"c_{i}")

                submit = st.form_submit_button("🚀 FINALIZAR CHAMADA", use_container_width=True, type="primary")
                
                if submit:
                    dados_insercao = [
                        {
                            "turma": turma_real, 
                            "aluno_nome": n, 
                            "status": "P" if is_presente else "F", 
                            "data_chamada": data_hoje
                        } 
                        for n, is_presente in presencas.items()
                    ]
                    
                    try:
                        with st.spinner("Salvando chamada no sistema..."):
                            supabase.table("frequencia").delete().match({"turma": turma_real, "data_chamada": data_hoje}).execute()
                            res_insert = supabase.table("frequencia").insert(dados_insercao).execute()
                            
                        if res_insert.data:
                            st.success("🎉 Chamada salva com sucesso!")
                            time.sleep(1.5) 
                            st.rerun()
                        else:
                             st.error("Falha ao salvar. Nenhuma confirmação recebida do servidor.")
                    except Exception as e:
                        st.error(f"Erro grave ao salvar: {e}")

        # ==========================================
        # ABA 2: REGISTRO DE EVASÃO
        # ==========================================
        with tab2:
            aula_sug = descobrir_aula_atual(hora_atual)
            lista_aulas = ["1º Aula", "2º Aula", "3º Aula", "4º Aula", "5º Aula", "6º Aula", "7º Aula", "8º Aula", "9º Aula"]
            
            if aula_sug in lista_aulas:
                idx_aula = lista_aulas.index(aula_sug)
            else:
                idx_aula = 0 

            aula_sel = st.selectbox("Selecione a Aula para Registro:", lista_aulas, index=idx_aula)
            st.write(f"📌 *Sugestão atual baseada no horário:* **{aula_sug}**")
            
            try:
                res_ev = supabase.table("evasoes").select("aluno_nome").eq("data_registro", data_hoje).eq("aula_periodo", aula_sel).eq("turma", turma_real).execute()
                fugoes = [r['aluno_nome'] for r in res_ev.data] if res_ev.data else []
            except:
                fugoes = []

            st.divider()

            for i, aluno in enumerate(alunos):
                c1, c2, c3 = st.columns([1, 3, 2])
                
                # --- APLICA A MESMA LÓGICA DO FOTOGRAMA PARA A IMAGEM NA EVASÃO ---
                chave = limpar_texto_absoluto(aluno['nome'])
                url_img = mapa_fotos.get(chave)
                
                if not url_img:
                    url_img = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
                
                c1.image(url_img, width=55)
                c2.markdown(f"<div style='padding-top:10px;'><b>{aluno['nome']}</b></div>", unsafe_allow_html=True)
                
                if aluno['nome'] in fugoes:
                    c3.error("🚨 Ausente")
                else:
                    if c3.button("🏃 Registrar", key=f"fuga_{i}", use_container_width=True):
                        try:
                            supabase.table("evasoes").insert({
                                "data_registro": data_hoje, 
                                "turma": turma_real, 
                                "aluno_nome": aluno['nome'], 
                                "aula_periodo": aula_sel
                            }).execute()
                            st.toast(f"Evasão registrada: {aluno['nome']}")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao registrar: {e}")
else:
    st.error("🚫 Por favor, acesse o sistema através de um QR Code válido.")