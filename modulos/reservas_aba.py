import streamlit as st
import pandas as pd
import datetime

# --- BANCO DE MATRÍCULAS (FIXO DA GESTÃO) ---
# Matrículas fixas para a gestão não precisar se cadastrar
MATRICULAS_BASE = {
    "11111": "Lilian Jordao",
    "22222": "Jackson Carvalho",
    "33333": "Lylia Cabral"
}

# Gestores que podem cancelar QUALQUER reserva
GESTORES = ["Lilian Jordao", "Jackson Carvalho", "Lylia Cabral"]

def exibir_reservas(supabase, lista_professores, aulas_opcoes, espacos, arg1=None, arg2=None, arg3=None):
    st.title("📅 Sistema de Reservas")
    
    # Adicionada a 5ª Aba para o Cadastro da Assinatura
    aba_cal, aba_lista, aba_nova, aba_cancelar, aba_assinatura = st.tabs([
        "🗓️ Calendário Mensal", 
        "📋 Lista Diária", 
        "✍️ Nova Reserva", 
        "❌ Gerenciar/Cancelar",
        "🔑 Cadastrar Assinatura"
    ])

    # -----------------------------------------
    # ABA 3: NOVA RESERVA (Com trava de conflito)
    # -----------------------------------------
    with aba_nova:
        st.subheader("Agendar Espaço")
        with st.form("form_nova_reserva"):
            col1, col2 = st.columns(2)
            with col1:
                data_reserva = st.date_input("Data:", value=datetime.date.today())
                aula = st.selectbox("Aula:", aulas_opcoes)
                professor = st.selectbox("Professor:", ["-- Selecione --"] + lista_professores)
            with col2:
                espaco = st.selectbox("Espaço:", ["-- Selecione --"] + espacos)
                equipamentos = st.text_input("Equipamentos (Opcional):", placeholder="Ex: Data show, Caixa de som")
                obs = st.text_input("Observações (Opcional):")
            
            btn_salvar = st.form_submit_button("💾 Confirmar Reserva")

            if btn_salvar:
                if professor == "-- Selecione --" or espaco == "-- Selecione --":
                    st.warning("⚠️ Selecione o Professor e o Espaço.")
                else:
                    conflito = supabase.table("reservas").select("id").eq("data_reserva", str(data_reserva))\
                        .eq("aula", aula).eq("espaco", espaco).eq("status", "Ativa").execute()
                    
                    if conflito.data:
                        st.error(f"🚨 CONFLITO! O espaço '{espaco}' já está reservado na {aula} para o dia {data_reserva.strftime('%d/%m/%Y')}.")
                    else:
                        try:
                            dados = {
                                "data_reserva": str(data_reserva),
                                "aula": aula,
                                "professor": professor,
                                "espaco": espaco,
                                "equipamentos": equipamentos,
                                "obs": obs,
                                "status": "Ativa" 
                            }
                            supabase.table("reservas").insert(dados).execute()
                            st.success("✅ Reserva confirmada com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao salvar: {e}")

    # -----------------------------------------
    # ABA 2: LISTA DIÁRIA (Agrupada por Espaço)
    # -----------------------------------------
    with aba_lista:
        st.subheader("Visão Diária por Espaço")
        data_filtro = st.date_input("Ver detalhes do dia:", value=datetime.date.today(), key="data_lista")
        
        try:
            res = supabase.table("reservas").select("*").eq("data_reserva", str(data_filtro)).execute()
            if res.data:
                df_dia = pd.DataFrame(res.data)
                
                for espaco_atual in espacos:
                    df_espaco = df_dia[df_dia['espaco'] == espaco_atual]
                    
                    if not df_espaco.empty:
                        with st.expander(f"📍 {espaco_atual} ({len(df_espaco)} reservas)", expanded=True):
                            df_exibir = df_espaco[['aula', 'professor', 'equipamentos', 'obs', 'status']].copy()
                            
                            df_exibir['status'] = df_exibir['status'].apply(
                                lambda x: "🟢 Ativa" if x == "Ativa" else "🔴 Cancelada"
                            )
                            
                            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma reserva para esta data.")
        except Exception as e:
            st.error(f"Erro ao carregar lista: {e}")

    # -----------------------------------------
    # ABA 4: CANCELAR RESERVA (Assinatura Eletrônica)
    # -----------------------------------------
    with aba_cancelar:
        st.subheader("Cancelar uma Reserva")
        st.info("Apenas gestores ou o próprio professor que reservou podem cancelar.")
        
        data_canc = st.date_input("Data da reserva a cancelar:", value=datetime.date.today(), key="data_canc")
        
        try:
            # Junta as matrículas da gestão com as do banco de dados
            MATRICULAS_DB = MATRICULAS_BASE.copy()
            try:
                res_mat = supabase.table("professores_matriculas").select("*").execute()
                if res_mat.data:
                    MATRICULAS_DB.update({r['matricula']: r['professor'] for r in res_mat.data})
            except:
                pass # Caso a tabela não tenha sido criada ainda, não quebra o app

            res_ativas = supabase.table("reservas").select("*").eq("data_reserva", str(data_canc)).eq("status", "Ativa").execute()
            
            if res_ativas.data:
                opcoes_canc = {f"{r['aula']} - {r['espaco']} ({r['professor']})": r['id'] for r in res_ativas.data}
                
                reserva_selecionada = st.selectbox("Selecione a Reserva para cancelar:", ["-- Selecione --"] + list(opcoes_canc.keys()))
                
                if reserva_selecionada != "-- Selecione --":
                    id_reserva = opcoes_canc[reserva_selecionada]
                    prof_da_reserva = next(r['professor'] for r in res_ativas.data if r['id'] == id_reserva)
                    
                    st.warning("⚠️ SUA MATRÍCULA NÃO FICARÁ EXPOSTA. DIGITE-A ABAIXO PARA ASSINAR O CANCELAMENTO.")
                    matricula_input = st.text_input("Assinatura Eletrônica (Sua Matrícula):", type="password", help="Digite apenas números")
                    
                    if st.button("🗑️ Confirmar Cancelamento", type="primary"):
                        if matricula_input in MATRICULAS_DB:
                            usuario_nome = MATRICULAS_DB[matricula_input]
                            
                            if usuario_nome in GESTORES or usuario_nome == prof_da_reserva:
                                supabase.table("reservas").update({
                                    "status": "Cancelada", 
                                    "cancelado_por": usuario_nome
                                }).eq("id", id_reserva).execute()
                                
                                st.success(f"✅ Reserva cancelada com sucesso por {usuario_nome}.")
                                st.rerun()
                            else:
                                st.error("⛔ Você não tem permissão para cancelar a reserva de outro professor.")
                        else:
                            st.error("❌ Matrícula inválida. Vá na aba 'Cadastrar Assinatura' para registrar sua matrícula.")
            else:
                st.info("Não há reservas ativas para cancelar neste dia.")
        except Exception as e:
            st.error(f"Erro no módulo de cancelamento: {e}")

    # -----------------------------------------
    # ABA 5: CADASTRAR ASSINATURA (Novo)
    # -----------------------------------------
    with aba_assinatura:
        st.subheader("Cadastro de Assinatura")
        st.error("🔒 PRIVACIDADE GARANTIDA: SUA MATRÍCULA NÃO FICARÁ EXPOSTA EM NENHUMA TELA DO SISTEMA. ELA É USADA APENAS COMO SENHA DE CANCELAMENTO.")
        
        prof_selecionado = st.selectbox("1. Selecione seu Nome:", ["-- Selecione --"] + lista_professores)
        matricula_nova = st.text_input("2. Digite sua Matrícula (Apenas números):", type="password")
        
        if st.button("💾 Salvar Minha Assinatura"):
            if prof_selecionado == "-- Selecione --" or not matricula_nova.isdigit():
                st.warning("⚠️ Selecione seu nome e digite apenas números na matrícula.")
            else:
                try:
                    # Checa se o professor já existe no banco
                    existe = supabase.table("professores_matriculas").select("*").eq("professor", prof_selecionado).execute()
                    
                    if existe.data:
                        supabase.table("professores_matriculas").update({"matricula": matricula_nova}).eq("professor", prof_selecionado).execute()
                    else:
                        supabase.table("professores_matriculas").insert({"professor": prof_selecionado, "matricula": matricula_nova}).execute()
                    
                    st.success(f"✅ Assinatura de {prof_selecionado} cadastrada com sucesso! Agora você pode cancelar suas reservas.")
                except Exception as e:
                    st.error(f"Erro ao salvar matrícula: {e}")

    # -----------------------------------------
    # ABA 1: CALENDÁRIO MENSAL (Exibição Dinâmica)
    # -----------------------------------------
    with aba_cal:
        st.subheader("Visão Geral do Mês")
        st.info("💡 Legenda: [Aula] - [Professor] - [Espaço]")
        
        try:
            res_cal = supabase.table("reservas").select("*").eq("status", "Ativa").execute()
            if res_cal.data:
                eventos = []
                for r in res_cal.data:
                    titulo = f"{r['aula']} - {r['professor']} - {r['espaco']}"
                    
                    eventos.append({
                        "title": titulo,
                        "start": r['data_reserva'],
                        "end": r['data_reserva'],
                    })
                
                st.dataframe(pd.DataFrame(eventos)) 
        except Exception as e:
            st.error(f"Erro ao carregar calendário: {e}")
