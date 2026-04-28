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

# Descoberta automática de modelo para evitar erro 404
try:
    modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    modelo_final = next((m for m in modelos if 'flash' in m), modelos[0])
    model = genai.GenerativeModel(modelo_final)
except:
    st.stop()

st.title("🏦 Transcritor de Extratos Bancários")

arquivo_pdf = st.file_uploader("Arraste o extrato aqui", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A analisar extrato e a aplicar as regras..."):
        try:
            pdf_data = arquivo_pdf.read()
            
            comando = """
            Transcreva as transações deste extrato seguindo estas REGRAS:
            1. Una descrições de várias linhas (quebras de linha) em uma única frase.
            2. Se houver várias colunas de descrição (como histórico + documento), junte-as.
            3. Una Crédito/Débito em uma única coluna 'Valor'. 
               - Se tiver 'D' ou for débito, use sinal de MENOS (ex: -10.50).
               - Se tiver 'C' ou for crédito, use sinal de MAIS (ex: 10.50).
            4. Formato Data: DD/MM/AAAA.
            5. Retorne APENAS o array JSON puro com chaves: 'Data', 'Transação', 'Valor'. Sem explicações.
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            
            # --- LIMPEZA PESADA DO JSON ---
            texto_sujo = resposta.text
            # Procura o primeiro '[' e o último ']'
            inicio = texto_sujo.find('[')
            fim = texto_sujo.rfind(']') + 1
            
            if inicio != -1 and fim != 0:
                json_limpo = texto_sujo[inicio:fim]
                # Remove possíveis quebras de linha dentro do JSON que quebram o código
                json_limpo = re.sub(r'\\n', ' ', json_limpo)
                lista_dados = json.loads(json_limpo)
                
                df = pd.DataFrame(lista_dados)
                
                # Garante que as colunas existem e estão na ordem
                for c in ["Data", "Transação", "Valor"]:
                    if c not in df.columns: df[c] = ""
                
                df = df[["Data", "Transação", "Valor"]]
                
                st.success("Transcritor finalizado!")
                st.dataframe(df, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", output.getvalue(), "extrato_concluido.xlsx")
            else:
                st.error("A IA não gerou uma tabela válida. Tente novamente.")
                st.code(texto_sujo) # Mostra o erro para podermos analisar

        except Exception as e:
            st.error(f"Erro no processamento: {e}")
