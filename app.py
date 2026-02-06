import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd

st.title("Demo – Factura Electrónica DIAN")

archivo = st.file_uploader("Cargar XML de la DIAN", type="xml")

if archivo:
    tree = ET.parse(archivo)
    root = tree.getroot()

    ns = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
    }

    try:
        fecha = root.find('.//cbc:IssueDate', ns).text
        numero = root.find('.//cbc:ID', ns).text
        total = root.find('.//cbc:PayableAmount', ns).text
    except:
        st.error("Este XML no parece ser una factura DIAN válida")
        st.stop()

    st.subheader("Datos de la factura")
    st.write("Número:", numero)
    st.write("Fecha:", fecha)
    st.write("Total:", total)

    st.subheader("Asiento contable sugerido")

    df = pd.DataFrame({
        "Cuenta": ["1305", "4135"],
        "Débito": [float(total), 0],
        "Crédito": [0, float(total)]
    })

    st.table(df)

    st.download_button(
        "Exportar asiento (CSV)",
        df.to_csv(index=False),
        "asiento_contable.csv",
        "text/csv"
    )
