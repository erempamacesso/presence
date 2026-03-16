import streamlit as st
import pandas as pd
from datetime import datetime

def exibir_ocorrencias(supabase):
    st.title("🚨 Mural de Ocorrências e Suspensões")
    st.write("Acompanhe e registre penalidades disciplinares aplicadas aos estudantes.")

    # ==========================================
    # 📋 MURAL DE SUSPENSÕES ATIVAS
    # ==========================================
    st.subheader("⚠️ Suspensões e Alertas Ativos")
    
    try:
        # Buscar ocorrências ativas
        res_ocorrencias = supabase.table("ocorrencias_disciplinares").select("*").eq("status", "Ativa").order("created_at", desc=True).execute()
        
        if res_ocorrencias.data:
            df_ocorrencias = pd.DataFrame(res_ocorrencias.data)
            
            # Escolhendo as colunas para ficar bonito na tela
            df_exibicao = df_ocorrencias[['aluno_nome', 'turma', 'tipo_ocorrencia', 'data_retorno', 'quem_registrou']]
            df_exibicao.columns = ['Nome do Estudante', 'Turma', 'Penalidade', 'Data de Retorno', 'Registrado por']
            
            # Deixando a data no padrão brasileiro (DD/MM/AAAA)
            df_exibicao['Data de Retorno'] = pd.to_datetime(df_exibicao['Data de Retorno']).dt.strftime('%d/%m/%Y')
            df_exibicao['Data de Retorno'] = df_exibicao['Data de Retorno'].fillna('Sem data')
            
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        else:
            st.success("Tudo tranquilo! Nenhuma ocorrência ou suspensão ativa no momento. 🎉")
    except Exception as e:
        st.error(f"Erro ao carregar o mural: {e}")

    st.divider()

    # ==========================================
    # 📝 REGISTRO DE NOVA OCORRÊNCIA
    # ==========================================
    st.subheader("➕ Registrar Nova Ocorrência")
    
    try:
        # Buscar turmas para o filtro
        res_turmas = supabase.table("alunos").select("turma").execute()
        lista_turmas = sorted(list(set([r['turma'] for r in res_turmas.data if r.get('turma')])))
        
        c1, c2 = st.columns(2)
        with c1:
            turma_sel = st.selectbox("1. Selecione a Turma:", [""] + lista_turmas)
        
        if turma_sel:
            # Buscar alunos apenas da turma selecionada
            alunos_turma = supabase.table("alunos").select("id, nome").eq("turma", turma_sel).order("nome").execute().data
            mapa_alunos = {a['nome']: a['id'] for a in alunos_turma}
            
            with c2:
                aluno_sel_nome = st.selectbox("2. Selecione o Estudante:", [""] + list(mapa_alunos.keys()))
            
            if aluno_sel_nome:
                aluno_id = mapa_alunos[aluno_sel_nome]
                
                with st.container(border=True):
                    st.markdown(f"**Registrando penalidade para:** `{aluno_sel_nome}`")
                    
                    tipo_ocorrencia = st.selectbox("Tipo de Ação:", ["Advertência", "Suspensão (Professor)", "Suspensão (Gestão)"])
                    motivo = st.text_area("Motivo (Descreva o que aconteceu):")
                    
                    # Se for suspensão, pede o dia que o aluno volta
                    data_retorno = None
                    if "Suspensão" in tipo_ocorrencia:
                        data_retorno = st.date_input("Data autorizada para retorno à escola/aula:")
                    
                    st.markdown("---")
                    st.markdown("🔑 **Autenticação de Segurança**")
                    
                    col_sec1, col_sec2 = st.columns(2)
                    with col_sec1:
                        usuario_nome = st.text_input("Seu Usuário (Quem está registrando):")
                    with col_sec2:
                        senha_assinatura = st.text_input("Sua Assinatura Eletrônica (Senha):", type="password")
                    
                    if st.button("🚨 Gravar Ocorrência", type="primary", use_container_width=True):
                        if not motivo or not usuario_nome or not senha_assinatura:
                            st.warning("Por favor, preencha o motivo, seu usuário e sua assinatura eletrônica!")
                        else:
                            # ⚠️ AQUI ENTRARÁ A LÓGICA DE VALIDAR A SENHA DEPOIS
                            
                            dados_inserir = {
                                "aluno_id": aluno_id,
                                "aluno_nome": aluno_sel_nome,
                                "turma": turma_sel,
                                "tipo_ocorrencia": tipo_ocorrencia,
                                "motivo": motivo,
                                "data_retorno": str(data_retorno) if data_retorno else None,
                                "quem_registrou": usuario_nome,
                                "status": "Ativa"
                            }
                            
                            try:
                                supabase.table("ocorrencias_disciplinares").insert(dados_inserir).execute()
                                st.success("Ocorrência registrada com sucesso!")
                                st.rerun() # Recarrega a página na hora para mostrar no mural
                            except Exception as e:
                                st.error(f"Erro ao salvar no banco: {e}")
    except Exception as e:
        st.error(f"Erro ao carregar o formulário: {e}")