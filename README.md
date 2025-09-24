# ECE_UP_AI_Secretariat
Input PDF files go in the **docs** directory

The processed data/files are outputted in the **data** directory

1) pip install -r requirements.txt
2) ollama pull llama3
3) ollama pull nomic-embed-text
4) python RAG/embed_populatedb.py --reset
5) python RAG/embed_populate_exams.py
6) Run main function