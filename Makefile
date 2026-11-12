# One-command reproducibility. Usage: make setup && make all
PY := .venv/bin/python
.PHONY: setup data pipeline notebook test preview all clean

setup:            ## create the virtual environment and install pinned dependencies
	python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt
	.venv/bin/python -m ipykernel install --sys-prefix --name python3   # notebook runs on the project venv

data:             ## download the Olist dataset into data/raw (skips if present)
	cd python && ../$(PY) -m olist_ba.ingest

pipeline:         ## SQL build/validation/analysis, pandas, stats, root cause, scenarios, charts, BI export
	cd python && ../$(PY) -m olist_ba.pipeline

notebook:         ## execute the analysis notebook in place
	$(PY) -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=python3 python/notebooks/analysis.ipynb

test:             ## run unit + integration tests
	$(PY) -m pytest

preview:          ## launch the Streamlit dashboard preview
	.venv/bin/streamlit run dashboard/streamlit/app.py

all: data pipeline notebook test

clean:            ## remove generated data (raw data kept)
	rm -rf data/processed data/bi/*.csv data/bi/manifest.json
