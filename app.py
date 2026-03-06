import streamlit as st
import xml.etree.ElementTree as ET
import zipfile
import io
import re

st.title("📄 Lector de Facturas Electrónicas DIAN")

archivo = st.file_uploader(
    "Sube un XML o un ZIP con facturas",
    type=["xml", "zip"]
)

def extraer_invoice(xml_texto):
    """
    Si el XML es un AttachedDocument de la DIAN,
    extrae la factura que viene dentro del CDATA
    """
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
            "subtotal": subtotal.text if subtotal is not None else "No encontrado",
            "iva": iva.text if iva is not None else "No encontrado",
            "total": total.text if total is not None else "No encontrado"
        }

    except:
        return None


if archivo is not None:

    # SI ES XML
    if archivo.name.endswith(".xml"):

        xml_texto = archivo.read().decode("utf-8")
        datos = leer_factura(xml_texto)

        if datos:
            st.success("Factura procesada")

            st.write("Proveedor:", datos["proveedor"])
            st.write("NIT:", datos["nit"])
            st.write("Cliente:", datos["cliente"])
            st.write("Número:", datos["numero"])
            st.write("Fecha:", datos["fecha"])
            st.write("Subtotal:", datos["subtotal"])
            st.write("IVA:", datos["iva"])
            st.write("Total:", datos["total"])

        else:
            st.error("No se pudo leer el XML")


    # SI ES ZIP
    elif archivo.name.endswith(".zip"):

        st.info("Procesando ZIP...")

        zip_data = zipfile.ZipFile(io.BytesIO(archivo.read()))

        for nombre in zip_data.namelist():

            if nombre.endswith(".xml"):

                xml_texto = zip_data.read(nombre).decode("utf-8")
                datos = leer_factura(xml_texto)

                if datos:
                    st.success(f"Factura encontrada: {nombre}")

                    st.write("Proveedor:", datos["proveedor"])
                    st.write("NIT:", datos["nit"])
                    st.write("Cliente:", datos["cliente"])
                    st.write("Número:", datos["numero"])
                    st.write("Fecha:", datos["fecha"])
                    st.write("Subtotal:", datos["subtotal"])
                    st.write("IVA:", datos["iva"])
                    st.write("Total:", datos["total"])
                    st.write("---")
