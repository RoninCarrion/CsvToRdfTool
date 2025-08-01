import streamlit as st
import pandas as pd
import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from pyvis.network import Network
import tempfile
import streamlit.components.v1 as components

st.set_page_config(page_title="CSV a RDF", layout="wide")
st.title("Conversión de Publicaciones CSV a RDF (TTL)")

# === Sección 1: Configuración ===
st.subheader("1️⃣ Configuración")

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
separators = {}
with st.expander("Mapear columnas"):
    csv_sample = st.file_uploader("📂 (Opcional) Cargar CSV para sugerir columnas", type="csv", key="csv_sugg")
    columnas = []
    if csv_sample:
        df_sample = pd.read_csv(csv_sample)
        columnas = df_sample.columns.tolist()
    num_maps = st.number_input("¿Cuántas columnas mapearás?", min_value=1, value=6)
    for i in range(num_maps):
        col1, col2, col3, col4 = st.columns([3, 3, 2, 2])
        with col1:
            csv_col = st.text_input(f"Columna CSV {i+1}", value=columnas[i] if i < len(columnas) else "", key=f"col_{i}")
        with col2:
            rdf_prop = st.text_input(f"Propiedad RDF {i+1} (ej: dcterms:title)", key=f"rdf_prop_{i}")
        is_multi = False
        sep = ","
        with col3:
            is_multi = st.checkbox("Múltiples", key=f"multi_{i}")
        with col4:
            if is_multi:
                sep = st.text_input("Separador", value=";", key=f"sep_{i}")
        if csv_col and rdf_prop:
            mappings[csv_col] = rdf_prop
            if is_multi:
                multi_valued_cols.append(csv_col)
                separators[csv_col] = sep

config = {
    "base_uri": base_uri,
    "class": rdf_class,
    "id_column": id_column,
    "prefixes": prefixes,
    "mappings": mappings,
    "multi_valued": multi_valued_cols,
    "separator": separators
}
st.markdown("### 🧾 Configuración generada (editable o exportable):")
st.code(json.dumps(config, indent=2), language="json")

# === Sección 2: Subida de CSV y generación ===
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
        separators = config.get("separator", {})

        for idx, row in df.iterrows():
            row_id = str(row.get(id_col, f"row_{idx}")).replace("/", "_").replace(".", "_")
            subject_uri = URIRef(base_uri + row_id)
            g.add((subject_uri, RDF.type, ns_map[class_prefix][class_term]))

            for col, prop in mappings.items():
                if pd.notna(row.get(col)):
                    prefix, term = prop.split(":")
                    pred_uri = ns_map[prefix][term]
                    value = row[col]
                    if col in multi_cols and isinstance(value, str):
                        sep = separators.get(col, ",")
                        items = [v.strip() for v in value.split(sep) if v.strip()]
                        for item in items:
                            g.add((subject_uri, pred_uri, Literal(item)))
                    else:
                        g.add((subject_uri, pred_uri, Literal(str(value))))

        ttl_output = g.serialize(format="turtle")

        # ✅ Vista previa del TTL
        st.markdown("### 🧾 Vista previa del RDF (.ttl)")
        st.code(ttl_output, language="turtle")

        # 🧠 Visualización como grafo RDF
        st.markdown("### 🧠 Visualización del Grafo RDF")
        net = Network(height="500px", width="100%", directed=True)
        added_nodes = set()

        for s, p, o in g:
            s_str, p_str, o_str = str(s), str(p), str(o)
            if s_str not in added_nodes:
                net.add_node(s_str, label=s_str, shape='ellipse', color='lightblue')
                added_nodes.add(s_str)
            if o_str not in added_nodes:
                net.add_node(o_str, label=o_str, shape='ellipse', color='lightgreen')
                added_nodes.add(o_str)
            net.add_edge(s_str, o_str, label=p_str)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            net.save_graph(tmp_file.name)
            HtmlFile = open(tmp_file.name, 'r', encoding='utf-8')
            source_code = HtmlFile.read()
            components.html(source_code, height=550, scrolling=True)

        # 📥 Descargar TTL
        st.download_button("📥 Descargar RDF (.ttl)", data=ttl_output, file_name="publicaciones.ttl", mime="text/turtle")
        st.success("✅ RDF generado correctamente.")