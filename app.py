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
    if "AttachedDocument" in xml_texto:
        match = re.search(r'<!\[CDATA\[(.*?)\]\]>', xml_texto, re.DOTALL)
        if match:
            xml_texto = match.group(1)
    return xml_texto


def leer_factura(xml_texto):

    xml_factura = extraer_invoice(xml_texto)

    try:
        root = ET.fromstring(xml_factura)

        proveedor = root.find(".//{*}RegistrationName")
        numero = root.find(".//{*}ID")
        total = root.find(".//{*}PayableAmount")
        base = root.find(".//{*}TaxExclusiveAmount")
        iva = root.find(".//{*}TaxAmount")

        return {
            "proveedor": proveedor.text if proveedor is not None else "No encontrado",
            "numero": numero.text if numero is not None else "No encontrado",
            "total": float(total.text) if total is not None else 0,
            "base": float(base.text) if base is not None else 0,
            "iva": float(iva.text) if iva is not None else 0
        }

    except:
        return None


def generar_asiento(datos):

    asiento = [
        {
            "cuenta": "1435 - Inventarios / Gasto",
            "debito": datos["base"],
            "credito": 0
        },
        {
            "cuenta": "2408 - IVA descontable",
            "debito": datos["iva"],
            "credito": 0
        },
        {
            "cuenta": "2205 - Proveedores",
            "debito": 0,
            "credito": datos["total"]
        }
    ]

    return asiento


def mostrar_asiento(asiento):

    st.subheader("📊 Asiento contable sugerido")

    for linea in asiento:
        st.write(
            linea["cuenta"],
            " | Débito:",
            f'{linea["debito"]:,.2f}',
            " | Crédito:",
            f'{linea["credito"]:,.2f}'
        )


if archivo is not None:

    if archivo.name.endswith(".xml"):

        xml_texto = archivo.read().decode("utf-8")
        datos = leer_factura(xml_texto)

        if datos:

            st.success("Factura procesada")

            st.write("Proveedor:", datos["proveedor"])
            st.write("Número:", datos["numero"])
            st.write("Base:", datos["base"])
            st.write("IVA:", datos["iva"])
            st.write("Total:", datos["total"])

            asiento = generar_asiento(datos)

            mostrar_asiento(asiento)

        else:
            st.error("No se pudo leer el XML")


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
                    st.write("Número:", datos["numero"])
                    st.write("Base:", datos["base"])
                    st.write("IVA:", datos["iva"])
                    st.write("Total:", datos["total"])

                    asiento = generar_asiento(datos)

                    mostrar_asiento(asiento)

                    st.write("---")
