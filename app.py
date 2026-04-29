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
    with st.spinner("Processando... Aguarde a conclusão da leitura completa."):
        try:
            pdf_data = arquivo_pdf.read()
            
            comando = """
            Transcreva TODAS as transações deste extrato.
            FORMATO OBRIGATÓRIO: Array JSON puro.
            REGRAS: 
            1. Use aspas duplas em todos os nomes e valores.
            2. VALOR: Use vírgula (ex: "1.452,90"). Use sinal de menos para saídas.
            3. DATA: DD/MM/AAAA.
            4. Se o texto for cortado, termine o último objeto corretamente.
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            texto_ia = resposta.text
            
            # --- LIMPEZA DE ERROS DE ASPAS E VÍRGULAS ---
            # Remove espaços extras e quebras de linha que confundem o JSON
            json_str = re.search(r'\[.*\]', texto_ia, re.DOTALL)
            
            if json_str:
                json_final = json_str.group(0)
                
                # TRUQUE MESTRE: Tenta converter o JSON "sujo" em uma tabela do Pandas direto
                try:
                    # O pandas é mais tolerante a erros de JSON que o comando json.loads
                    df = pd.read_json(io.StringIO(json_final))
                except:
                    # Se o pandas falhar, tentamos uma limpeza manual de vírgulas extras
                    json_final = re.sub(r',\s*\]', ']', json_final) 
                    json_final = re.sub(r',\s*\}', '}', json_final)
                    lista_dados = json.loads(json_final)
                    df = pd.DataFrame(lista_dados)

                st.success(f"Sucesso! {len(df)} linhas processadas.")
                st.dataframe(df[["Data", "Transação", "Valor"]], use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel BRL", output.getvalue(), "extrato_final.xlsx")
            else:
                st.error("A IA não gerou uma tabela válida.")
                st.code(texto_ia)

        except Exception as e:
            st.error(f"Erro de processamento: {e}")
            st.info("Dica: Se o arquivo for muito grande, tente processar poucas páginas por vez.")
