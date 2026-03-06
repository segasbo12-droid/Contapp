import streamlit as st
import xml.etree.ElementTree as ET
import zipfile
import io
import re
import pandas as pd

st.title("📄 Lector de Facturas Electrónicas DIAN")

archivo = st.file_uploader(
    "Sube un XML o un ZIP con facturas",
    type=["xml", "zip"]
)

# Cargar tabla de cuentas
tabla_cuentas = pd.read_excel("tabla_cuentas.xlsx")

def buscar_cuenta(descripcion):

    descripcion = descripcion.lower()

    for i, fila in tabla_cuentas.iterrows():

        palabra = str(fila["palabra"]).lower()
        cuenta = str(fila["cuenta"])

        if palabra in descripcion:
            return cuenta

    return "5135"


def extraer_invoice(xml_texto):

    if "AttachedDocument" in xml_texto:

        match = re.search(r'<!\[CDATA\[(.*?)\]\]>', xml_texto, re.DOTALL)

        if match:
            xml_texto = match.group(1)

    return xml_texto


def leer_factura(xml_texto):

    xml_factura = extraer_invoice(xml_texto)

    try:

        root = ET.fromstring(xml_factura)

        proveedor = root.find(".//{*}AccountingSupplierParty//{*}RegistrationName")
        nit = root.find(".//{*}AccountingSupplierParty//{*}CompanyID")

        numero = root.find(".//{*}ID")
        fecha = root.find(".//{*}IssueDate")

        descripcion = root.find(".//{*}Description")

        subtotal = root.find(".//{*}LineExtensionAmount")
        iva = root.find(".//{*}TaxAmount")
        total = root.find(".//{*}PayableAmount")

        return {
            "proveedor": proveedor.text if proveedor is not None else "No encontrado",
            "nit": nit.text if nit is not None else "No encontrado",
            "numero": numero.text if numero is not None else "No encontrado",
            "fecha": fecha.text if fecha is not None else "No encontrado",
            "descripcion": descripcion.text if descripcion is not None else "",
            "subtotal": float(subtotal.text) if subtotal is not None else 0,
            "iva": float(iva.text) if iva is not None else 0,
            "total": float(total.text) if total is not None else 0
        }

    except:
        return None


def generar_asiento(datos):

    subtotal = datos["subtotal"]
    iva = datos["iva"]
    total = datos["total"]

    descripcion = datos["descripcion"]

    cuenta_debito = buscar_cuenta(descripcion)

    retefuente = subtotal * 0.11
    reteica = subtotal * 0.00966

    asiento = [
        [datos["nit"], datos["proveedor"], cuenta_debito, subtotal, 0],
        [datos["nit"], datos["proveedor"], "2408", iva, 0],
        [datos["nit"], datos["proveedor"], "2365", 0, retefuente],
        [datos["nit"], datos["proveedor"], "2368", 0, reteica],
        [datos["nit"], datos["proveedor"], "2205", 0, total - retefuente - reteica]
    ]

    df = pd.DataFrame(
        asiento,
        columns=["NIT","Proveedor","Cuenta contable","Debito","Credito"]
    )

    return df


if archivo is not None:

    facturas = []

    if archivo.name.endswith(".xml"):

        xml_texto = archivo.read().decode("utf-8")

        datos = leer_factura(xml_texto)

        if datos:
            facturas.append(datos)

    elif archivo.name.endswith(".zip"):

        zip_data = zipfile.ZipFile(io.BytesIO(archivo.read()))

        for nombre in zip_data.namelist():

            if nombre.endswith(".xml"):

                xml_texto = zip_data.read(nombre).decode("utf-8")

                datos = leer_factura(xml_texto)

                if datos:
                    facturas.append(datos)

    if len(facturas) > 0:

        st.success(f"{len(facturas)} factura(s) procesada(s)")

        todos_asientos = []

        for datos in facturas:

            st.write("Proveedor:", datos["proveedor"])
            st.write("NIT:", datos["nit"])
            st.write("Factura:", datos["numero"])
            st.write("Descripción:", datos["descripcion"])
            st.write("Subtotal:", datos["subtotal"])
            st.write("IVA:", datos["iva"])
            st.write("Total:", datos["total"])
            st.write("---")

            df = generar_asiento(datos)

            todos_asientos.append(df)

        df_final = pd.concat(todos_asientos)

        st.subheader("Asiento contable generado")

        st.dataframe(df_final)

        excel_file = "asientos_contables.xlsx"

        df_final.to_excel(excel_file, index=False)

        with open(excel_file, "rb") as f:

            st.download_button(
                "📥 Descargar Excel contable",
                f,
                file_name="asientos_contables.xlsx"
            )

    else:

        st.error("No se pudieron leer facturas válidas")
