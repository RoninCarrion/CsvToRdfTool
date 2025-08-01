import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import DCTERMS, FOAF, XSD

# 1. Leer CSV
df = pd.read_csv('../assets/scopus.csv', sep=',', encoding='utf-8')

# 2. Crear grafo y namespaces
g = Graph()
EX = Namespace("http://example.org/scopus#")
SCHEMA = Namespace("http://schema.org/")
VIVO = Namespace("http://vivoweb.org/ontology/core#")
BIBO = Namespace("http://purl.org/ontology/bibo/")

g.bind("ex", EX)
g.bind("dcterms", DCTERMS)
g.bind("foaf", FOAF)
g.bind("schema", SCHEMA)
g.bind("vivo", VIVO)
g.bind("bibo", BIBO)

# 3. Generar triples
for idx, row in df.iterrows():
    doi = str(row['DOI']).replace('/', '_').replace('.', '_') if pd.notna(row['DOI']) else f"article_{idx}"
    article = EX[f'article_{doi}']
    g.add((article, RDF.type, BIBO.Article))

    if pd.notna(row['Title']):
        g.add((article, DCTERMS.title, Literal(row['Title'], lang='en')))

    if pd.notna(row['Year']):
        g.add((article, DCTERMS.issued, Literal(str(int(row['Year'])), datatype=XSD.gYear)))

    if pd.notna(row['Source title']):
        journal = EX[f"journal_{idx}"]
        g.add((article, DCTERMS.isPartOf, journal))
        g.add((journal, RDF.type, BIBO.Journal))
        g.add((journal, FOAF.name, Literal(row['Source title'], lang='en')))

    if pd.notna(row['Author full names']):
        authors = row['Author full names'].split(';')
        for i, author in enumerate(authors):
            author_id = f"author_{idx}_{i}"
            author_uri = EX[author_id.strip().replace(' ', '_')]
            g.add((author_uri, RDF.type, FOAF.Person))
            g.add((author_uri, FOAF.name, Literal(author.strip())))
            g.add((author_uri, VIVO.affiliation, EX['institution_dummy']))  # se puede mejorar
            g.add((article, DCTERMS.creator, author_uri))

    if pd.notna(row['Author Keywords']):
        g.add((article, SCHEMA.keywords, Literal(row['Author Keywords'])))

    if pd.notna(row['DOI']):
        g.add((article, BIBO.doi, Literal(row['DOI'])))

# 4. Guardar RDF
g.serialize(destination='../assets/publicaciones.ttl', format='turtle')
print("RDF generado como publicaciones.ttl")