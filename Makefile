.PHONY: test gui lint fmt screenshots clean

test:           ## run the whole headless test-suite
	pytest

gui:            ## launch the graphical app (falls back to the CLI)
	python -m calc

cli:            ## launch the terminal interface
	python -m calc cli

lint:           ## static analysis
	ruff check calc tests

fmt:            ## auto-fix style issues
	ruff check --fix calc tests

screenshots:    ## regenerate README screenshots from the running app
	QT_QPA_PLATFORM=offscreen python scripts/make_screenshots.py

clean:
	rm -rf .pytest_cache .ruff_cache .coverage build dist *.egg-info
