# Run from the repository root: make -f integration/Makefile test
PYTHON ?= python3
export PYTHONPATH := $(CURDIR)/integration
SOURCES ?= build/integration/candidates
BUILD_ROOT ?= build/integration/builds
PREFIX_ROOT ?= build/integration/install
JOBS ?= 4
COMPONENT ?= metric-flow-x

.PHONY: test inventory sources build contracts compose-check docs
test:
	$(PYTHON) -m unittest discover -s integration/tests -v
inventory:
	mkdir -p build/integration
	$(PYTHON) -m dealiix inventory --refresh --output build/integration/new-inventory.json
sources:
	$(PYTHON) -m dealiix prepare-sources --manifest integration/sources.json --destination $(SOURCES)
build:
	$(PYTHON) -m dealiix.build $(COMPONENT) --manifest integration/sources.json \
	  --source-root $(SOURCES) --build-root $(BUILD_ROOT) --prefix-root $(PREFIX_ROOT) --jobs $(JOBS) \
	  $(if $(DEAL_II_DIR),--dealii-dir $(DEAL_II_DIR)) $(if $(coral_DIR),--coral-dir $(coral_DIR))
contracts:
	docker buildx build --platform linux/amd64 --target contracts \
	  -f integration/containers/Dockerfile -t dealiix/contracts:integration-v1 --load .
compose-check:
	docker compose -f integration/compose.yaml config --quiet
docs:
	./scripts/build_doc.sh
