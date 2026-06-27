.PHONY: init list update upgrade format lint check test build clean ci config pages
.PHONY: dev staging verify verify-fast verify-one
.PHONY: verify-chat verify-embedding verify-depthpro verify-ernie verify-flux2
.PHONY: verify-ideogram4 verify-qwen verify-seedvr2 verify-zimage
.PHONY: verify-acestep verify-audiogen verify-ltx2 verify-web
.PHONY: verify-relay verify-relay-local verify-relay-gcp
.DEFAULT_GOAL := check

init:
	mise run setup
list:
	uv pip list
update:
	uv sync --all-packages --all-extras --all-groups
	uv pip list --outdated
upgrade:
	uv sync --upgrade --all-packages --all-extras --all-groups
clean:
	mise run clean

format:
	mise run format
lint:
	mise run lint
test:
	mise run test
build:
	mise run build

config:
	mkdir -p config
	uv run kiapi config template > config/settings.full-template.yaml
pages:
	uv run python scripts/build_pages.py
check:
	mise run format
	mise run lint
	make config
	make pages
ci:
	mise run ci

dev:
	uv run kiapi run --host 127.0.0.1 --port 8000 --debug
staging:
	uv run kiapi run --host 0.0.0.0 --port 8500 --debug
verify:
	mise run verify
verify-fast:
	mise run verify --fast
verify-one:
	mise run verify embedding
verify-chat:
	mise run verify chat
verify-embedding:
	mise run verify embedding
verify-depthpro:
	mise run verify depthpro
verify-ernie:
	mise run verify ernie
verify-flux2:
	mise run verify flux2
verify-ideogram4:
	mise run verify ideogram4
verify-qwen:
	mise run verify qwen
verify-seedvr2:
	mise run verify seedvr2
verify-zimage:
	mise run verify zimage
verify-acestep:
	mise run verify acestep
verify-audiogen:
	mise run verify audiogen
verify-ltx2:
	mise run verify ltx2
verify-web:
	mise run verify web
verify-relay:
	mise run verify relay
verify-relay-local:
	mise run verify relay-local
verify-relay-gcp:
	mise run verify relay-gcp
