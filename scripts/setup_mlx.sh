#!/usr/bin/env bash
set -euo pipefail
python -m pip install --upgrade pip
python -m pip install -e '.[dev,audio]'
python -m pip install mlx
echo 'Install the current upstream MLX Qwen3-ASR backend/model separately.'
