.PHONY: all test experiments figures paper frontend clean

PY := PYTHONPATH=. python3

all: test experiments figures paper

test:
	$(PY) -m pytest tests/ -v

experiments:
	$(PY) experiments/validation.py
	$(PY) experiments/scenarios.py
	$(PY) experiments/interventions.py

figures: experiments
	$(PY) experiments/make_figures.py

paper: figures
	cd paper && pdflatex -interaction=nonstopmode hotcarwatch.tex > /dev/null \
		&& bibtex hotcarwatch > /dev/null \
		&& pdflatex -interaction=nonstopmode hotcarwatch.tex > /dev/null \
		&& pdflatex -interaction=nonstopmode hotcarwatch.tex > /dev/null
	@echo "Built paper/hotcarwatch.pdf"

frontend:
	cd frontend && python3 -m http.server 8000

clean:
	rm -rf results/ paper/figures/*.pdf paper/*.aux paper/*.bbl paper/*.blg \
	       paper/*.log paper/*.out paper/*.toc paper/hotcarwatch.pdf
	find . -name __pycache__ -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
