import streamlit as st
import datetime
import time
from github import Github

def exibir_gestao_feira(supabase_conn):
    st.title("🎪 Central de Eventos e Feiras")
    
    # AS 3 ABAS
    aba_ver, aba_evento, aba_orientadores = st.tabs([
        "👀 Ver Eventos Ativos",
        "📅 1. Lançar Novo Evento", 
        "👨‍🏫 2. Cadastrar Trabalhos"
    ])
    
    # ==========================================
    # ABA 0: VITRINE (COM O BANNER)
    # ==========================================
    with aba_ver:
        try:
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
            eventos = res.data
            
            if not eventos:
                st.info("Nenhum evento ativo no momento.")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        # --- BANNER ---
                        link_banner = ev.get('imagem_capa_link')
                        if link_banner:
                            st.image(link_banner, use_container_width=True)
                        
                        # --- INFORMAÇÕES ---
                        col_info, col_btn = st.columns([3, 1])
                        with col_info:
                            st.subheader(f"🏆 {ev['nome']}")
                            st.caption(f"🗓️ {ev['data_inicio']} até {ev['data_fim']}")
                            st.write(f"📍 **Onde:** {ev.get('onde', 'EREM PAM')}")
                            st.write(f"👥 **Turmas:** {ev.get('turmas', 'Geral')}")
                        
                        with col_btn:
                            # CORREÇÃO: Usando 'key' única para evitar o erro de ID duplicado
                            if ev.get("edital_link"):
                                st.link_button("📄 Ver Edital", ev["edital_link"], use_container_width=True, key=f"btn_edit_{ev['id']}")
                            else:
                                st.button("🚫 Sem Edital", disabled=True, use_container_width=True, key=f"btn_off_{ev['id']}")
                            
                            st.metric("Grupos (Máx)", ev['max_membros'])
        except Exception as e:
            st.error(f"Erro ao carregar vitrine: {e}")

    # ==========================================
    # ABA 1: LANÇAR EVENTO (CORRIGIDA)
    # ==========================================
    with aba_evento:
        st.subheader("Configurar Novo Evento")
        
        # CORREÇÃO: Nome do formulário único para evitar conflito global
        with st.form("form_criacao_evento_unico", clear_on_submit=True):
            # CORREÇÃO: Usando placeholder para que o campo comece vazio
            nome_evento = st.text_input("Nome do Evento", placeholder="Ex: NATUMAT 2026")
            
            col1, col2 = st.columns(2)
            data_inicio = col1.date_input("Data de Início", datetime.date.today())
            data_fim = col2.date_input("Data de Fim", datetime.date.today() + datetime.timedelta(days=1))
            
            col3, col4 = st.columns(2)
            local_ev = col3.text_input("Local", placeholder="Ex: Pátio da Escola")
            turmas_ev = col4.text_input("Turmas", placeholder="Ex: 1º e 2º Anos")
            
            col5, col6 = st.columns(2)
            min_alunos = col5.number_input("Mínimo de Alunos/Grupo", min_value=1, value=4)
            max_alunos = col6.number_input("Máximo de Alunos/Grupo", min_value=1, value=8)
            
            observacoes = st.text_area("Observações")
            
            st.markdown("---")
            st.write("🖼️ **Capa do Evento (Banner)**")
            arquivo_banner = st.file_uploader("Arraste a imagem (JPG/PNG)", type=["png", "jpg", "jpeg"], key="up_banner")
            
            st.write("📄 **Edital do Evento (PDF)**")
            arquivo_pdf = st.file_uploader("Arraste o edital em PDF", type=["pdf"], key="up_pdf")
            
            salvar_evento = st.form_submit_button("💾 Salvar Evento", type="primary", use_container_width=True)
            
            if salvar_evento:
                if not nome_evento:
                    st.warning("⚠️ O nome do evento é obrigatório!")
                else:
                    link_foto = ""
                    link_pdf = ""
                    
                    try:
                        token = st.secrets["GITHUB_TOKEN"]
                        g = Github(token)
                        repo = g.get_repo("erempamacesso/presence")
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # Upload Banner
                        if arquivo_banner:
                            path_b = f"banners/banner_{ts}.png"
                            repo.create_file(path_b, f"Banner: {nome_evento}", arquivo_banner.read(), branch="main")
                            link_foto = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_b}"
                        
                        # Upload PDF
                        if arquivo_pdf:
                            path_p = f"editais/edital_{ts}.pdf"
                            repo.create_file(path_p, f"Edital: {nome_evento}", arquivo_pdf.read(), branch="main")
                            link_pdf = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_p}"
                            
                        # Salvar Supabase
                        dados = {
                            "nome": nome_evento, "data_inicio": str(data_inicio), "data_fim": str(data_fim),
                            "onde": local_ev, "turmas": turmas_ev, "min_membros": min_alunos,
                            "max_membros": max_alunos, "observacoes": observacoes,
                            "imagem_capa_link": link_foto, "edital_link": link_pdf, "ativo": True
                        }
                        supabase_conn.table("feira_eventos").insert(dados).execute()
                        st.success("✅ Evento publicado! Limpando campos...")
                        time.sleep(1.5)
                        st.rerun() # CORREÇÃO: Força o reset completo da tela
                        
                    except Exception as e:
                        st.error(f"🚨 Erro: {e}")

    # ==========================================
    # ABA 2: CADASTRAR TRABALHOS
    # ==========================================
    with aba_orientadores:
        st.subheader("Cadastro de Trabalhos / Linhas de Pesquisa")
        
        try:
            res_ev = supabase_conn.table("feira_eventos").select("id, nome").eq("ativo", True).execute()
            dict_eventos = {i["nome"]: i["id"] for i in res_ev.data}
            
            with st.form("form_trabalho_unico", clear_on_submit=True):
                ev_sel = st.selectbox("Evento", list(dict_eventos.keys())) if dict_eventos else None
                
                res_prof = supabase_conn.table("professores_matriculas").select("professor").execute()
                profs = ["Selecione..."] + sorted([p["professor"] for p in res_prof.data if p["professor"]])
                prof_sel = st.selectbox("Orientador", profs)
                
                titulo = st.text_input("Título do Trabalho")
                desc = st.text_area("Descrição")
                vagas = st.number_input("Limite de Grupos", min_value=1, value=5)
                
                if st.form_submit_button("➕ Adicionar Trabalho", use_container_width=True):
                    if ev_sel and prof_sel != "Selecione..." and titulo:
                        dados_t = {
                            "evento_id": dict_eventos[ev_sel], "professor_nome": prof_sel,
                            "titulo_trabalho": titulo, "descricao": desc, "vagas_grupos": vagas
                        }
                        supabase_conn.table("feira_temas").insert(dados_t).execute()
                        st.success("✅ Trabalho cadastrado!")
                        time.sleep(1)
                        st.rerun()
        except Exception as e:
            st.error(f"Erro: {e}")