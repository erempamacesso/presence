import streamlit as st
from supabase import create_client
import os
from dotenv import load_dotenv
from datetime import datetime

# 1. Configuração Padrão
st.set_page_config(page_title="Reservas EREMPAM", layout="centered")

load_dotenv()
SUPABASE_URL = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📅 Sistema de Reservas")
st.markdown("Reserve espaços e equipamentos da escola.")

# --- DADOS FIXOS DA ESCOLA ---
# Pode colar a sua lista real de professores aqui dentro
LISTA_PROFESSORES = [
    "Ana Maria (Matemática)", "Carlos Eduardo (História)", 
    "Fernanda Lima (Português)", "João Silva (Física)", "Maria Souza (Biologia)"
]

AULAS = ["1ª Aula", "2ª Aula", "3ª Aula", "4ª Aula", "5ª Aula", "6ª Aula"]
ESPACOS_TOTAIS = ["Auditório", "Laboratório de Ciências", "Laboratório de Informática", "Quadra", "Nenhum (Só Equipamento)"]

# Quantidade total de cada equipamento na escola
TOTAL_DATASHOWS = 5
TOTAL_CAIXAS = 3
TOTAL_MICROFONES = 3  # Chutei 3, ajuste conforme a realidade

# --- ETAPA 1: ESCOLHER DATA E HORA PRIMEIRO ---
# Precisamos disso primeiro para saber o que já está ocupado
col1, col2 = st.columns(2)
with col1:
    data_selecionada = st.date_input("Data da Reserva:", min_value=datetime.today())
with col2:
    aula_selecionada = st.selectbox("Qual Aula?", AULAS)

# Busca no banco todas as reservas que JÁ EXISTEM para esse dia e essa aula
try:
    resposta = supabase.table("reservas").select("*").eq("data_reserva", str(data_selecionada)).eq("aula", aula_selecionada).execute()
    reservas_existentes = resposta.data
except Exception as e:
    st.error("Erro ao conectar com o banco.")
    reservas_existentes = []

# --- LÓGICA DE PREVENÇÃO DE CONFLITOS (ESPAÇOS) ---
# Descobre quais espaços já foram alugados nesta data/aula
espacos_ocupados = [reserva['espaco'] for reserva in reservas_existentes if reserva['espaco'] != "Nenhum (Só Equipamento)"]
# Filtra a lista: só mostra o que não está ocupado
espacos_disponiveis = [e for e in ESPACOS_TOTAIS if e not in espacos_ocupados]

# --- LÓGICA DE INVENTÁRIO (EQUIPAMENTOS) ---
# Conta quantos equipamentos já estão reservados nesta data/aula
datashows_usados = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Datashow" in r['equipamentos'])
caixas_usadas = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Caixa de Som" in r['equipamentos'])
mics_usados = sum(1 for r in reservas_existentes if r.get('equipamentos') and "Microfone" in r['equipamentos'])

# Calcula o que sobrou
disp_data = TOTAL_DATASHOWS - datashows_usados
disp_caixa = TOTAL_CAIXAS - caixas_usadas
disp_mic = TOTAL_MICROFONES - mics_usados

# Monta a lista de opções de equipamentos mostrando a quantidade
opcoes_equip = []
if disp_data > 0: opcoes_equip.append(f"Datashow ({disp_data} disponíveis)")
if disp_caixa > 0: opcoes_equip.append(f"Caixa de Som ({disp_caixa} disponíveis)")
if disp_mic > 0: opcoes_equip.append(f"Microfone ({disp_mic} disponíveis)")

st.divider()

# --- ETAPA 2: FORMULÁRIO DE RESERVA ---
with st.form("form_reserva"):
    # Resposta à sua pergunta: selectbox não permite que o usuário digite, ele SÓ PODE ESCOLHER.
    professor = st.selectbox("👩‍🏫 Professor(a):", ["-- Selecione --"] + sorted(LISTA_PROFESSORES))
    
    if not espacos_disponiveis:
        st.error("⚠️ Todos os espaços já estão ocupados neste horário!")
        espaco = st.selectbox("📍 Espaço:", ["Nenhum (Só Equipamento)"])
    else:
        espaco = st.selectbox("📍 Espaço:", espacos_disponiveis)
    
    if not opcoes_equip:
        st.warning("⚠️ Todos os equipamentos já estão emprestados neste horário.")
        equipamentos = st.multiselect("💻 Equipamentos:", ["Nenhum disponível"])
    else:
        # multiselect permite escolher mais de um!
        equipamentos = st.multiselect("💻 Equipamentos (Opcional):", opcoes_equip)
    
    observacoes = st.text_area("📝 Observações (Opcional):", placeholder="Ex: Deixar o datashow na sala dos professores...")

    enviar = st.form_submit_button("✅ Confirmar Reserva", use_container_width=True)

    if enviar:
        if professor == "-- Selecione --":
            st.warning("Por favor, selecione seu nome na lista.")
        else:
            # Limpa os nomes dos equipamentos para salvar limpo no banco (ex: tira o "(4 disponíveis)")
            equip_limpos = [e.split(" (")[0] for e in equipamentos if "disponíve" in e]
            equip_str = ", ".join(equip_limpos) if equip_limpos else "Nenhum"

            dados = {
                "data_reserva": str(data_selecionada),
                "aula": aula_selecionada,
                "professor": professor,
                "espaco": espaco,
                "equipamentos": equip_str,
                "observacoes": observacoes
            }

            try:
                supabase.table("reservas").insert(dados).execute()
                st.success("🎉 Reserva efetuada com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
