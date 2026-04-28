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
            comando = "Transcreva as transações deste extrato bancário. Una descrições de várias linhas. Una Crédito/Débito em 'Valor'. Retorne APENAS um array JSON puro com chaves: 'Data', 'Transação', 'Valor'."
            
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
