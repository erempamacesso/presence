import streamlit as st
import datetime
import time
from github import Github

def exibir_gestao_feira(supabase_conn):
    st.title("🎪 Central de Eventos e Feiras")
    st.markdown("Gerencie eventos, editais, banners e linhas de pesquisa dos orientadores.")
    
    # AS 3 ABAS
    aba_ver, aba_evento, aba_orientadores = st.tabs([
        "👀 Ver Eventos Ativos",
        "📅 1. Lançar Novo Evento", 
        "👨‍🏫 2. Cadastrar Trabalhos"
    ])
    
    # ==========================================
    # ABA 0: VITRINE (COM O BANNER TIPO EVENTIM)
    # ==========================================
    with aba_ver:
        try:
            res = supabase_conn.table("feira_eventos").select("*").eq("ativo", True).execute()
            eventos = res.data
            
            if not eventos:
                st.info("Nenhum evento ativo no momento. Crie um na aba ao lado! 👉")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        # --- BANNER ---
                        link_banner = ev.get('imagem_capa_link')
                        if link_banner:
                            st.markdown(f"""
                                <div style="width:100%; max-height:300px; overflow:hidden; border-radius:15px; margin-bottom:15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                                    <img src="{link_banner}" style="width:100%; height:auto; display:block;">
                                </div>
                            """, unsafe_allow_html=True)
                        
                        # --- INFORMAÇÕES ---
                        col_info, col_btn = st.columns([3, 1])
                        with col_info:
                            st.subheader(f"🏆 {ev['nome']}")
                            st.caption(f"🗓️ **Período:** {ev['data_inicio']} até {ev['data_fim']}")
                            st.write(f"📍 **Onde:** {ev.get('onde', 'EREM PAM')}")
                            st.write(f"👥 **Turmas:** {ev.get('turmas', 'Geral')}")
                            st.write(f"📝 **Sobre:** {ev.get('observacoes', '')}")
                        
                        with col_btn:
                            # CORREÇÃO DO ERRO DE DUPLICATA: Adicionando keys únicas com o ID do evento
                            if ev.get("edital_link"):
                                st.link_button("📄 Ver Edital", ev["edital_link"], use_container_width=True, key=f"btn_edital_{ev['id']}")
                            else:
                                st.button("🚫 Sem Edital", disabled=True, use_container_width=True, key=f"btn_no_edital_{ev['id']}")
                            
                            st.metric("Grupos (Mín-Máx)", f"{ev['min_membros']} a {ev['max_membros']} alunos")
        except Exception as e:
            st.error(f"Erro ao carregar vitrine: {e}")

    # ==========================================
    # ABA 1: LANÇAR EVENTO
    # ==========================================
    with aba_evento:
        st.subheader("Configurar Novo Evento")
        
        with st.form("form_novo_evento", clear_on_submit=True):
            # CORREÇÃO DE LIMPEZA: Trocando "value" por "placeholder"
            nome_evento = st.text_input("Nome do Evento", placeholder="Ex: NATUMAT 2026")
            
            col1, col2 = st.columns(2)
            # Ao remover o value daqui, ele automaticamente usa a data de hoje como padrão e reseta ao salvar
            data_inicio = col1.date_input("Data de Início")
            data_fim = col2.date_input("Data de Fim")
            
            col3, col4 = st.columns(2)
            local_ev = col3.text_input("Local (Ex: Pátio, Auditório)", placeholder="Ex: Pátio e Laboratórios")
            turmas_ev = col4.text_input("Público/Turmas", placeholder="Ex: 1º, 2º e 3º Anos")
            
            col5, col6 = st.columns(2)
            min_alunos = col5.number_input("Mínimo de Alunos/Grupo", min_value=1, value=4)
            max_alunos = col6.number_input("Máximo de Alunos/Grupo", min_value=1, value=8)
            
            observacoes = st.text_area("Observações (Aparecerá no app dos alunos)", placeholder="Digite informações adicionais...")
            
            st.markdown("---")
            # --- UPLOAD DE BANNER AUTOMÁTICO ---
            st.write("🖼️ **Capa do Evento (Banner)**")
            arquivo_foto = st.file_uploader("Arraste a foto do banner aqui", type=["png", "jpg", "jpeg"])
            
            st.markdown("---")
            st.write("📄 **Edital do Evento (PDF)**")
            arquivo_pdf = st.file_uploader("Arraste o edital em PDF aqui para upload automático", type=["pdf"])
            
            salvar_evento = st.form_submit_button("💾 Salvar Evento", type="primary", use_container_width=True)
            
            if salvar_evento:
                link_foto = ""
                link_final_edital = ""
                
                # SÓ EXECUTA SE O PROFESSOR COLOCOU O NOME DO EVENTO
                if not nome_evento:
                    st.warning("⚠️ O nome do evento é obrigatório!")
                else:
                    try:
                        token = st.secrets["GITHUB_TOKEN"]
                        g = Github(token)
                        repo = g.get_repo("erempamacesso/presence")
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # 1. FAZ O UPLOAD DA FOTO (Se houver)
                        if arquivo_foto is not None:
                            caminho_foto = f"banners/banner_{timestamp}.png"
                            conteudo_foto = arquivo_foto.read()
                            repo.create_file(caminho_foto, f"Upload Banner: {nome_evento}", conteudo_foto, branch="main")
                            link_foto = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{caminho_foto}"
                            st.toast("✅ Banner enviado ao GitHub!")

                        # 2. FAZ O UPLOAD DO PDF (Se houver)
                        if arquivo_pdf is not None:
                            caminho_git = f"editais/edital_{timestamp}.pdf"
                            conteudo_pdf = arquivo_pdf.read()
                            repo.create_file(caminho_git, f"Upload Edital: {nome_evento}", conteudo_pdf, branch="main")
                            link_final_edital = f"https://raw.githubusercontent.com/erempamacesso/presence/main/{caminho_git}"
                            st.toast("✅ Edital enviado ao GitHub com sucesso!")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao enviar arquivos para o GitHub: {e}")

                    # 3. GRAVA TUDO NO SUPABASE
                    dados_evento = {
                        "nome": nome_evento,
                        "data_inicio": str(data_inicio),
                        "data_fim": str(data_fim),
                        "onde": local_ev,
                        "turmas": turmas_ev,
                        "min_membros": min_alunos,
                        "max_membros": max_alunos,
                        "observacoes": observacoes,
                        "imagem_capa_link": link_foto,
                        "edital_link": link_final_edital,
                        "ativo": True
                    }
                    try:
                        supabase_conn.table("feira_eventos").insert(dados_evento).execute()
                        st.success(f"✅ Evento '{nome_evento}' publicado com sucesso!")
                        time.sleep(1.5)
                        st.rerun() # Isso força a página a recarregar e limpar o form!
                    except Exception as e:
                        st.error(f"🚨 Erro ao salvar o evento: {e} (Verifique as colunas no Supabase!)")

    # ==========================================
    # ABA 2: CADASTRAR TRABALHOS (ORIENTADORES)
    # ==========================================
    with aba_orientadores:
        st.subheader("Cadastro de Trabalhos / Linhas de Pesquisa")
        
        try:
            res_eventos = supabase_conn.table("feira_eventos").select("id, nome").eq("ativo", True).execute()
            dict_eventos = {item["nome"]: item["id"] for item in res_eventos.data}
            lista_eventos = list(dict_eventos.keys())
        except Exception as e:
            lista_eventos = []
            st.warning("Crie um evento na aba ao lado primeiro.")

        try:
            resposta = supabase_conn.table("professores_matriculas").select("professor").execute()
            lista_professores = ["Selecione..."] + sorted([linha["professor"] for linha in resposta.data if linha["professor"]])
        except Exception as e:
            lista_professores = ["Selecione..."]
        
        with st.form("form_novo_tema", clear_on_submit=True):
            evento_selecionado = st.selectbox("Vincular a qual Evento?", lista_eventos) if lista_eventos else None
            professor_selecionado = st.selectbox("Selecione o Orientador", lista_professores)
            titulo_trabalho = st.text_input("Título do Trabalho / Tema")
            descricao_trabalho = st.text_area("Descrição Breve")
            vagas = st.number_input("Limite de grupos para este orientador", min_value=1, value=5)
            
            salvar_tema = st.form_submit_button("➕ Adicionar Linha de Pesquisa", type="primary", use_container_width=True)
            
            if salvar_tema:
                if not evento_selecionado or professor_selecionado == "Selecione..." or not titulo_trabalho:
                    st.warning("Preencha todos os campos obrigatórios!")
                else:
                    dados_tema = {
                        "evento_id": dict_eventos[evento_selecionado],
                        "professor_nome": professor_selecionado,
                        "titulo_trabalho": titulo_trabalho,
                        "descricao": descricao_trabalho,
                        "vagas_grupos": vagas
                    }
                    try:
                        supabase_conn.table("feira_temas").insert(dados_tema).execute()
                        st.success("✅ Trabalho cadastrado com sucesso!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"🚨 Erro ao salvar tema: {e}")