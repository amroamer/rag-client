# Agent name → RAGFlow agent ID mapping
# These IDs come from your RAGFlow canvas export

AGENT_REGISTRY: dict[str, dict] = {
    "supervisor": {
    "id": "6af2eaa42c7611f19c8a01d4a214c307",
    "title": "Data Governance Supervisor",
    "description": "Classifies user intent and returns the correct agent route",
    "output_format": "json",
    },"ndmo-classification": {
        "id": "d9350ce626f811f19ebabf1904121a5d",
        "title": "NDMO Data Classification",
        "description": "Classifies data columns into TOP SECRET / SECRET / CONFIDENTIAL / PUBLIC per NDMO framework",
        "output_format": "json",
    },
    "pii-detection": {
        "id": "5ae87dc8272011f1bcb727acdc027aa2",
        "title": "PII Detection",
        "description": "Scans data elements for PII and recommends ENCRYPT / MASK / RESTRICT actions",
        "output_format": "json",
    },
    "business-definitions": {
        "id": "303f458c272211f1bcb727acdc027aa2",
        "title": "Business Definitions",
        "description": "Generates bilingual EN/AR business definitions for data columns",
        "output_format": "json",
    },
    "report-tester": {
        "id": "e1252f78270f11f19ebbbf1904121a5d",
        "title": "Report Tester",
        "description": "Validates CSV/tabular reports for null, duplicate, calculation, and date issues",
        "output_format": "markdown",
    },
    "dq-rules-generator": {
        "id": "2ac2798e272311f1bcb727acdc027aa2",
        "title": "DQ Rules Generator",
        "description": "Generates implementable data quality rules with severity levels from a dataset",
        "output_format": "json",
    },
}

VALID_AGENT_NAMES = list(AGENT_REGISTRY.keys())
