"""
.. module:: DSO

 Translated by owl2rdflib

 Translated to RDFlib from ontology http://www.semanticweb.org/directory-service-ontology#

 :Date 03/02/2021 07:16:48
"""
from rdflib import URIRef
from rdflib.namespace import ClosedNamespace

DSO =  ClosedNamespace(
    uri=URIRef('http://www.semanticweb.org/sansom/ontologies/2021/4/ECSDIsagma'),
    terms=[
        # Classes
        'Register',
        'RegisterResult',
        'RegisterAction',
        'Deregister',
        'InfoAgent',
        'ServiceAgent',
        'Search',
        'SolverAgent',
        'Modify',
        'AgenteUsuario',

        # Object properties
        'AgentType',

        # Data properties
        'Uri',
        'Name',
        'Address',

        # Named Individuals
        'FlightsAgent',
        'HotelsAgent',
        'TravelServiceAgent',
        'PersonalAgent',
        'WeatherAgent',
        'PaymentAgent'
    ]
)
