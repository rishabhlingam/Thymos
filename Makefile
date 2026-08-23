setup:
	pip install -r requirements.txt

pipeline:
	python load_data.py
	python analysis.py

dashboard:
	./venv/bin/uvicorn backend.main:app --port 8000 &
	cd frontend && npm run dev