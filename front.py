import streamlit as st
import pandas as pd
import json
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import DCTERMS, FOAF, XSD

st.title("🧠 Conversión de Publicaciones CSV a RDF (TTL)")

config_file = st.file_uploader("📄 Sube tu archivo de configuración (config.json)", type="json")

if config_file:
    config = json.load(config_file)
    st.success("✅ Configuración cargada correctamente.")

    csv_file = st.file_uploader("📂 Sube tu archivo de publicaciones (CSV)", type="csv")

    if csv_file:
        df = pd.read_csv(csv_file)
        st.write("Vista previa del CSV:")
        st.dataframe(df.head())

        if st.button("🚀 Generar RDF (TTL)"):
            g = Graph()
            base_uri = config["base_uri"]
            class_uri = config["class"]
            id_col = config["id_column"]
            mappings = config["mappings"]
            prefixes = config["prefixes"]

            ns_map = {}
            for prefix, uri in prefixes.items():
                ns = Namespace(uri)
                g.bind(prefix, ns)
                ns_map[prefix] = ns

            for idx, row in df.iterrows():
                row_id = str(row.get(id_col, f"row_{idx}")).replace("/", "_").replace(".", "_")
                subject_uri = URIRef(base_uri + row_id)

                class_prefix, class_term = class_uri.split(":")
                g.add((subject_uri, RDF.type, ns_map[class_prefix][class_term]))

                for col, prop in mappings.items():
                    if pd.notna(row.get(col)):
                        prefix, term = prop.split(":")
                        pred_uri = ns_map[prefix][term]
                        g.add((subject_uri, pred_uri, Literal(str(row[col]))))

            ttl_output = g.serialize(format="turtle")
            st.download_button("📥 Descargar RDF en TTL", data=ttl_output, file_name="publicaciones.ttl", mime="text/turtle")
            st.success("✅ RDF generado correctamente.")