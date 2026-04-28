import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

# Configuração visual
st.set_page_config(page_title="Extrator de Extratos", layout="wide")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# Segurança da Chave API
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Erro: Chave não encontrada nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- MÁGICA: DESCOBERTA AUTOMÁTICA DO MODELO ---
try:
    # Procura qual modelo está liberado para a sua chave
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Tenta priorizar o 'flash' que é mais rápido, se não usa o primeiro da lista
    modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
    model = genai.GenerativeModel(modelo_final)
except Exception as e:
    st.error(f"Erro ao conectar com a IA: {e}")
    st.stop()

st.title("🏦 Transcritor de Extratos")
st.write(f"*(Conectado via: {modelo_final})*")

arquivo_pdf = st.file_uploader("Arraste o extrato em PDF aqui", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A transcrever..."):
        try:
            pdf_data = arquivo_pdf.read()
            
           comando = """
Age como um especialista em conciliação bancária. Transcreva este extrato seguindo estas diretrizes rigorosas:

1. RECONHECIMENTO DE TRANSAÇÃO (Foto 1 - Múltiplas Colunas):
   - Existem várias colunas que compõem a descrição (ex: 'Histórico', 'Documento', 'Origem'). 
   - Deves concatenar (juntar) o conteúdo de TODAS as colunas amarelas de uma linha numa única célula na coluna 'Transação'.
   - Exemplo: Se 'Histórico' diz 'PIX' e 'Origem' diz 'João', a Transação deve ser 'PIX - João'.

2. TRATAMENTO DE QUEBRAS DE LINHA (Foto 2 - Descrições Longas):
   - Se uma transação ocupar mais de uma linha física no papel, une-as. 
   - Não cries uma nova linha na tabela se não houver uma nova data ou um novo valor associado. 
   - Toda a descrição espalhada por várias linhas deve ser agrupada na mesma 'Transação'.

3. LÓGICA DE VALORES (Sinais C/D):
   - Se o valor vier acompanhado de 'D' ou estiver numa coluna de 'Débito', guarda-o como NEGATIVO (ex: -150.00).
   - Se vier acompanhado de 'C' ou estiver numa coluna de 'Crédito', guarda-o como POSITIVO (ex: 150.00).
   - Remove símbolos de moeda (R$, €), mas mantém a vírgula ou ponto decimal corretamente.

4. FORMATO DE SAÍDA:
   - Retorna APENAS um array JSON puro.
   - Chaves: "Data", "Transação", "Valor".
   - Ignora cabeçalhos, saldos totais e rodapés.
"""
            
            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            
            match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
            lista_dados = json.loads(match.group(0) if match else resposta.text)
            
            df = pd.DataFrame(lista_dados)[["Data", "Transação", "Valor"]]
            st.dataframe(df, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Baixar Excel", output.getvalue(), "extrato_final.xlsx")
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
            st.info("A IA não conseguiu estruturar os dados. Verifique se o PDF é legível.")
