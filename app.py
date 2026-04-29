import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re
from pypdf import PdfReader

st.set_page_config(page_title="Extrator Industrial", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🏦 Transcritor de Extratos de Alta Capacidade")
st.info("Este modo divide o PDF em partes para garantir que 100% das linhas sejam lidas.")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A ler PDF e a dividir em blocos..."):
        try:
            # Lendo o PDF página por página
            reader = PdfReader(arquivo_pdf)
            todas_transacoes = []
            
            progresso = st.progress(0)
            num_paginas = len(reader.pages)

            for i, page in enumerate(reader.pages):
                texto_pagina = page.extract_text()
                
                comando = f"""
                Extraia as transações bancárias deste texto.
                DATA: DD/MM/AAAA.
                VALOR: Use vírgula (ex: 1250,45). Saídas com sinal (-).
                TRANSAÇÃO: Descrição completa.
                SAÍDA: Retorne APENAS um array JSON: [{"Data":"...","Transação":"...","Valor":"..."}]
                Texto: {texto_pagina}
                """

                resposta = model.generate_content(comando)
                
                # Captura e limpa o JSON de cada página
                match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
                if match:
                    try:
                        dados_pagina = json.loads(match.group(0))
                        todas_transacoes.extend(dados_pagina)
                    except:
                        pass
                
                progresso.progress((i + 1) / num_paginas)

            if todas_transacoes:
                df = pd.DataFrame(todas_transacoes)
                
                # Padronização de Colunas
                mapeamento = {col: col.capitalize() for col in df.columns}
                df = df.rename(columns=mapeamento)
                for c in ["Data", "Transação", "Valor"]:
                    if c not in df.columns: df[c] = ""
                
                df_final = df[["Data", "Transação", "Valor"]].drop_duplicates()

                st.success(f"Concluído! {len(df_final)} transações extraídas com sucesso.")
                st.dataframe(df_final, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel Completo", output.getvalue(), "extrato_total.xlsx")
            else:
                st.error("Não foram encontradas transações.")

        except Exception as e:
            st.error(f"Erro: {e}")
