#!/usr/bin/env bash
set -euo pipefail

have() {
  command -v "$1" >/dev/null 2>&1
}

find_local() {
  if have "$1"; then
    command -v "$1"
    return 0
  fi
  if [ -x "$HOME/.local/bin/$1" ]; then
    printf '%s\n' "$HOME/.local/bin/$1"
    return 0
  fi
  return 1
}

install_with_brew() {
  local package="$1"
  if ! have brew; then
    echo "ERROR: Homebrew is required for automatic installation on macOS."
    echo "Install Homebrew first, then rerun this script."
    exit 1
  fi
  brew install "$package"
}

if ! have python3 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "ERROR: Python 3.10 or newer is required. Install it, then rerun bootstrap."
  exit 1
fi

if ! find_local pandoc >/dev/null; then
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "Installing pandoc..."
    install_with_brew pandoc
  else
    echo "ERROR: pandoc is missing. Automatic installation is currently supported by this skill on macOS/Homebrew."
    exit 1
  fi
fi

if ! find_local epub2md >/dev/null; then
  if ! find_local uv >/dev/null; then
    if [ "$(uname -s)" = "Darwin" ]; then
      echo "Installing uv..."
      install_with_brew uv
    else
      echo "ERROR: uv is missing. Automatic installation is currently supported by this skill on macOS/Homebrew."
      exit 1
    fi
  fi
  echo "Installing epub2md with uv..."
  "$(find_local uv)" tool install epub2md
fi

echo
echo "Ready:"
printf '  pandoc:  %s\n' "$(find_local pandoc)"
printf '  epub2md: %s\n' "$(find_local epub2md)"
