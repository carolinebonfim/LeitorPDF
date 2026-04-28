import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

# Configuração visual "Limpa"
st.set_page_config(page_title="Extrator de Extratos", layout="wide")

# Esconder menus desnecessários
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# Segurança: A chave API fica escondida nos "Secrets" do site
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("📑 Transcritor de Extratos")
st.write("Transcreve Data, Transação e Valor automaticamente.")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A ler documento..."):
        try:
            pdf_data = arquivo_pdf.read()
            comando = """
            Transcreva as transações deste extrato. 
            Regras: 
            1. Una descrições de várias linhas na coluna 'Transação'.
            2. Una Crédito/Débito na coluna 'Valor' (saídas com sinal de menos).
            3. Formato Data: DD/MM/AAAA.
            4. Retorne APENAS um array JSON puro com chaves: 'Data', 'Transação', 'Valor'.
            """
            
            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            
            # Limpeza para garantir que apenas a tabela seja lida
            match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
            lista_dados = json.loads(match.group(0) if match else resposta.text)
            
            df = pd.DataFrame(lista_dados)[["Data", "Transação", "Valor"]]
            st.dataframe(df, use_container_width=True)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button("📥 Descarregar Excel", output.getvalue(), "extrato.xlsx")
        except Exception as e:
            st.error(f"Erro: {e}")