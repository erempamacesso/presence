import streamlit as st
import datetime

def mostrar_tela_inscricao_feira(supabase_conn):
    st.title("🎪 Inscrição - Feira de Ciências")
    
    aluno = st.session_state.get('aluno', {})
    turma_aluno = aluno.get('turma', 'Sem Turma')
    id_aluno = str(aluno.get('id', '')) # Garante que seja texto para o Supabase

    # Máquina de estados interna: Começa na vitrine, depois vai pra escolha do tema
    if 'fluxo_feira' not in st.session_state:
        st.session_state.fluxo_feira = 'vitrine'
        
    # ==========================================
    # PASSO 1: A VITRINE DE EVENTOS
    # ==========================================
    if st.session_state.fluxo_feira == 'vitrine':
        st.write("### Eventos Disponíveis para sua Turma")
        
        try:
            res = supabase_conn.table("feira_eventos").select(
                "id, nome, data_inicio, data_fim, onde, turmas, edital_link, imagem_capa_link, min_membros, max_membros, ativo"
            ).eq("ativo", True).execute()
            eventos = res.data
            
            if not eventos:
                st.info("Nenhum evento ativo no momento.")
            else:
                for ev in eventos:
                    with st.container(border=True):
                        # Layout de 3 colunas idêntico ao do professor
                        col_img, col_info, col_btn = st.columns([1.5, 3, 1.5])
                        
                        with col_img:
                            if ev.get('imagem_capa_link'):
                                st.image(ev['imagem_capa_link'], use_container_width=True)
                            else:
                                st.markdown("<div style='height: 150px; background-color: #f0f2f6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #888;'>🖼️ Sem Imagem</div>", unsafe_allow_html=True)
                        
                        with col_info:
                            st.subheader(f"🏆 {ev['nome']}")
                            data_ini, data_fim = ev.get('data_inicio', ''), ev.get('data_fim', '')
                            try:
                                d_ini_br = datetime.datetime.strptime(data_ini, '%Y-%m-%d').strftime('%d/%m/%Y')
                                d_fim_br = datetime.datetime.strptime(data_fim, '%Y-%m-%d').strftime('%d/%m/%Y')
                            except:
                                d_ini_br, d_fim_br = data_ini, data_fim

                            st.markdown(f"🗓️ **Período:** <span style='color: #ff4b4b;'>{d_ini_br} até {d_fim_br}</span>", unsafe_allow_html=True)
                            st.write(f"📍 **Onde:** {ev.get('onde', 'EREM PAM')}")
                            st.write(f"👥 **Turmas:** {ev.get('turmas', 'Geral')}")
                        
                        with col_btn:
                            v_min, v_max = ev.get('min_membros', 0), ev.get('max_membros', 0)
                            st.markdown(f"""
                                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #e6e6e6; margin-bottom: 12px;">
                                    <span style="font-size: 0.70rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">ALUNOS POR GRUPO</span><br>
                                    <span style="font-size: 1.4rem; font-weight: 800; color: #1f77b4;">{v_min} a {v_max}</span>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # BOTÃO MAGICO: Leva para a tela de temas
                            if st.button("👉 Quero Participar", key=f"part_ev_{ev['id']}", type="primary", use_container_width=True):
                                st.session_state.evento_selecionado = ev
                                st.session_state.fluxo_feira = 'escolha_tema'
                                st.rerun()
                                
                            if ev.get("edital_link"):
                                st.link_button("📄 Ver Edital", ev["edital_link"], use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao carregar eventos: {e}")
            
        st.divider()
        if st.button("⬅️ Voltar ao Painel Principal"):
            st.session_state.etapa = "ante_sala"
            st.rerun()

    # ==========================================
    # PASSO 2: ESCOLHA DA DISCIPLINA / TEMA (Sanfonas)
    # ==========================================
    elif st.session_state.fluxo_feira == 'escolha_tema':
        evento = st.session_state.evento_selecionado
        st.subheader(f"Inscrição: {evento['nome']}")
        st.info(f"📍 Olá Líder! Sua turma é: **{turma_aluno}**")

        # 1. VERIFICA TRAVAS DA TURMA
        try:
            res_inscricoes = supabase_conn.table("feira_inscricoes").select("disciplina").eq("turma", turma_aluno).execute()
            disciplinas_ocupadas = [ins["disciplina"] for ins in res_inscricoes.data]
        except:
            disciplinas_ocupadas = []

        # 2. PUXA OS TEMAS SÓ DESSE EVENTO
        try:
            res_temas = supabase_conn.table("feira_temas").select("*").eq("evento_id", evento['id']).execute()
            todos_temas = res_temas.data if res_temas.data else []
        except Exception as e:
            st.error(f"Erro ao carregar temas: {e}")
            return

        st.markdown("### Selecione o Segmento")
        
        segmentos = ["Química", "Física", "Biologia", "Matemática"]
        icons = {"Química": "🧪", "Física": "⚛️", "Biologia": "🧬", "Matemática": "📐"}

        for seg in segmentos:
            label = f"{icons[seg]} {seg}"
            
            if seg in disciplinas_ocupadas:
                with st.expander(f"🔒 {label} - (Indisponível para sua turma)"):
                    st.warning(f"Sua turma ({turma_aluno}) já possui um grupo inscrito em {seg}.")
            
            else:
                with st.expander(f"📂 {label} - (Disponível)"):
                    temas_do_segmento = [t for t in todos_temas if t.get('disciplina') == seg]
                    
                    if not temas_do_segmento:
                        st.write("Nenhum tema cadastrado para este segmento ainda.")
                    else:
                        st.write("Escolha um dos temas abaixo:")
                        
                        # BUGS CORRIGIDOS: Usando 'titulo_trabalho' em vez de 'nome'
                        opcoes = {f"{t['titulo_trabalho']} (Prof. {t.get('professor_nome', '')})": t['id'] for t in temas_do_segmento}
                        escolha = st.radio("Temas disponíveis:", list(opcoes.keys()), key=f"radio_{seg}")
                        
                        id_tema_escolhido = opcoes[escolha]
                        
                        if st.button(f"🚀 Selecionar {seg}", key=f"btn_{seg}", type="primary"):
                            st.session_state.dados_inscricao = {
                                "evento_id": evento['id'],
                                "tema_id": id_tema_escolhido,
                                "tema_nome": escolha,
                                "disciplina": seg,
                                "turma": turma_aluno,
                                "lider_id": id_aluno,
                                "min_membros": evento.get('min_membros', 1),
                                "max_membros": evento.get('max_membros', 5)
                            }
                            st.success(f"Tema de {seg} selecionado! Na próxima etapa você vai adicionar os colegas.")
                            # st.session_state.fluxo_feira = 'adicionar_membros'
                            # st.rerun()

        st.divider()
        if st.button("⬅️ Voltar aos Eventos"):
            st.session_state.fluxo_feira = 'vitrine'
            st.rerun()