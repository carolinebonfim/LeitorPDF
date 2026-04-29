import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

st.set_page_config(page_title="Extrator Pro", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

try:
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
    model = genai.GenerativeModel(modelo_final)
except:
    st.stop()

st.title("🏦 Transcritor de Extratos Bancários")

arquivo_pdf = st.file_uploader("Arraste o extrato em PDF aqui", type=["pdf"])

if arquivo_pdf:
    with st.spinner("Lendo PDF e filtrando transações..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            # Comando focado em ignorar cabeçalhos e saldos
            comando = """
            Analise este PDF e extraia APENAS as transações bancárias.
            
            REGRAS CRÍTICAS:
            1. IGNORE o cabeçalho, saldos anteriores, saldos do dia e rodapés.
            2. Foque nas linhas que contêm uma Data, uma Descrição/Histórico e um Valor.
            3. DESCRIÇÃO: Se a descrição ocupar mais de uma linha, junte-as em uma só.
            4. VALOR: Se o valor tiver 'D' ou for débito, use sinal de menos (-). Se for 'C' ou crédito, use sinal de mais (+).
            5. FORMATO: Retorne estritamente um array JSON com as chaves: "Data", "Transação", "Valor".
            6. Não escreva nenhuma palavra de explicação, apenas o JSON.
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            texto_ia = resposta.text
            
            # Localiza o JSON na resposta de forma robusta
            match = re.search(r'\[.*\]', texto_ia, re.DOTALL)
            
            if match:
                dados = json.loads(match.group(0))
                df = pd.DataFrame(dados)
                
                # Garante que as colunas existem
                for col in ["Data", "Transação", "Valor"]:
                    if col not in df.columns: df[col] = ""
                
                st.success("Extrato processado com sucesso!")
                st.dataframe(df[["Data", "Transação", "Valor"]], use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), "extrato_final.xlsx")
            else:
                st.error("A IA não conseguiu identificar a tabela de transações neste PDF.")
                with st.expander("Clique aqui para ver o que a IA leu"):
                    st.write(texto_ia)

        except Exception as e:
            st.error(f"Erro técnico: {e}")
