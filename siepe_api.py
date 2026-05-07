import requests
import logging
import pandas as pd  # <--- CORREÇÃO: O import que faltava

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
        Realiza o login. Adicionamos um GET inicial para garantir que o cookie 
        da sessão seja gerado antes de enviar a senha.
        """
        try:
            # Garante que a página de login carregue primeiro
            self.session.get(f"{self.base_url}/GerenciadorAcessoWeb/login.do", timeout=10)

            url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin"
            payload = {'login': usuario, 'senha': senha}
            
            headers_login = {'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do"}
            response = self.session.post(url_login, data=payload, headers=headers_login, timeout=15)
            
            if response.status_code == 200:
                # O SIEPE às vezes retorna 200 mas com mensagem de erro no texto
                if "inválido" in response.text.lower():
                    return False, "Usuário ou senha inválidos no SIEPE."
                return True, "Login realizado."
            return False, f"Erro de conexão: {response.status_code}"
        except Exception as e:
            return False, f"Falha técnica: {str(e)}"

    def enviar_notas_siepe(self, payload_dados):
        url_save = f"{self.base_url}/GerenciadorAcessoWeb/EWServlet.ew"
        headers_save = {
            'Referer': 'https://www.siepe.educacao.pe.gov.br/diarioclasse/DiarioClasse.do'
        }
        try:
            response = self.session.post(url_save, data=payload_dados, headers=headers_save, timeout=20)
            if response.status_code == 200:
                return True, "Notas integradas com sucesso!"
            return False, f"Erro no servidor SIEPE: {response.status_code}"
        except Exception as e:
            return False, f"Falha de conexão: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        """
        Mapeia os dados do Streamlit para os campos do SIEPE.
        """
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

        for _, row in df_view.iterrows():
            # Usa o aluno_id que é o ID interno do SIEPE para cada estudante
            id_aluno = str(row['aluno_id'])
            
            def fmt(v): 
                return str(v).replace('.', ',') if (v is not None and v > 0) else ""

            payload[f"nota_1_{id_aluno}"] = fmt(row['AT1'])
            payload[f"nota_2_{id_aluno}"] = fmt(row['AT2'])
            payload[f"nota_3_{id_aluno}"] = fmt(row['AT3'])
            payload[f"nota_4_{id_aluno}"] = fmt(row['AT4'])
            payload[f"nota_5_{id_aluno}"] = fmt(row['AT5'])
            payload[f"nota_7_{id_aluno}"] = fmt(row['N2'])

        return self.enviar_notas_siepe(payload)