.DEFAULT_GOAL := default
.PHONY: build bump-version clean config default publish publish-test
default: format lint config pages
#--------------------------------------------------
init:
	uv sync --all-groups --all-extras
	mise run download
list:
	uv pip list
	uv pip list --outdated
update:
	uv sync --all-groups --all-extras
	uv run kiapi activate --repo mlx-video-ltx2
upgrade:
	uv sync --upgrade --all-groups --all-extras
	uv run kiapi activate --repo mlx-video-ltx2
#--------------------------------------------------
format:
	uv run ruff format kiapi tests scripts
	uv run ruff check --fix kiapi tests scripts
format-unsafe:
	uv run ruff format kiapi tests scripts
	uv run ruff check --fix --unsafe-fixes kiapi tests scripts
lint:
	uv run ruff check kiapi tests scripts
	uv run mypy kiapi tests scripts
test:
	uv run pytest tests/
#--------------------------------------------------
dev:
	uv run kiapi run --host 127.0.0.1 --port 8000 --debug
staging:
	uv run kiapi run --host 0.0.0.0 --port 8500 --debug
#--------------------------------------------------
verify:
	mise run verify
verify-fast:
	mise run verify --fast
verify-one:
	uv run python scripts/verify_embedding.py
# chat
verify-chat:
	uv run python scripts/verify_chat.py
# embedding
verify-embedding:
	uv run python scripts/verify_embedding.py
# image
verify-depthpro:
	uv run python scripts/verify_depthpro.py
verify-ernie:
	KIAPI_VERIFY_ERNIE_TRAIN=1 uv run python scripts/verify_ernie.py
verify-flux2:
	KIAPI_VERIFY_FLUX2_TRAIN=1 uv run python scripts/verify_flux2.py
verify-ideogram4:
	uv run python scripts/verify_ideogram4.py
verify-qwen:
	uv run python scripts/verify_qwen.py
verify-seedvr2:
	uv run python scripts/verify_seedvr2.py
verify-zimage:
	KIAPI_VERIFY_ZIMAGE_TRAIN=1 uv run python scripts/verify_zimage.py
# audio
verify-acestep:
	uv run python scripts/verify_acestep.py
verify-audiogen:
	uv run python scripts/verify_audiogen.py
# video
verify-ltx2:
	uv run python scripts/verify_ltx2.py
# web
verify-web:
	uv run python scripts/verify_web.py
# relay
verify-relay:
	uv run python scripts/relay/verify.py
verify-relay-local:
	uv run python scripts/relay/verify_local.py
verify-relay-gcp:
	uv run python scripts/relay/verify_gcp.py
#--------------------------------------------------
config:
	mkdir -p config
	uv run kiapi config template > config/settings.full-template.yaml
pages:
	uv run python scripts/build_pages.py
#--------------------------------------------------
bump-version:
	mise run bump-version
clean:
	mise run clean
build:
	mise run build
publish-test:
	mise run publish --test
publish:
	mise run publish
#--------------------------------------------------
install:
	uv run kiapi service install
start:
	uv run kiapi service start
stop:
	uv run kiapi service stop
uninstall:
	uv run kiapi service uninstall
