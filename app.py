import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import zipfile
import io

st.title("Automatizador Contable - Factura DIAN")

# Cargar tablas
tabla_cuentas_file = st.file_uploader("Subir tabla de cuentas", type=["xlsx"])
tabla_retenciones_file = st.file_uploader("Subir tabla de retenciones", type=["xlsx"])

if tabla_cuentas_file:
    tabla_cuentas = pd.read_excel(tabla_cuentas_file)
else:
    tabla_cuentas = None

if tabla_retenciones_file:
    tabla_retenciones = pd.read_excel(tabla_retenciones_file)
else:
    tabla_retenciones = None


# Subir factura
archivo = st.file_uploader("Sube XML o ZIP de factura DIAN", type=["xml","zip"])


def leer_xml(xml_file):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    datos = {
        "nit": "",
        "proveedor": "",
        "total": 0
    }

    for elem in root.iter():

        if "CompanyID" in elem.tag:
            datos["nit"] = elem.text

        if "RegistrationName" in elem.tag:
            datos["proveedor"] = elem.text

        if "PayableAmount" in elem.tag:
            datos["total"] = float(elem.text)

    return datos


def buscar_cuenta(concepto):

    if tabla_cuentas is None:
        return "0000"

    for i,row in tabla_cuentas.iterrows():

        if row["concepto"].lower() in concepto.lower():
            return row["cuenta"]

    return "0000"


def calcular_retenciones(base, concepto):

    retenciones = []

    if tabla_retenciones is None:
        return retenciones

    for i,row in tabla_retenciones.iterrows():

        if row["concepto"].lower() in concepto.lower():

            valor = base * (row["porcentaje"] / 100)

            retenciones.append({
                "cuenta": row["cuenta"],
                "valor": valor
            })

    return retenciones


if archivo:

    xml_data = None

    if archivo.name.endswith(".zip"):

        z = zipfile.ZipFile(archivo)

        for nombre in z.namelist():

            if nombre.endswith(".xml"):
                xml_data = z.open(nombre)
                break

    else:
        xml_data = archivo


    datos = leer_xml(xml_data)

    st.write("Proveedor:", datos["proveedor"])
    st.write("NIT:", datos["nit"])
    st.write("Total:", datos["total"])


    concepto = st.text_input("Concepto contable (ej: servicios, compra, inventario)")


    if st.button("Generar asiento"):

        cuenta_gasto = buscar_cuenta(concepto)

        subtotal = datos["total"]

        asientos = []

        # Debito gasto
        asientos.append([
            datos["nit"],
            datos["proveedor"],
            cuenta_gasto,
            subtotal,
            0
        ])

        # Calcular retenciones
        retenciones = calcular_retenciones(subtotal, concepto)

        total_retenciones = 0

        for r in retenciones:

            total_retenciones += r["valor"]

            asientos.append([
                datos["nit"],
                datos["proveedor"],
                r["cuenta"],
                0,
                r["valor"]
            ])

        # Cuenta proveedor
        cuenta_proveedor = "2205"

        asientos.append([
            datos["nit"],
            datos["proveedor"],
            cuenta_proveedor,
            0,
            subtotal - total_retenciones
        ])

        df_final = pd.DataFrame(
            asientos,
            columns=["NIT","Proveedor","Cuenta","Debito","Credito"]
        )

        st.dataframe(df_final)

        excel = io.BytesIO()

        df_final.to_excel(excel,index=False)

        st.download_button(
            "Descargar Excel",
            data=excel.getvalue(),
            file_name="asiento_contable.xlsx"
        )
