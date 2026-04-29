import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

# Configuração da Página para um visual mais profissional
st.set_page_config(page_title="Extrator Express", layout="wide")

# Estilo para esconder menus e focar na ferramenta
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Usando a versão FLASH que é a mais rápida de todas
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("⚡ Transcritor de Extratos Express")
st.write("Extração rápida com valores formatados em BRL (Vírgula).")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf:
    with st.spinner("Processando em alta velocidade..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            # Comando otimizado para velocidade e formato brasileiro
            comando = """
            Extraia as transações deste extrato.
            
            REGRAS DE FORMATAÇÃO:
            1. DATA: DD/MM/AAAA.
            2. VALOR: Use obrigatoriamente VÍRGULA como separador decimal (ex: 1250,45). 
               - Se for Débito/Saída, coloque sinal de menos antes (ex: -50,00).
               - Se for Crédito/Entrada, coloque sinal de mais ou apenas o número (ex: 100,00).
            3. TRANSAÇÃO: Junte descrições de múltiplas linhas e múltiplas colunas em uma só.
            
            SAÍDA: Retorne APENAS o array JSON puro com chaves "Data", "Transação", "Valor".
            """

            # Chamada direta para o modelo mais rápido
            resposta = model.generate_content([
                comando,
                {'mime_type': 'application/pdf', 'data': pdf_data}
            ])
            
            # Captura o JSON
            match = re.search(r'\[.*\]', resposta.text, re.DOTALL)
            
            if match:
                lista_dados = json.loads(match.group(0))
                df = pd.DataFrame(lista_dados)
                
                # Garante as colunas e a ordem
                df = df[["Data", "Transação", "Valor"]]

                st.success("Transcrição concluída!")
                st.dataframe(df, use_container_width=True)

                # Excel formatado
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Baixar Planilha em BRL",
                    data=output.getvalue(),
                    file_name="extrato_brl.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Não foi possível formatar os dados. Tente novamente.")

        except Exception as e:
            st.error(f"Erro: {e}")
