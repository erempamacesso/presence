import streamlit as st
import datetime
import time
from github import Github

def exibir_gestao_feira(supabase_conn):
    st.title("🎪 Central de Eventos e Feiras")
    st.markdown("Gerencie os eventos, banners, editais e linhas de pesquisa da escola.")
    
    # CRIANDO AS 3 ABAS
    aba_ver, aba_evento, aba_orientadores = st.tabs([
        "👀 Ver Eventos Ativos",
        "📅 1. Lançar Novo Evento", 
        "👨‍🏫 2. Cadastrar Trabalhos"
    ])
    
    # ==========================================
# ABA 0: VITRINE (CORRIGIDA: DATAS E MEMBROS)
# ==========================================
with aba_ver:
    @st.cache_data(ttl=60)
    def buscar_eventos_vitrine(_supabase):
        # Selecionando as colunas de membros (min e max)
        return _supabase.table("feira_eventos").select(
            "id, nome, data_inicio, data_fim, onde, turmas, edital_link, imagem_capa_link, min_membros, max_membros, ativo"
        ).eq("ativo", True).execute()

    # Botão de atualização
    if st.button("🔄 Atualizar Vitrine"):
        st.cache_data.clear()
        st.rerun()

    try:
        res = buscar_eventos_vitrine(supabase_conn)
        eventos = res.data
        
        if not eventos:
            st.info("Nenhum evento ativo no momento.")
        else:
            for ev in eventos:
                with st.container(border=True):
                    # 1. Capa do Evento
                    if ev.get('imagem_capa_link'):
                        st.image(ev['imagem_capa_link'], use_container_width=True)
                    
                    col_info, col_btn = st.columns([2.5, 1.5])
                    
                    with col_info:
                        st.subheader(f"🏆 {ev['nome']}")
                        
                        # 2. Datas com fonte maior e destaque
                        data_ini = ev['data_inicio']
                        data_fim = ev['data_fim']
                        st.markdown(f"🗓️ **Período:** <span style='font-size: 1.1rem; color: #ff4b4b;'>{data_ini} até {data_fim}</span>", unsafe_allow_html=True)
                        
                        st.write(f"📍 **Onde:** {ev.get('onde', 'EREM PAM')}")
                        st.write(f"👥 **Turmas:** {ev.get('turmas', 'Geral')}")
                    
                    with col_btn:
                        # 3. Correção Conceitual: Mínimo e Máximo de Alunos
                        v_min = ev.get('min_membros', 0)
                        v_max = ev.get('max_membros', 0)
                        
                        st.markdown(f"""
                            <div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; border: 1px solid #ddd;">
                                <span style="font-size: 0.8rem; color: #555;">ALUNOS POR GRUPO</span><br>
                                <span style="font-size: 1.5rem; font-weight: bold; color: #1f77b4;">{v_min} a {v_max}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.write("") # Espaçador
                        
                        if ev.get("edital_link"):
                            st.link_button("📄 Ver Edital", ev["edital_link"], use_container_width=True)
                        else:
                            st.button("🚫 Sem Edital", disabled=True, use_container_width=True)
                            
    except Exception as e:
        st.error(f"Erro ao carregar vitrine: {e}")

    # ==========================================
    # ABA 1: CRIAR NOVO EVENTO (COM UPLOAD)
    # ==========================================
    with aba_evento:
        st.subheader("Configurar Novo Evento")
        
        # O formulário tem um nome único no sistema inteiro
        with st.form("form_criacao_evento_mestre", clear_on_submit=True):
            nome_evento = st.text_input("Nome do Evento", placeholder="Ex: NATUMAT 2026")
            
            col1, col2 = st.columns(2)
            data_inicio = col1.date_input("Data de Início")
            data_fim = col2.date_input("Data de Fim")
            
            col3, col4 = st.columns(2)
            local_ev = col3.text_input("Local da Feira", placeholder="Ex: Pátio e Laboratórios")
            turmas_ev = col4.text_input("Público-Alvo / Turmas", placeholder="Ex: 1º e 2º Anos")
            
            col5, col6 = st.columns(2)
            min_alunos = col5.number_input("Mínimo de Alunos por Grupo", min_value=1, value=4)
            max_alunos = col6.number_input("Máximo de Alunos por Grupo", min_value=1, value=8)
            
            observacoes = st.text_area("Observações Extras", placeholder="Digite instruções adicionais...")
            
            st.markdown("---")
            st.write("🖼️ **Banner de Divulgação (Imagem)**")
            arquivo_banner = st.file_uploader("Arraste a capa aqui (JPG ou PNG)", type=["png", "jpg", "jpeg"], key="up_capa_evento")
            
            st.write("📄 **Edital Oficial (PDF)**")
            arquivo_pdf = st.file_uploader("Arraste o edital aqui", type=["pdf"], key="up_pdf_evento")
            
            salvar_evento = st.form_submit_button("💾 Salvar e Publicar Evento", type="primary", use_container_width=True)
            
            if salvar_evento:
                if not nome_evento:
                    st.warning("⚠️ Você precisa digitar pelo menos o nome do evento!")
                else:
                    link_foto_final = ""
                    link_pdf_final = ""
                    
                    try:
                        token = st.secrets["GITHUB_TOKEN"]
                        g = Github(token)
                        repo = g.get_repo("erempamacesso/presence")
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # Processar Upload da Imagem
                        if arquivo_banner is not None:
                            path_img = f"banners/banner_{ts}.png"
                            repo.create_file(path_img, f"Upload Banner: {nome_evento}", arquivo_banner.read(), branch="main")
                            link_foto_final = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_img}"
                        
                        # Processar Upload do PDF
                        if arquivo_pdf is not None:
                            path_pdf = f"editais/edital_{ts}.pdf"
                            repo.create_file(path_pdf, f"Upload Edital: {nome_evento}", arquivo_pdf.read(), branch="main")
                            link_pdf_final = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{path_pdf}"
                            
                        # Salvar tudo no Supabase
                        dados_para_salvar = {
                            "nome": nome_evento,
                            "data_inicio": str(data_inicio),
                            "data_fim": str(data_fim),
                            "onde": local_ev,
                            "turmas": turmas_ev,
                            "min_membros": min_alunos,
                            "max_membros": max_alunos,
                            "observacoes": observacoes,
                            "imagem_capa_link": link_foto_final,
                            "edital_link": link_pdf_final,
                            "ativo": True
                        }
                        
                        supabase_conn.table("feira_eventos").insert(dados_para_salvar).execute()
                        st.success(f"✅ Evento '{nome_evento}' criado com sucesso!")
                        time.sleep(1.5)
                        st.rerun() # Recarrega a página para limpar o formulário de verdade
                        
                    except Exception as e:
                        st.error(f"🚨 Erro durante o salvamento: {e}")

    # ==========================================
    # ABA 2: CADASTRAR TRABALHOS (ORIENTADORES)
    # ==========================================
    with aba_orientadores:
        st.subheader("Cadastro de Linhas de Pesquisa / Temas")
        
        try:
            # Busca eventos ativos para o selectbox
            res_ev = supabase_conn.table("feira_eventos").select("id, nome").eq("ativo", True).execute()
            dict_eventos = {item["nome"]: item["id"] for item in res_ev.data}
            
            with st.form("form_novo_trabalho_mestre", clear_on_submit=True):
                ev_selecionado = st.selectbox("Para qual evento?", list(dict_eventos.keys())) if dict_eventos else None
                
                # Busca professores ativos
                res_prof = supabase_conn.table("professores_matriculas").select("professor").execute()
                lista_profs = ["Selecione..."] + sorted([p["professor"] for p in res_prof.data if p["professor"]])
                prof_selecionado = st.selectbox("Professor Orientador", lista_profs)
                
                titulo = st.text_input("Título da Linha de Pesquisa")
                descricao = st.text_area("Descrição Breve")
                vagas = st.number_input("Limite de Grupos", min_value=1, value=5)
                
                btn_salvar_tema = st.form_submit_button("➕ Adicionar Tema", use_container_width=True)
                
                if btn_salvar_tema:
                    if ev_selecionado and prof_selecionado != "Selecione..." and titulo:
                        dados_tema = {
                            "evento_id": dict_eventos[ev_selecionado],
                            "professor_nome": prof_selecionado,
                            "titulo_trabalho": titulo,
                            "descricao": descricao,
                            "vagas_grupos": vagas
                        }
                        supabase_conn.table("feira_temas").insert(dados_tema).execute()
                        st.success("✅ Linha de pesquisa cadastrada!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Preencha evento, orientador e título!")
        except Exception as e:
            st.error(f"Erro ao carregar dados dos orientadores: {e}")