setup:
	pip install -r requirements.txt

pipeline:
	python load_data.py
	python analysis.py

dashboard:
	echo "TO DO: dashboard target"