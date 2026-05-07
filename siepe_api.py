import requests
import pandas as pd  # Importação essencial para evitar "pd is not defined"
import logging

class SiepeClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://www.siepe.educacao.pe.gov.br"
        
        # User-agent atualizado para simular um navegador moderno
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.base_url,
            'Connection': 'keep-alive'
        })

    def fazer_login(self, usuario, senha):
        """
        Realiza o login no SIEPE. O GET inicial é necessário para 
        estabelecer os cookies de sessão antes do POST de login.
        """
        try:
            self.session.get(f"{self.base_url}/GerenciadorAcessoWeb/login.do", timeout=10)

            url_login = f"{self.base_url}/GerenciadorAcessoWeb/segurancaAction.do?actionType=ajaxLogin"
            payload = {'login': usuario, 'senha': senha}
            
            headers_login = {'Referer': f"{self.base_url}/GerenciadorAcessoWeb/login.do"}
            response = self.session.post(url_login, data=payload, headers=headers_login, timeout=15)
            
            if response.status_code == 200:
                if "inválido" in response.text.lower() or "erro" in response.text.lower():
                    return False, f"SIEPE: {response.text[:50]}"
                return True, "Login realizado com sucesso."
            return False, f"Status erro: {response.status_code}"
        except Exception as e:
            return False, f"Falha técnica no login: {str(e)}"

    def enviar_notas_siepe(self, payload_dados):
        """
        Envia o payload de notas para o servlet do SIEPE (EWServlet.ew).
        """
        url_save = f"{self.base_url}/GerenciadorAcessoWeb/EWServlet.ew"
        headers_save = {
            'Referer': 'https://www.siepe.educacao.pe.gov.br/diarioclasse/DiarioClasse.do'
        }
        try:
            response = self.session.post(url_save, data=payload_dados, headers=headers_save, timeout=25)
            if response.status_code == 200:
                return True, "Notas integradas com sucesso!"
            return False, f"Erro no servidor: {response.status_code}"
        except Exception as e:
            return False, f"Erro de rede: {str(e)}"

    def sincronizar_dataframe_ao_siepe(self, df_view, ids_contexto):
        """
        Transforma o DataFrame em um payload compatível com o portal.
        """
        payload = {
            "idAbaSelecionada": "2",
            "idAbaSelecionadaPedagogico": "2",
            "hdnMetodosCarregados": "selecionarAba",
            "ddlSerieNotaFalta": ids_contexto.get('turma_id'), # ID 2483 da imagem
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
            # Tenta usar o ID do SIEPE se disponível, senão usa o aluno_id
            id_aluno = str(row.get('id_siepe', row.get('aluno_id')))
            
            def fmt(v): 
                # Converte para string com vírgula se for maior que zero
                try:
                    val = float(v)
                    return str(val).replace('.', ',') if val > 0 else ""
                except: return ""

            payload[f"nota_1_{id_aluno}"] = fmt(row['AT1'])
            payload[f"nota_2_{id_aluno}"] = fmt(row['AT2'])
            payload[f"nota_3_{id_aluno}"] = fmt(row['AT3'])
            payload[f"nota_4_{id_aluno}"] = fmt(row['AT4'])
            payload[f"nota_5_{id_aluno}"] = fmt(row['AT5'])
            payload[f"nota_7_{id_aluno}"] = fmt(row['N2']) # N2 mapeado para nota_7

        return self.enviar_notas_siepe(payload)