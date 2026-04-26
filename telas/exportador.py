from docx import Document
from io import BytesIO
import re

def limpar_conteudo(dado):
    """
    Limpa dicionários ou tags HTML para o Word ficar perfeito e sem sujeiras.
    """
    if isinstance(dado, dict):
        return dado.get('texto', list(dado.values())[0] if dado else "")
    
    # Remove as tags HTML (como <p>, <b>, etc)
    texto_limpo = re.sub(r'<[^>]+>', '', str(dado))
    return texto_limpo.strip()

def gerar_prova_word(titulo_prova, questoes):
    """
    Função (Motor) que cria o documento Word em memória usando as questões do banco.
    """
    doc = Document()
    
    # ==========================================
    # 1. CABEÇALHO E QUESTÕES DA PROVA
    # ==========================================
    doc.add_heading(f'Avaliação: {titulo_prova}', 0)
    doc.add_paragraph('Nome: __________________________________________________ Turma: _______')
    doc.add_paragraph('\n') 

    for i, q in enumerate(questoes, 1):
        enunciado = limpar_conteudo(q.get('enunciado', ''))
        doc.add_paragraph(f"{i}) {enunciado}")
        
        opcoes = q.get('alternativas') or q.get('opcoes') or {} 
        
        if opcoes:
            for letra in ["A", "B", "C", "D", "E"]:
                if letra in opcoes:
                    texto_alt = limpar_conteudo(opcoes[letra])
                    doc.add_paragraph(f"    ({letra}) {texto_alt}")
        
        doc.add_paragraph('\n') 

    # ==========================================
    # 2. GABARITO (PÁGINA SEPARADA)
    # ==========================================
    doc.add_page_break() # Força o Word a pular para uma página nova
    doc.add_heading('Gabarito - Uso Exclusivo da Coordenação/Professor', 1)
    doc.add_paragraph('\n')

    for i, q in enumerate(questoes, 1):
        # ATENÇÃO: O código tenta achar a resposta correta pelos nomes mais comuns de banco de dados.
        # Se no seu Supabase a coluna se chamar diferente, basta trocar aqui!
        resposta_correta = q.get('resposta_correta') or q.get('gabarito') or q.get('resposta') or "Não informada no banco"
        
        # Adiciona a linha do gabarito em negrito
        p = doc.add_paragraph()
        p.add_run(f"Questão {i}: ").bold = True
        p.add_run(f"Alternativa {resposta_correta}")

    # ==========================================
    # 3. SALVAMENTO EM MEMÓRIA
    # ==========================================
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    
    return buffer