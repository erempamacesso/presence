"""Utilitários para gerar PDFs de forma segura para o Streamlit."""


def pdf_para_bytes(pdf):
    """Converte a saída de um FPDF em bytes, qualquer que seja a versão da biblioteca.

    - fpdf2 retorna bytearray  -> converte para bytes
    - fpdf antigo retorna str  -> codifica em latin-1
    O st.download_button só aceita bytes, por isso tudo passa por aqui.
    """
    # dest="S" é necessário no fpdf antigo; no fpdf2 é aceito e ignorado
    try:
        saida = pdf.output(dest="S")
    except TypeError:
        saida = pdf.output()
    if isinstance(saida, str):
        return saida.encode("latin-1", errors="replace")
    return bytes(saida)
