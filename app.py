import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

st.set_page_config(page_title="Extrator Express", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- MÁGICA: BUSCA AUTOMÁTICA DE MODELO ---
@st.cache_resource
def get_model():
    try:
        # Lista todos os modelos que você tem permissão de usar
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Retorna o primeiro que encontrar (geralmente o Flash ou Pro)
                return genai.GenerativeModel(m.name)
    except Exception as e:
        st.error(f"Erro ao listar modelos: {e}")
        return None

model = get_model()

st.title("⚡ Transcritor de Extratos Express")
st.write(f"*(Modelo ativo: {model.model_name if model else 'Nenhum'})*")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf and model:
    with st.spinner("Processando em alta velocidade..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            comando = """
            Extraia as transações deste extrato.
            REGRAS:
            1. DATA: DD/MM/AAAA.
            2. VALOR: Use VÍRGULA como separador decimal (ex: 1250,45). 
               - Débito/Saída: sinal de menos (ex: -50,00).
               - Crédito/Entrada: positivo (ex: 100,00).
            3. TRANSAÇÃO: Junte descrições de múltiplas linhas e colunas em uma só.
            SAÍDA: Retorne APENAS o array JSON puro com chaves "Data", "Transação", "Valor".
            """

            resposta = model.generate_content([
                comando,
                {'mime_type': 'application/pdf', 'data': pdf_data}
            ])
            
            match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
            
            if match:
                lista_dados = json.loads(match.group(0))
                df = pd.DataFrame(lista_dados)
                df = df[["Data", "Transação", "Valor"]]

                st.success("Transcrição concluída!")
                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button("📥 Baixar Planilha em BRL", output.getvalue(), "extrato_brl.xlsx")
            else:
                st.error("Não foi possível formatar os dados. Veja a resposta da IA:")
                st.write(resposta.text)
        except Exception as e:
            st.error(f"Erro: {e}")
