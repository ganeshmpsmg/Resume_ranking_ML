"""
app/core/taxonomy.py
---------------------
Master skills taxonomy and education ranking used across parsing,
extraction, and ranking services.
"""

SKILL_TAXONOMY = {
    "Programming Languages": [
        "Python", "Java", "C++", "C", "C#", "JavaScript", "TypeScript", "Go",
        "Rust", "R", "MATLAB", "Scala", "Kotlin", "Swift", "PHP", "Ruby",
        "Perl", "SQL", "Shell Scripting", "Bash", "HTML", "CSS",
    ],
    "Machine Learning / AI": [
        "Machine Learning", "Deep Learning", "Natural Language Processing",
        "NLP", "Computer Vision", "Reinforcement Learning", "TensorFlow",
        "PyTorch", "Keras", "Scikit-learn", "XGBoost", "LightGBM",
        "CatBoost", "Hugging Face", "Transformers", "BERT", "GPT",
        "Sentence Transformers", "OpenCV", "spaCy", "NLTK", "MLOps",
        "Feature Engineering", "Model Deployment", "Generative AI",
        "LLM", "LangChain", "RAG", "Neural Networks", "CNN", "RNN", "LSTM",
        "Time Series Analysis", "Statistics", "A/B Testing",
    ],
    "Cloud / DevOps": [
        "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes",
        "Terraform", "Jenkins", "CI/CD", "Ansible", "Linux", "Git", "GitHub",
        "GitLab", "Lambda", "EC2", "S3", "CloudFormation", "Heroku",
        "DevOps", "Microservices", "REST API", "GraphQL", "Nginx",
        "Serverless", "Render", "Vercel", "Netlify",
    ],
    "Databases": [
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "Redis",
        "Cassandra", "DynamoDB", "Elasticsearch", "Firebase", "MariaDB",
        "Neo4j", "Snowflake", "BigQuery", "Data Warehousing", "FAISS",
        "ChromaDB", "Pinecone", "Vector Database",
    ],
    "Tools / Frameworks": [
        "Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly", "Streamlit",
        "Flask", "Django", "FastAPI", "React", "Node.js", "Tableau",
        "Power BI", "Excel", "Jupyter", "VS Code", "Postman", "Jira",
        "Confluence", "Apache Spark", "Hadoop", "Airflow", "Kafka", "dbt",
    ],
}

SKILL_LOOKUP: dict[str, tuple[str, str]] = {}
for _category, _skills in SKILL_TAXONOMY.items():
    for _skill in _skills:
        SKILL_LOOKUP[_skill.lower()] = (_skill, _category)

ALL_SKILLS_SORTED = sorted(SKILL_LOOKUP.keys(), key=len, reverse=True)

EDUCATION_RANKS = {
    "phd": 5, "doctorate": 5,
    "master": 4, "m.tech": 4, "mtech": 4, "msc": 4, "m.sc": 4, "mba": 4,
    "ms": 4, "m.s": 4, "me": 4, "m.e": 4,
    "bachelor": 3, "b.tech": 3, "btech": 3, "bsc": 3, "b.sc": 3, "be": 3,
    "b.e": 3, "bca": 3, "ba": 3, "b.a": 3,
    "diploma": 2,
    "high school": 1, "12th": 1, "intermediate": 1,
}
