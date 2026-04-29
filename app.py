import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import json
import re

st.set_page_config(page_title="Extrator Pro - Alta Capacidade", layout="wide")

if "GEMINI_API_KEY" not in st.secrets:
    st.error("Configure a GEMINI_API_KEY nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            # Aumentamos ao máximo o limite de palavras da resposta
            return genai.GenerativeModel(m.name, generation_config={"max_output_tokens": 8192, "temperature": 0})
    return None

model = get_model()

st.title("🏦 Transcritor de Extratos (Arquivos Longos)")

arquivo_pdf = st.file_uploader("Suba o extrato em PDF", type=["pdf"])

if arquivo_pdf:
    with st.spinner("A processar um ficheiro grande... Isto pode demorar até 1 minuto."):
        try:
            pdf_data = arquivo_pdf.read()
            
            # Comando mais "seco" para economizar espaço na resposta da IA
            comando = """
            Transcreva TODAS as transações deste PDF.
            REGRAS:
            1. DATA: DD/MM/AAAA.
            2. VALOR: Use vírgula (ex: 1250,45). Saídas com sinal (-).
            3. TRANSAÇÃO: Nome da operação.
            SAÍDA: Retorne APENAS um array JSON. Exemplo: [{"Data":"01/01","Transação":"X","Valor":"10,00"}]
            """

            resposta = model.generate_content([comando, {'mime_type': 'application/pdf', 'data': pdf_data}])
            texto_ia = resposta.text
            
            # Tenta encontrar qualquer pedaço de JSON que tenha vindo
            # Mesmo que o arquivo seja cortado, vamos tentar salvar o que apareceu
            match = re.search(r'\[.*', texto_ia, re.DOTALL)
            
            if match:
                conteudo = match.group(0).strip()
                
                # Se o JSON veio incompleto (sem o último ]), nós fechamos ele
                if not conteudo.endswith(']'):
                    # Procura o último objeto completo } e fecha o array
                    if '}' in conteudo:
                        conteudo = conteudo[:conteudo.rfind('}')+1] + ']'
                
                try:
                    df = pd.read_json(io.StringIO(conteudo))
                except:
                    # Segunda tentativa de limpeza caso a primeira falhe
                    lista = json.loads(re.sub(r',[^,]*$', '', conteudo) + ']')
                    df = pd.DataFrame(lista)

                # Padronização de nomes de colunas
                mapeamento = {col: col.capitalize() for col in df.columns}
                df = df.rename(columns=mapeamento)
                
                # Garante as 3 colunas principais
                for c in ["Data", "Transação", "Valor"]:
                    if c not in df.columns: df[c] = ""

                df_final = df[["Data", "Transação", "Valor"]]
                
                st.success(f"Sucesso! {len(df_final)} transações recuperadas.")
                st.dataframe(df_final, use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_final.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel BRL", output.getvalue(), "extrato_final.xlsx")
            else:
                st.error("A IA não conseguiu estruturar os dados. Resposta recebida:")
                st.write(texto_ia)

        except Exception as e:
            st.error(f"Erro: {e}")
