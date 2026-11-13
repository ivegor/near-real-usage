# Every command runs in Docker (see Dockerfile): in the image's first stage, the environment, on this repository
# mounted at /app and as the current user, so that the files it writes land here and belong to you. The environment is
# rebuilt only when uv.lock or the Python version change. Without Docker, `uv run python -m thesis ...` does the same.
IMAGE := near-real-usage
RUN := docker run --rm --user "$$(id -u):$$(id -g)" -v "$(CURDIR):/app" $(IMAGE)-env

.PHONY: env serve docker test offline build snapshot census wallets outcomes fetch-value thesis

env:
	docker build --target env -t $(IMAGE)-env .

# the dashboard on http://localhost:8000; building the image runs the tests and the offline build
serve docker:
	docker build -t $(IMAGE) . && docker run --rm -p 8000:8000 $(IMAGE)

test: env
	$(RUN) python -m pytest -q -p no:cacheprovider

offline: env
	$(RUN) python -m thesis build --offline

# downloads the daily series and the fee series from the public APIs
build: env
	$(RUN) python -m thesis build

snapshot: env
	$(RUN) python -m thesis snapshot

# network commands that refresh the committed samples (see README)
census wallets outcomes fetch-value: env
	$(RUN) python -m thesis $@

# any other command with its arguments, e.g. make thesis ARGS="bq-age result.csv" (the file inside the repository)
thesis: env
	$(RUN) python -m thesis $(ARGS)
