import requests
import logging
import pandas as pd  # <--- Faltava isso aqui!

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.base_url,
            'Connection': 'keep-alive'
        })

    def fazer_login(self, usuario, senha):
        """
        Realiza o login no sistema do SIEPE.
        """
        # Passo opcional mas recomendado: carregar a página inicial para pegar cookies básicos
        self.session.get(f"{self.base_url}/GerenciadorAcessoWeb/login.do", timeout=10)

        url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin"
        payload = {
            'login': usuario,
            'senha': senha
        }
        try:
            headers_login = {'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do"}
            response = self.session.post(url_login, data=payload, headers=headers_login, timeout=15)
            
            # O SIEPE costuma retornar "OK" ou um JSON no texto se der certo
            if response.status_code == 200:
                # Se o login falhar mesmo com 200, ele geralmente avisa no corpo da resposta
                if "inválido" in response.text.lower() or "erro" in response.text.lower():
                    return False, "Usuário ou senha inválidos segundo o SIEPE."
                return True, "Login processado."
            return False, f"Erro de comunicação. Status: {response.status_code}"
        except Exception as e:
            return False, str(e)

    def enviar_notas_siepe(self, payload_dados):
        url_save = f"{self.base_url}/GerenciadorAcessoWeb/EWServlet.ew"
        headers_save = {
            'Referer': 'https://www.siepe.educacao.pe.gov.br/diarioclasse/DiarioClasse.do'
        }
        try:
            response = self.session.post(url_save, data=payload_dados, headers=headers_save, timeout=20)
            if response.status_code == 200:
                return True, "Notas integradas com sucesso!"
            return False, f"Servidor retornou erro {response.status_code}"
        except Exception as e:
            return False, f"Falha de conexão: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        # O payload carrega as configurações da turma e disciplina que você capturou no navegador
        payload = {
            "idAbaSelecionada": "2",
            "idAbaSelecionadaPedagogico": "2",
            "hdnMetodosCarregados": "selecionarAba",
            "ddlSerieNotaFalta": ids_contexto.get('turma_id'),
            "ddlPeriodo": ids_contexto.get('bimestre', "1"),
            "ddlDisciplina": ids_contexto.get('disciplina_id'),
            "inputConceitos": "null",
            "EWBase": ids_contexto.get('ew_base'),
            "EWId": ids_contexto.get('ew_id'),
            "EWAction": "raiseEvent",
            "EWMethod": "btnGravarNotasFaltasDisciplina_onclick",
            "dummy": ids_contexto.get('dummy')
        }

        # Varre cada linha da tabela (df_view) para preencher as notas de cada aluno
        for _, row in df_view.iterrows():
            # Tenta usar 'id_siepe' (se você já tiver no banco), senão usa o 'aluno_id' padrão
            id_aluno = str(row['id_siepe']) if 'id_siepe' in row else str(row['aluno_id'])
            
            # Função para converter o ponto (.) do Python para a vírgula (,) do SIEPE
            def fmt(v): 
                return str(v).replace('.', ',') if (v is not None and v > 0) else ""

            # Mapeia as notas das ATs e da Prova (N2 vai no campo nota_7)
            payload[f"nota_1_{id_aluno}"] = fmt(row['AT1'])
            payload[f"nota_2_{id_aluno}"] = fmt(row['AT2'])
            payload[f"nota_3_{id_aluno}"] = fmt(row['AT3'])
            payload[f"nota_4_{id_aluno}"] = fmt(row['AT4'])
            payload[f"nota_5_{id_aluno}"] = fmt(row['AT5'])
            payload[f"nota_7_{id_aluno}"] = fmt(row['N2'])

        # Envia o pacote completo de notas para o servidor
        return self.enviar_notas_siepe(payload)