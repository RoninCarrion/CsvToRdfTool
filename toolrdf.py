import pandas as pd
import json
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD

# Cargar configuración
with open('config.json', 'r') as f:
    config = json.load(f)

# Leer CSV
df = pd.read_csv(config["input_file"])

# Crear grafo RDF
g = Graph()

# Crear namespaces y bind prefixes
namespaces = {}
for prefix, uri in config["prefixes"].items():
    ns = Namespace(uri)
    namespaces[prefix] = ns
    g.bind(prefix, ns)

# Clase RDF para cada recurso
rdf_class_prefix, rdf_class_name = config["class"].split(":")
rdf_class = namespaces[rdf_class_prefix][rdf_class_name]

# Base URI para recursos
base_uri = config["base_uri"]

# Generar RDF
for _, row in df.iterrows():
    row_id = str(row[config["id_column"]]).replace("/", "_").replace("@", "_")
    subject = URIRef(base_uri + row_id)
    g.add((subject, RDF.type, rdf_class))

    for col, prop_full in config["mappings"].items():
        if pd.notna(row[col]):
            prefix, prop = prop_full.split(":")
            predicate = namespaces[prefix][prop]
            value = Literal(str(row[col]))
            g.add((subject, predicate, value))

# Guardar como Turtle
g.serialize('../assets/output.ttl', format='turtle')
print("✅ RDF generado: output.ttl")