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
            df_exibicao.columns = ['Nome do Estudante', 'Turma', 'Penalidade', 'Vigente até', 'Registrado por']
            
            # Deixando a data no padrão brasileiro (DD/MM/AAAA)
            # Adicionado um tratamento caso a data venha nula do banco
            df_exibicao['Vigente até'] = pd.to_datetime(df_exibicao['Vigente até'], errors='coerce').dt.strftime('%d/%m/%Y')
            df_exibicao['Vigente até'] = df_exibicao['Vigente até'].fillna('Sem prazo')
            
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
                    
                    # 1. ESCOLHA DO TIPO DE OCORRÊNCIA
                    tipo_selecionado = st.selectbox("Tipo de Ação:", ["Advertência", "Suspensão (Professor)", "Suspensão (Gestão)", "Outros"])
                    
                    # Se escolher "Outros", abre um campo de texto para digitar
                    if tipo_selecionado == "Outros":
                        tipo_ocorrencia = st.text_input("Qual ocorrência? (Especifique):")
                    else:
                        tipo_ocorrencia = tipo_selecionado

                    motivo = st.text_area("Motivo (Descreva o que aconteceu):")
                    
                    # 2. ⏳ LÓGICA DO PRAZO DE SUSPENSÃO
                    data_retorno = None
                    if "Suspensão" in tipo_selecionado:
                        data_hoje = datetime.today().date()
                        data_retorno = st.date_input("⏳ Vigente até (Último dia da suspensão):", min_value=data_hoje)
                        
                        # Calcula e mostra os dias na tela em tempo real
                        if data_retorno:
                            dias_suspensao = (data_retorno - data_hoje).days + 1
                            st.info(f"O aluno ficará suspenso por **{dias_suspensao} dia(s)**. O alerta sumirá após essa data.")
                    
                    st.markdown("---")
                    st.markdown("🔑 **Autenticação de Segurança**")
                    
                    # 3. 🔐 LÓGICA DA ASSINATURA ELETRÔNICA (Usa só a matrícula)
                    senha_assinatura = st.text_input("Sua Assinatura Eletrônica (a mesma usa para cancelar reservas):", type="password", help="Digite sua matrícula para validar a ocorrência.")
                    
                    if st.button("🚨 Gravar Ocorrência", type="primary", use_container_width=True):
                        # Verifica se preencheu tudo (inclusive o campo 'Outros' se foi selecionado)
                        if not motivo or not senha_assinatura or not tipo_ocorrencia:
                            st.warning("Por favor, preencha o tipo de ocorrência, o motivo e a sua assinatura (Matrícula)!")
                        else:
                            # Vai no banco conferir a assinatura secreta
                            res_prof = supabase.table("professores_matriculas").select("professor").eq("matricula", senha_assinatura).execute()
                            
                            if not res_prof.data:
                                st.error("❌ Assinatura inválida! Matrícula não encontrada no sistema.")
                            else:
                                # Pegou o nome do professor automaticamente
                                nome_professor = res_prof.data[0]['professor']
                                
                                dados_inserir = {
                                    "aluno_id": aluno_id,
                                    "aluno_nome": aluno_sel_nome,
                                    "turma": turma_sel,
                                    "tipo_ocorrencia": tipo_ocorrencia,
                                    "motivo": motivo,
                                    "data_retorno": str(data_retorno) if data_retorno else None,
                                    "quem_registrou": nome_professor,
                                    "status": "Ativa"
                                }
                                
                                try:
                                    supabase.table("ocorrencias_disciplinares").insert(dados_inserir).execute()
                                    st.success(f"✅ Ocorrência assinada e registrada por: **{nome_professor}**!")
                                    st.rerun() # Recarrega a página na hora para mostrar no mural
                                except Exception as e:
                                    st.error(f"Erro ao salvar no banco: {e}")
    # AQUI ESTAVA FALTANDO O FECHAMENTO DO CÓDIGO! 👇
    except Exception as e:
        st.error(f"Erro ao carregar o formulário: {e}")