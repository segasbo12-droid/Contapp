import streamlit as st
import xml.etree.ElementTree as ET
import zipfile
import io
import re
import pandas as pd

st.title("📊 ContApp - Lector de Facturas DIAN y Generador de Asientos")

archivo = st.file_uploader(
    "Sube un XML o un ZIP con facturas",
    type=["xml", "zip"]
)

# Cargar tablas contables
tabla_cuentas = pd.read_excel("tabla_cuentas.xlsx")
tabla_retenciones = pd.read_excel("tabla_retenciones.xlsx")


# EXTRAER FACTURA SI ES ATTACHED DOCUMENT
def extraer_invoice(xml_texto):

    if "AttachedDocument" in xml_texto:
        match = re.search(r'<!\[CDATA\[(.*?)\]\]>', xml_texto, re.DOTALL)
        if match:
            xml_texto = match.group(1)

    return xml_texto


# LEER FACTURA
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
            "proveedor": proveedor.text if proveedor is not None else "",
            "nit": nit.text if nit is not None else "",
            "cliente": cliente.text if cliente is not None else "",
            "numero": numero.text if numero is not None else "",
            "fecha": fecha.text if fecha is not None else "",
            "subtotal": float(subtotal.text) if subtotal is not None else 0,
            "iva": float(iva.text) if iva is not None else 0,
            "total": float(total.text) if total is not None else 0
        }

    except:
        return None


# CLASIFICAR TIPO DE COMPRA
def clasificar_compra(datos):

    proveedor = datos["proveedor"].lower()

    if "restaurant" in proveedor or "hotel" in proveedor:
        return "gasto"

    if "industrial" in proveedor or "insumos" in proveedor:
        return "inventario"

    return "servicio"


# BUSCAR CUENTA CONTABLE
def buscar_cuenta(tipo):

    fila = tabla_cuentas[tabla_cuentas["tipo"] == tipo]

    if len(fila) > 0:
        return fila.iloc[0]["cuenta"]

    return "519595"


# BUSCAR RETENCION
def buscar_retencion(tipo):

    fila = tabla_retenciones[tabla_retenciones["tipo"] == tipo]

    if len(fila) > 0:

        porcentaje = fila.iloc[0]["porcentaje"]
        cuenta = fila.iloc[0]["cuenta"]

        return porcentaje, cuenta

    return 0, ""


# GENERAR ASIENTO CONTABLE
def generar_asiento(datos):

    tipo = clasificar_compra(datos)

    cuenta_debito = buscar_cuenta(tipo)

    subtotal = datos["subtotal"]
    iva = datos["iva"]
    total = datos["total"]

    porcentaje_ret, cuenta_ret = buscar_retencion(tipo)

    valor_ret = subtotal * porcentaje_ret

    cuenta_proveedor = "220505"
    cuenta_iva = "240805"

    asiento = []

    # DEBITO
    asiento.append({
        "NIT": datos["nit"],
        "Proveedor": datos["proveedor"],
        "Cuenta": cuenta_debito,
        "Debito": subtotal,
        "Credito": 0
    })

    # IVA
    if iva > 0:
        asiento.append({
            "NIT": datos["nit"],
            "Proveedor": datos["proveedor"],
            "Cuenta": cuenta_iva,
            "Debito": iva,
            "Credito": 0
        })

    # RETENCION
    if valor_ret > 0:
        asiento.append({
            "NIT": datos["nit"],
            "Proveedor": datos["proveedor"],
            "Cuenta": cuenta_ret,
            "Debito": 0,
            "Credito": valor_ret
        })

    # PROVEEDOR
    asiento.append({
        "NIT": datos["nit"],
        "Proveedor": datos["proveedor"],
        "Cuenta": cuenta_proveedor,
        "Debito": 0,
        "Credito": total - valor_ret
    })

    return asiento


# PROCESAR ARCHIVO
asientos_totales = []

if archivo is not None:

    if archivo.name.endswith(".xml"):

        xml_texto = archivo.read().decode("utf-8")

        datos = leer_factura(xml_texto)

        if datos:

            st.success("Factura procesada")

            st.write(datos)

            asiento = generar_asiento(datos)

            asientos_totales.extend(asiento)

    elif archivo.name.endswith(".zip"):

        zip_data = zipfile.ZipFile(io.BytesIO(archivo.read()))

        for nombre in zip_data.namelist():

            if nombre.endswith(".xml"):

                xml_texto = zip_data.read(nombre).decode("utf-8")

                datos = leer_factura(xml_texto)

                if datos:

                    asiento = generar_asiento(datos)

                    asientos_totales.extend(asiento)


# EXPORTAR EXCEL
if len(asientos_totales) > 0:

    df_final = pd.DataFrame(asientos_totales)

    st.subheader("Vista previa del asiento contable")

    st.dataframe(df_final)

    excel_file = "asientos_contables.xlsx"

    df_final.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:

        st.download_button(
            "Descargar Excel para ERP",
            f,
            file_name="asientos_contables.xlsx"
        )
