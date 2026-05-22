import requests
import streamlit as st
import time
from supabase import create_client
import urllib3
import os
import toml

# Desativa avisos de SSL inseguro caso a verificação seja desabilitada
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================
# SECRETS
# =========================================

try:
    # Tenta carregar do Streamlit (Produção)
    TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    SUPABASE_URL = st.secrets["SUPABASE_URL_ALUNOS"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY_ALUNOS"]
except:
    # Fallback para local
    secrets = toml.load(".streamlit/secrets.toml")
    TOKEN = secrets["TELEGRAM_BOT_TOKEN"]
    SUPABASE_URL = secrets["SUPABASE_URL_ALUNOS"]
    SUPABASE_KEY = secrets["SUPABASE_KEY_ALUNOS"]

# =========================================
# SUPABASE
# =========================================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================
# SESSÃO HTTP (Melhora performance e resolve SSL)
# =========================================
session = requests.Session()
# Se o erro persistir, mude para False para ignorar a validação SSL da rede local
session.verify = True

# =========================================
# FUNÇÕES AUXILIARES
# =========================================


def buscar_resumo_estudantes(chat_id):
    """Busca nomes dos estudantes vinculados ao chat_id para exibir no menu"""
    resultado = (
        supabase.table("responsaveis_oficiais")
        .select("cpf_responsavel")
        .eq("telegram_chat_id", chat_id)
        .limit(1)
        .execute()
    )
    if not resultado.data:
        return ""

    cpf = resultado.data[0]["cpf_responsavel"]
    vinculos = (
        supabase.table("responsaveis_oficiais")
        .select("numero_matricula")
        .eq("cpf_responsavel", cpf)
        .execute()
    )

    nomes = []
    for v in vinculos.data:
        aluno = (
            supabase.table("alunos")
            .select("nome")
            .eq("numero_matricula", v["numero_matricula"])
            .limit(1)
            .execute()
        )
        if aluno.data:
            nomes.append(f"• {aluno.data[0]['nome']}")

    if nomes:
        return "\nEstudante(s) vinculado(s):\n" + "\n".join(nomes)
    return "\nNenhum estudante vinculado ainda."


def enviar_mensagem(chat_id, texto, reply_markup=None):
    try:
        payload = {"chat_id": chat_id, "text": texto}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json=payload)
    except Exception as e:
        print(f"Erro ao enviar: {e}")


# =========================================
# MENU INLINE
# =========================================

inline_keyboard = {
    "inline_keyboard": [
        [{"text": "📋 Meus estudantes", "callback_data": "meus_estudantes"}],
        [{"text": "📈 Ver atrasos", "callback_data": "ver_atrasos"}],
        [{"text": "🔔 Notificações", "callback_data": "notificacoes"}],
        [{"text": "🛑 Sair", "callback_data": "sair"}],
    ]
}

# =========================================
# OFFSET
# =========================================

offset = 0

print("🤖 Bot online...")

# =========================================
# LOOP PRINCIPAL
# =========================================

while True:

    try:

        # =================================
        # GET UPDATES
        # =================================

        url_updates = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        response = session.get(url_updates, params={"offset": offset, "timeout": 30})

        dados = response.json()

        if "result" not in dados:
            erro_msg = dados.get("description", "Sem descrição")
            print(f"⚠️ Resposta inesperada do Telegram: {erro_msg}")

            # Trata especificamente o erro de conflito (múltiplas instâncias)
            if "Conflict" in erro_msg:
                print(
                    "🚨 ERRO DE CONFLITO: Outra instância deste Bot está rodando em algum lugar."
                )
                time.sleep(5)
            else:
                time.sleep(2)
            continue

        # =================================
        # PROCESSA RESULTADOS
        # =================================

        for item in dados["result"]:

            offset = item["update_id"] + 1

            # =============================
            # MENSAGENS
            # =============================

            if "message" in item:

                mensagem = item["message"].get("text", "")

                chat_id = str(item["message"]["chat"]["id"])

                print(f"Mensagem: {mensagem}")

                # =========================
                # START
                # =========================

                if mensagem == "/start":

                    # Verifica se este Chat ID já está vinculado a algum responsável
                    checagem = (
                        supabase.table("responsaveis_oficiais")
                        .select("nome_responsavel")
                        .eq("telegram_chat_id", chat_id)
                        .limit(1)
                        .execute()
                    )

                    if checagem.data:
                        nome = checagem.data[0]["nome_responsavel"]
                        resumo = buscar_resumo_estudantes(chat_id)
                        resposta = f"Olá, {nome}! 👋\n{resumo}\n\nO que deseja consultar agora?"
                        enviar_mensagem(chat_id, resposta, inline_keyboard)
                    else:
                        resposta = """
Bem-vindo ao sistema EREMPAM!

Ainda não identificamos sua conta.
Por favor, digite apenas os **números do seu CPF** para vincular seu acesso.
"""
                        enviar_mensagem(chat_id, resposta)

                # =========================
                # CPF
                # =========================

                elif mensagem.isdigit() and len(mensagem) == 11:

                    cpf = mensagem.zfill(11)

                    resultado = (
                        supabase.table("responsaveis_oficiais")
                        .select("nome_responsavel")
                        .eq("cpf_responsavel", cpf)
                        .limit(1)
                        .execute()
                    )

                    reply_markup_to_send = (
                        None  # Inicializa o reply_markup para ser definido abaixo
                    )
                    # =====================
                    # CPF ENCONTRADO
                    # =====================

                    if resultado.data:

                        nome = resultado.data[0]["nome_responsavel"]

                        (
                            supabase.table("responsaveis_oficiais")
                            .update({"telegram_chat_id": chat_id})
                            .eq("cpf_responsavel", cpf)
                            .execute()
                        )

                        # Busca os estudantes vinculados a este CPF
                        estudantes_vinculados_matriculas = (
                            supabase.table("responsaveis_oficiais")
                            .select("numero_matricula")
                            .eq("cpf_responsavel", cpf)
                            .execute()
                        )

                        student_buttons = []
                        if estudantes_vinculados_matriculas.data:
                            for (
                                aluno_matricula_data
                            ) in estudantes_vinculados_matriculas.data:
                                matricula = aluno_matricula_data["numero_matricula"]
                                # Busca o ID e nome do aluno na tabela 'alunos'
                                aluno_info = (
                                    supabase.table("alunos")
                                    .select("id, nome")
                                    .eq("numero_matricula", matricula)
                                    .limit(1)
                                    .execute()
                                )
                                if aluno_info.data:
                                    aluno_id = aluno_info.data[0]["id"]
                                    aluno_nome = aluno_info.data[0]["nome"]
                                    student_buttons.append(
                                        [
                                            {
                                                "text": aluno_nome,
                                                "callback_data": f"ver_atrasos_aluno:{aluno_id}",
                                            }
                                        ]
                                    )

                        if student_buttons:
                            # Adiciona um botão para voltar ao menu principal
                            student_buttons.append(
                                [
                                    {
                                        "text": "⬅️ Voltar ao Menu Principal",
                                        "callback_data": "main_menu",
                                    }
                                ]
                            )
                            student_selection_keyboard = {
                                "inline_keyboard": student_buttons
                            }

                            resposta = f"""
✅ Vinculação realizada com sucesso.

Responsável:
{nome}
"""
                            enviar_mensagem(chat_id, resposta, inline_keyboard)
                        else:
                            resposta = f"""
✅ Vinculação realizada com sucesso.

Responsável:
{nome}
"""
                            enviar_mensagem(chat_id, resposta, inline_keyboard)

                    # =====================
                    # CPF NÃO ENCONTRADO
                    # =====================

                    else:
                        enviar_mensagem(
                            chat_id,
                            "❌ CPF não encontrado. Verifique os números digitados ou fale com a secretaria.",
                        )

            # =============================
            # CALLBACK BUTTONS
            # =============================

            elif "callback_query" in item:

                callback = item["callback_query"]

                data = callback["data"]

                chat_id = str(callback["message"]["chat"]["id"])

                print(f"Botão: {data}")

                resposta = ""  # Inicializa a mensagem de resposta
                reply_markup_to_send = None  # Inicializa o reply_markup

                # =========================
                # MEUS ESTUDANTES
                # =========================

                if data == "meus_estudantes":

                    resultado = (
                        supabase.table("responsaveis_oficiais")
                        .select("cpf_responsavel")
                        .eq("telegram_chat_id", chat_id)
                        .limit(1)
                        .execute()
                    )

                    if not resultado.data:

                        resposta = """
❌ Responsável não encontrado.
"""
                        reply_markup_to_send = inline_keyboard

                    else:

                        cpf = resultado.data[0]["cpf_responsavel"]

                        estudantes = (
                            supabase.table("responsaveis_oficiais")
                            .select("numero_matricula, turma_vinculo")
                            .eq("cpf_responsavel", cpf)
                            .execute()
                        )

                        resposta = "📋 Seus estudantes:\n\n"

                        for aluno in estudantes.data:

                            matricula = aluno["numero_matricula"]

                            turma = aluno["turma_vinculo"]

                            aluno_real = (
                                supabase.table("alunos")
                                .select("nome")
                                .eq("numero_matricula", matricula)
                                .limit(1)
                                .execute()
                            )

                            nome_aluno = "Aluno não encontrado"

                            if aluno_real.data:

                                nome_aluno = aluno_real.data[0]["nome"]

                            resposta += f"👦 {nome_aluno}\n" f"🏫 {turma}\n\n"
                        reply_markup_to_send = inline_keyboard

                # =========================
                # VER ATRASOS
                # =========================

                elif data == "ver_atrasos":

                    resultado = (
                        supabase.table("responsaveis_oficiais")
                        .select("cpf_responsavel")
                        .eq("telegram_chat_id", chat_id)
                        .limit(1)
                        .execute()
                    )

                    if not resultado.data:

                        resposta = """
❌ Responsável não encontrado.
"""
                        reply_markup_to_send = inline_keyboard

                    else:

                        cpf = resultado.data[0]["cpf_responsavel"]

                        estudantes = (
                            supabase.table("responsaveis_oficiais")
                            .select("numero_matricula")
                            .eq("cpf_responsavel", cpf)
                            .execute()
                        )

                        resposta = "📈 Últimos atrasos:\n\n"

                        encontrou = False

                        for aluno in estudantes.data:

                            matricula = aluno["numero_matricula"]

                            # Primeiro, resolvemos o ID interno do aluno a partir da matrícula
                            aluno_info = (
                                supabase.table("alunos")
                                .select("id")
                                .eq("numero_matricula", matricula)
                                .limit(1)
                                .execute()
                            )

                            if not aluno_info.data:
                                continue

                            id_real = str(aluno_info.data[0]["id"])

                            atrasos = (
                                supabase.table("atrasos_alunos")
                                .select("aluno_nome, turma, data_atraso, hora_chegada")
                                .eq("aluno_id", id_real)
                                .limit(3)
                                .execute()
                            )

                            for atraso in atrasos.data:

                                encontrou = True

                                resposta += (
                                    f"👦 {atraso['aluno_nome']}\n"
                                    f"🏫 {atraso['turma']}\n"
                                    f"📅 {atraso['data_atraso']}\n"
                                    f"⏰ {atraso['hora_chegada']}\n\n"
                                )

                        reply_markup_to_send = inline_keyboard
                        if not encontrou:

                            resposta = """
✅ Nenhum atraso encontrado.
"""
                # =========================
                # NOTIFICAÇÕES
                # =========================

                elif data == "notificacoes":

                    resposta = """
🔔 Notificações já estão ativadas.
"""
                    reply_markup_to_send = inline_keyboard

                # =========================
                # SAIR
                # =========================

                elif data == "sair":

                    (
                        supabase.table("responsaveis_oficiais")
                        .update({"telegram_chat_id": None})
                        .eq("telegram_chat_id", chat_id)
                        .execute()
                    )

                    resposta = """
✅ Seu Telegram foi desvinculado com sucesso.
"""
                    reply_markup_to_send = None  # Sem teclado inline após desvincular

                # =========================
                # ENVIA RESPOSTA
                # =========================

                if resposta:  # Envia a mensagem apenas se houver uma resposta definida
                    json_data = {"chat_id": chat_id, "text": resposta}
                    if reply_markup_to_send is not None:
                        json_data["reply_markup"] = reply_markup_to_send
                    session.post(
                        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                        json=json_data,
                    )

    except Exception as erro:

        print(f"Erro: {erro}")

    time.sleep(1)
