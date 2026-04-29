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

@st.cache_resource
def get_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            return genai.GenerativeModel(m.name, generation_config={"temperature": 0})
    return None

model = get_model()

st.title("🏦 Transcritor de Extratos de Alta Capacidade")
st.write("Processamento página a página para garantir a leitura total.")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf and model:
    with st.spinner("A processar páginas..."):
        try:
            reader = PdfReader(arquivo_pdf)
            todas_transacoes = []
            
            barra_progresso = st.progress(0)
            num_paginas = len(reader.pages)

            for i, pagina in enumerate(reader.pages):
                texto_extraido = pagina.extract_text()
                
                # Comando limpo para evitar erro de string
                prompt = f"Extraia as transações deste texto para um array JSON com chaves Data, Transação e Valor. Use virgula nos decimais. Texto: {texto_extraido}"

                resposta = model.generate_content(prompt)
                
                # Procura o JSON na resposta
                match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
                if match:
                    try:
                        dados = json.loads(match.group(0))
                        todas_transacoes.extend(dados)
                    except:
                        continue
                
                barra_progresso.progress((i + 1) / num_paginas)

            if todas_transacoes:
                df = pd.DataFrame(todas_transacoes)
                
                # Padronizar nomes de colunas (ignora maiúsculas/minúsculas)
                df.columns = [c.capitalize() for c in df.columns]
                
                # Garantir as colunas desejadas
                for col in ["Data", "Transação", "Valor"]:
                    if col not in df.columns:
                        # Tenta achar colunas com nomes parecidos
                        for real_col in df.columns:
                            if col.lower()[:3] in real_col.lower():
                                df = df.rename(columns={real_col: col})
                
                # Filtra apenas o necessário
                colunas_finais = [c for c in ["Data", "Transação", "Valor"] if c in df.columns]
                df_final = df[colunas_finais].drop_duplicates()

                st.success(f"Concluído! {len(df_final)} linhas extraídas.")
                st.dataframe(df_final, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel Completo", output.getvalue(), "extrato_completo.xlsx")
            else:
                st.warning("Nenhuma transação identificada.")

        except Exception as e:
            st.error(f"Erro técnico: {e}")
