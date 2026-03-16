import streamlit as st
from supabase import create_client
import random

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Portal do Aluno - EREMPAM", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #e0eafc 0%, #cfdef3 100%);
    }
    .card-aluno {
        background: rgba(255, 255, 255, 0.8);
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
        border: 1px solid white;
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO COM OS DOIS BANCOS ---
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL_ALUNOS"], st.secrets["SUPABASE_KEY_ALUNOS"]), \
           create_client(st.secrets["SUPABASE_URL_PROVAS"], st.secrets["SUPABASE_KEY_PROVAS"])

db_alunos, db_provas = init_db()

# --- 3. CONTROLE DE ESTADO (MEMÓRIA) ---
if 'aluno' not in st.session_state:
    st.session_state.aluno = None
if 'prova_feita' not in st.session_state:
    st.session_state.prova_feita = False
if 'questoes_preparadas' not in st.session_state:
    st.session_state.questoes_preparadas = None

# ==========================================
# 🟢 ETAPA 1: TELA DE LOGIN DO ALUNO
# ==========================================
if st.session_state.aluno is None:
    st.markdown('<div class="card-aluno"><h1>🎓 Bem-vindo ao EREMPAM</h1><p>Identifique-se para começar sua prova</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("form_login"):
            # Usando a coluna numero_matricula que criamos no SQL
            matricula = st.text_input("Sua Matrícula (Ex: 1111111):", placeholder="Digite aqui...")
            btn_acessar = st.form_submit_button("🚀 Acessar Avaliação", use_container_width=True)
            
            if btn_acessar:
                if matricula.strip():
                    try:
                        # Buscando o aluno
                        st.info(f"Procurando a matrícula: '{matricula.strip()}'...")
                        res = db_alunos.table("alunos").select("*").eq("numero_matricula", matricula.strip()).execute()
                        
                        # Mostrando o que o banco devolveu (DEBUG)
                        st.write("Resposta do Banco:", res.data)
                        
                        if res.data:
                            st.success("Aluno encontrado!")
                            st.session_state.aluno = res.data[0]
                            st.rerun()
                        else:
                            st.error("O banco buscou, mas retornou VAZIO. A matrícula não bateu.")
                    except Exception as e:
                        st.error(f"ERRO DE CONEXÃO: {e}")
                else:
                    st.warning("Por favor, digite sua matrícula.")

# ==========================================
# 🔵 ETAPA 2: REALIZAÇÃO DA PROVA
# ==========================================
elif not st.session_state.prova_feita:
    aluno = st.session_state.aluno
    nome_primeiro = aluno.get('nome', 'Aluno').split()[0]
    turma = aluno.get('turma', 'Turma não informada')
    
    st.sidebar.title(f"👋 Olá, {nome_primeiro}")
    st.sidebar.info(f"📍 {turma}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    # Descobre a série baseada na turma (Ex: "3º A" -> "3º Ano")
    serie = "1º Ano" if "1º" in turma else "2º Ano" if "2º" in turma else "3º Ano"
    
    # Busca se tem prova ATIVA para essa série no banco de PROVAS
    res_prova = db_provas.table("modelos_prova").select("*").eq("serie", serie).eq("ativa", True).execute()

    if not res_prova.data:
        st.markdown(f'<div class="card-aluno"><h2>📚 Olá, {nome_primeiro}!</h2><p>Nenhuma prova disponível para o {serie} no momento.</p></div>', unsafe_allow_html=True)
    else:
        prova_ativa = res_prova.data[0]
        st.markdown(f'<div class="card-aluno"><h2>📄 {prova_ativa["titulo"]}</h2><p>Boa sorte, {aluno.get("nome", "Aluno")}!</p></div>', unsafe_allow_html=True)
        
        # --- PREPARAR E EMBARALHAR (ANTI-FRAUDE) ---
        if st.session_state.questoes_preparadas is None:
            ids_questoes = prova_ativa['questoes_ids']
            res_questoes = db_provas.table("questoes").select("*").in_("id", ids_questoes).execute()
            questoes_db = res_questoes.data
            
            # 1. Embaralha a ordem das questões
            random.shuffle(questoes_db)
            
            preparadas = []
            for q in questoes_db:
                # 2. Embaralha as alternativas
                alts = [(letra, texto) for letra, texto in q.get('alternativas', {}).items() if texto.strip()]
                random.shuffle(alts)
                
                preparadas.append({
                    "id": q["id"],
                    "enunciado": q["enunciado"],
                    "assunto": q.get("assunto", "Geral"),
                    "resposta_correta": q["resposta_correta"],
                    "justificativas": q.get("justificativas", {}),
                    "opcoes_embaralhadas": alts
                })
            st.session_state.questoes_preparadas = preparadas
            st.session_state.prova_ativa_id = prova_ativa['id']

        # --- RENDERIZAR A PROVA ---
        questoes = st.session_state.questoes_preparadas
        respostas = {}
        
        with st.form("form_prova"):
            for i, q in enumerate(questoes):
                st.markdown(f"### Questão {i+1}")
                st.markdown(q['enunciado'], unsafe_allow_html=True)
                
                # Extrai apenas os textos embaralhados para o botão de rádio
                opcoes_texto = [texto for letra, texto in q['opcoes_embaralhadas']]
                escolha = st.radio("Escolha sua resposta:", opcoes_texto, index=None, key=f"q_{q['id']}")
                
                if escolha:
                    # Recupera a letra original correspondente ao texto escolhido
                    letra_original = next(letra for letra, texto in q['opcoes_embaralhadas'] if texto == escolha)
                    respostas[q['id']] = letra_original
                    
                st.divider()

            if st.form_submit_button("✅ Finalizar e Ver Diagnóstico", type="primary", use_container_width=True):
                if len(respostas) < len(questoes):
                    st.warning("⚠️ Responda todas as questões antes de finalizar!")
                else:
                    # Calcula a nota
                    acertos = sum(1 for q in questoes if respostas.get(q['id']) == q['resposta_correta'])
                    nota = (acertos / len(questoes)) * 10
                    
                    # Salva no banco de PROVAS
                    dados_envio = {
                        "aluno_nome": aluno.get('nome', 'Aluno'),
                        "prova_id": st.session_state.prova_ativa_id,
                        "questoes_ids": prova_ativa['questoes_ids'],
                        "respostas_aluno": respostas,
                        "nota_final": nota,
                        "serie": serie
                    }
                    try:
                        db_provas.table("respostas_alunos").insert(dados_envio).execute()
                        # Passa os dados para a tela de diagnóstico
                        st.session_state.respostas_aluno = respostas
                        st.session_state.nota_final = nota
                        st.session_state.prova_feita = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao enviar: {e}")

# ==========================================
# 🟠 ETAPA 3: TELA DE DIAGNÓSTICO (FEEDBACK)
# ==========================================
else:
    st.markdown('<div class="card-aluno"><h1>🎯 Seu Resultado</h1></div>', unsafe_allow_html=True)
    
    qs = st.session_state.questoes_preparadas
    resps = st.session_state.respostas_aluno
    nota = st.session_state.nota_final

    st.metric("Sua Nota Final", f"{nota:.1f}")
    st.divider()
    st.subheader("Análise Questão por Questão:")

    for i, q in enumerate(qs):
        r = resps[q['id']]
        correta = q['resposta_correta']
        justs = q.get('justificativas', {})
        
        with st.expander(f"Questão {i+1} - {'✅' if r == correta else '❌'} {q['assunto']}"):
            if r == correta:
                st.success("Parabéns, você acertou!")
            else:
                # Procura os textos originais para mostrar o que ele marcou vs o que era correto
                texto_marcado = next((t for l, t in q['opcoes_embaralhadas'] if l == r), "Sua resposta")
                texto_correto = next((t for l, t in q['opcoes_embaralhadas'] if l == correta), "Resposta correta")
                
                st.error(f"**Você marcou:** {texto_marcado}\n\n**A resposta correta era:** {texto_correto}")
            
            feedback = justs.get(r, "Analise sua resposta com os materiais da aula.")
            if feedback.strip():
                st.info(f"💡 **Diagnóstico do Professor:** {feedback}")

    st.divider()
    if st.button("🚪 Sair do Portal", type="primary"):
        st.session_state.clear()
        st.rerun()