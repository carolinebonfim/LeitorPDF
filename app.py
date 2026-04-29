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

arquivo_pdf = st.file_uploader("Arraste o extrato aqui", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A analisar..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            comando = """
            Transcreva as transações deste extrato seguindo estas REGRAS:
            1. Una descrições de várias linhas numa única frase.
            2. Una Crédito/Débito em 'Valor' (Débito com sinal -, Crédito com sinal +).
            3. Formato Data: DD/MM/AAAA.
            4. Retorne APENAS o array JSON puro com chaves: 'Data', 'Transação', 'Valor'.
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            texto_ia = resposta.text
            
            # --- NOVO SISTEMA DE CAPTURA SEGURO ---
            match = re.search(r'\[.*\]', texto_ia, re.DOTALL)
            
            if match:
                json_limpo = match.group(0)
                lista_dados = json.loads(json_limpo)
                df = pd.DataFrame(lista_dados)
                
                # Garante colunas certas
                for c in ["Data", "Transação", "Valor"]:
                    if c not in df.columns: df[c] = ""
                
                st.dataframe(df[["Data", "Transação", "Valor"]], use_container_width=True)
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), "extrato.xlsx")
            else:
                # Se não achou JSON, mostra o que a IA disse
                st.warning("A IA não encontrou transações ou não formatou como tabela.")
                with st.expander("Ver resposta bruta da IA"):
                    st.write(texto_ia)

        except Exception as e:
            st.error(f"Erro: {e}")
