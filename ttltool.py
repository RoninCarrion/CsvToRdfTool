import streamlit as st
import pandas as pd
import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import DCTERMS, FOAF, XSD

st.set_page_config(page_title="CSV a RDF", layout="wide")
st.title("🧠 Conversión de Publicaciones CSV a RDF (TTL)")

st.subheader("1️⃣ Configuración")

# Prefijos por defecto
default_prefixes = {
    "bibo": "http://purl.org/ontology/bibo/",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "http://schema.org/",
    "foaf": "http://xmlns.com/foaf/0.1/"
}

base_uri = st.text_input("🔗 URI base", value="http://example.org/publication/")
rdf_class = st.text_input("🧬 Clase RDF (ej: bibo:AcademicArticle)", value="bibo:AcademicArticle")
id_column = st.text_input("🆔 Columna de ID (único por fila)", value="DOI")

st.markdown("### 🏷️ Prefijos RDF")
prefixes = default_prefixes.copy()
with st.expander("Editar prefijos"):
    delete_keys = []
    for prefix, uri in prefixes.items():
        col1, col2, col3 = st.columns([3, 6, 1])
        with col1:
            new_prefix = st.text_input(f"Prefijo", value=prefix, key=f"pre_{prefix}")
        with col2:
            new_uri = st.text_input(f"URI", value=uri, key=f"uri_{prefix}")
        with col3:
            if st.checkbox("❌", key=f"del_{prefix}"):
                delete_keys.append(prefix)
        if new_prefix != prefix or new_uri != uri:
            prefixes[new_prefix] = new_uri
            if new_prefix != prefix:
                delete_keys.append(prefix)

    for key in delete_keys:
        prefixes.pop(key, None)

    st.markdown("**Agregar nuevo prefijo:**")
    col1, col2 = st.columns(2)
    with col1:
        new_p = st.text_input("Nuevo prefijo", key="new_prefix")
    with col2:
        new_u = st.text_input("Nuevo URI", key="new_uri")
    if new_p and new_u:
        prefixes[new_p] = new_u

st.markdown("### 🔁 Mapeo de columnas")
mappings = {}
multi_valued_cols = []
with st.expander("Mapear columnas"):
    csv_sample = st.file_uploader("📂 (Opcional) Cargar CSV para sugerir columnas", type="csv", key="csv_sugg")
    columnas = []
    if csv_sample:
        df_sample = pd.read_csv(csv_sample)
        columnas = df_sample.columns.tolist()

    num_maps = st.number_input("¿Cuántas columnas mapearás?", min_value=1, value=6)
    for i in range(num_maps):
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            csv_col = st.text_input(f"Columna CSV {i+1}", value=columnas[i] if i < len(columnas) else "", key=f"col_{i}")
        with col2:
            rdf_prop = st.text_input(f"Propiedad RDF {i+1} (ej: dcterms:title)", key=f"rdf_prop_{i}")
        with col3:
            if st.checkbox("Múltiples valores", key=f"multi_{i}"):
                multi_valued_cols.append(csv_col)
        if csv_col and rdf_prop:
            mappings[csv_col] = rdf_prop

# Mostrar configuración generada
config = {
    "input_file": "../assets/scopus.csv",  # Ruta relativa por defecto (puedes editarla)
    "base_uri": base_uri,
    "class": rdf_class,
    "id_column": id_column,
    "prefixes": prefixes,
    "mappings": mappings,
    "multi_valued": multi_valued_cols
}
st.markdown("### 🧾 Configuración generada (editable o exportable):")
st.code(json.dumps(config, indent=2), language="json")

st.divider()
st.subheader("2️⃣ Subir CSV y generar RDF")

csv_file = st.file_uploader("📄 Sube tu archivo CSV", type="csv", key="csv_main")
if csv_file:
    df = pd.read_csv(csv_file)
    st.write("Vista previa del CSV:")
    st.dataframe(df.head())

    if st.button("🚀 Generar RDF"):
        g = Graph()
        ns_map = {}
        for prefix, uri in config["prefixes"].items():
            ns = Namespace(uri)
            g.bind(prefix, ns)
            ns_map[prefix] = ns

        class_prefix, class_term = config["class"].split(":")
        base_uri = config["base_uri"]
        id_col = config["id_column"]
        mappings = config["mappings"]
        multi_cols = config.get("multi_valued", [])

        for idx, row in df.iterrows():
            row_id = str(row.get(id_col, f"row_{idx}")).replace("/", "_").replace(".", "_")
            subject_uri = URIRef(base_uri + row_id)
            g.add((subject_uri, RDF.type, ns_map[class_prefix][class_term]))

            for col, prop in mappings.items():
                if pd.notna(row.get(col)):
                    prefix, term = prop.split(":")
                    pred_uri = ns_map[prefix][term]
                    value = row[col]

                    # Valores separados por coma
                    if col in multi_cols and isinstance(value, str):
                        items = [v.strip() for v in value.split(",")]
                        for item in items:
                            g.add((subject_uri, pred_uri, Literal(item)))
                    else:
                        g.add((subject_uri, pred_uri, Literal(str(value))))

        ttl_output = g.serialize(format="turtle")
        st.download_button("📥 Descargar RDF (.ttl)", data=ttl_output, file_name="publicaciones.ttl", mime="text/turtle")
        st.success("✅ RDF generado correctamente.")