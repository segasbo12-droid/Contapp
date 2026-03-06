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

        cliente = root.find(".//{*}AccountingCustomerParty//{*}RegistrationName")

        numero = root.find(".//{*}ID")
        fecha = root.find(".//{*}IssueDate")

        subtotal = root.find(".//{*}LineExtensionAmount")
        iva = root.find(".//{*}TaxAmount")
        total = root.find(".//{*}PayableAmount")

        return {
            "proveedor": proveedor.text if proveedor is not None else "No encontrado",
            "nit": nit.text if nit is not None else "No encontrado",
            "cliente": cliente.text if cliente is not None else "No encontrado",
            "numero": numero.text if numero is not None else "No encontrado",
            "fecha": fecha.text if fecha is not None else "No encontrado",
            "subtotal": float(subtotal.text) if subtotal is not None else 0,
            "iva": float(iva.text) if iva is not None else 0,
            "total": float(total.text) if total is not None else 0
        }

    except:
        return None


def generar_asiento(datos, tipo_operacion):

    subtotal = datos["subtotal"]
    iva = datos["iva"]
    total = datos["total"]

    retefuente = subtotal * 0.11
    reteica = subtotal * 0.00966

    if tipo_operacion == "Inventario":
        cuenta_debito = "1435"
    elif tipo_operacion == "Costo":
        cuenta_debito = "6135"
    else:
        cuenta_debito = "5135"

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

        tipo_operacion = st.selectbox(
            "Tipo de operación contable",
            ["Inventario","Costo","Gasto"]
        )

        todos_asientos = []

        for datos in facturas:

            st.write("Proveedor:", datos["proveedor"])
            st.write("NIT:", datos["nit"])
            st.write("Factura:", datos["numero"])
            st.write("Subtotal:", datos["subtotal"])
            st.write("IVA:", datos["iva"])
            st.write("Total:", datos["total"])
            st.write("---")

            df = generar_asiento(datos, tipo_operacion)

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
