import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

st.set_page_config(page_title="Extrator Express", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            return genai.GenerativeModel(m.name, generation_config={"max_output_tokens": 8192, "temperature": 0})
    return None

model = get_model()

st.title("⚡ Transcritor de Extratos Bancários")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf:
    with st.spinner("Processando..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            comando = """
            Transcreva as transações deste extrato para um array JSON.
            Campos: "Data", "Transação", "Valor".
            REGRAS: 
            1. VALOR: Use vírgula (ex: "1.452,90"). Use sinal de menos para saídas.
            2. DATA: DD/MM/AAAA.
            3. TRANSAÇÃO: Junte as descrições longas.
            Retorne APENAS o JSON.
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            texto_ia = resposta.text
            
            match = re.search(r'\[.*\]', texto_ia, re.DOTALL)
            
            if match:
                json_final = match.group(0)
                # Tenta ler o JSON
                try:
                    df = pd.read_json(io.StringIO(json_final))
                except:
                    lista_dados = json.loads(json_final)
                    df = pd.DataFrame(lista_dados)

                # --- MÁGICA: PADRONIZAÇÃO DE COLUNAS ---
                # Isso converte qualquer nome que a IA inventou para o seu padrão
                mapeamento = {}
                for col in df.columns:
                    col_norm = col.lower().strip()
                    if 'dat' in col_norm: mapeamento[col] = "Data"
                    elif 'trans' in col_norm or 'desc' in col_norm or 'hist' in col_norm: mapeamento[col] = "Transação"
                    elif 'val' in col_norm: mapeamento[col] = "Valor"
                
                df = df.rename(columns=mapeamento)

                # Se mesmo assim faltar alguma, a gente cria vazia para não dar erro
                for esperado in ["Data", "Transação", "Valor"]:
                    if esperado not in df.columns:
                        df[esperado] = ""

                # Ordena e exibe apenas as 3 colunas desejadas
                df_final = df[["Data", "Transação", "Valor"]]

                st.success(f"Sucesso! {len(df_final)} linhas processadas.")
                st.dataframe(df_final, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel BRL", output.getvalue(), "extrato_final.xlsx")
            else:
                st.error("Não foi possível localizar os dados.")
                st.code(texto_ia)

        except Exception as e:
            st.error(f"Erro: {e}")
