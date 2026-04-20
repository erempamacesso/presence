import streamlit as st
import json

def mostrar_tela_diagnosticos(supabase):
    st.title("🤖 Importar Diagnósticos Pedagógicos")
    st.write("Vincule feedbacks gerados por Inteligência Artificial aos alunos após uma prova.")
    
    # Puxa as provas para o professor selecionar
    res_provas = supabase.table("modelos_prova").select("id, titulo").order("id", desc=True).execute()
    
    if res_provas.data:
        c1, c2 = st.columns([1, 1.5], gap="large")
        
        # ==========================================
        # LADO ESQUERDO: SELEÇÃO E INSTRUÇÕES
        # ==========================================
        with c1:
            st.subheader("1️⃣ Selecione a Prova")
            # Cria dicionário para o selectbox associar o Título ao ID
            provas_dict = {p['titulo']: p['id'] for p in res_provas.data}
            prova_selecionada = st.selectbox("Vincular feedbacks à qual prova?", list(provas_dict.keys()))
            prova_id = provas_dict[prova_selecionada]
            
            st.divider()
            st.markdown("**Como usar?**")
            st.write("1. Exporte a planilha de notas e erros para o ChatGPT/Gemini.")
            st.write("2. Peça para a IA gerar um diagnóstico curto para cada aluno em formato JSON.")
            st.write("3. O formato **obrigatório** deve ser:")
            st.code('{\n  "123": "O aluno precisa revisar o assunto X.",\n  "124": "Excelente desempenho!"\n}', language="json")
            st.caption("*Onde '123' e '124' são os IDs ou Matrículas dos alunos.*")
            
        # ==========================================
        # LADO DIREITO: SALVAR NO BANCO
        # ==========================================
        with c2:
            st.subheader("2️⃣ Importar Diagnósticos")
            json_input = st.text_area("Cole o JSON da IA aqui:", height=250, placeholder='{\n  "ID_DO_ALUNO": "Feedback gerado pela IA..."\n}')
            
            if st.button("💾 Salvar Feedbacks no Banco", type="primary", use_container_width=True):
                if not json_input.strip():
                    st.warning("⚠️ Cole o código JSON antes de tentar salvar.")
                else:
                    try:
                        dados_ia = json.loads(json_input)
                        count = 0
                        
                        with st.spinner("Salvando feedbacks no banco de dados..."):
                            for al_id, txt in dados_ia.items():
                                supabase.table("feedback_ia_alunos").insert({
                                    "aluno_id": str(al_id), # CORREÇÃO: Força string para evitar erro de tipo
                                    "prova_id": str(prova_id),
                                    "diagnostico_pedagogico": txt,
                                    "revisado_professor": True
                                }).execute()
                                count += 1
                                
                        st.success(f"✅ {count} feedbacks salvos na tabela 'feedback_ia_alunos' para a prova '{prova_selecionada}'!")
                        st.balloons()
                        
                    except json.JSONDecodeError:
                        st.error("❌ Erro: O texto colado não é um JSON válido. Verifique se faltam aspas, vírgulas ou chaves ({}).")
                    except Exception as e:
                        st.error("❌ Erro ao salvar no banco. Mensagem:")
                        st.code(str(e))
    else:
        st.warning("Nenhuma prova encontrada. Crie uma prova primeiro na aba 'Gerar Modelo de Prova'.")