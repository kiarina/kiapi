.PHONY: init list sync update upgrade format lint check test build clean ci config pages
.PHONY: dev staging verify verify-fast
.PHONY: verify-kiapi verify-kiapi-relay verify-kiapi-proxy
.DEFAULT_GOAL := check
#--------------------------------------------------
init:
	mise run setup
list:
	uv pip list
sync:
	uv sync --all-packages --all-extras --all-groups
update:
	uv sync --inexact --all-packages --all-extras --all-groups
	uv pip list --outdated
upgrade:
	uv sync --inexact --upgrade --all-packages --all-extras --all-groups
clean:
	mise run clean
#--------------------------------------------------
setup-relay-gcp:
	mise -C packages/kiapi-relay run gcp:setup
#--------------------------------------------------
test-settings-upload:
	mise run test-settings:upload .env test_settings.yaml
test-settings-download:
	mise run test-settings:download
#--------------------------------------------------
format:
	mise run format
lint:
	mise run lint
test:
	mise run test
build:
	mise run build
#--------------------------------------------------
config:
	mkdir -p config
	uv run kiapi config template > config/settings.full-template.yaml
pages:
	uv run python scripts/build_pages.py
#--------------------------------------------------
check:
	mise run format
	mise run lint
	make config
	make pages
ci:
	mise run ci
#--------------------------------------------------
dev:
	uv run kiapi run --host 127.0.0.1 --port 8000 --debug
staging:
	uv run kiapi run --host 0.0.0.0 --port 8500 --relay gcp --debug
#--------------------------------------------------
verify:
	mise run verify
verify-fast:
	mise run verify --fast
verify-kiapi:
	mise run verify --kiapi
verify-kiapi-relay:
	mise run verify --kiapi-relay
verify-kiapi-proxy:
	mise run verify --kiapi-proxy
verify-kiapi-proxy-fastest:
	mise run verify --kiapi-proxy --family embedding
