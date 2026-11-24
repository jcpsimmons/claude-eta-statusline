#!/usr/bin/env bash
# Install claude-eta-statusline.
#   ./install.sh                 install everything
#   ./install.sh --no-claude-md  skip adding the instructions to ~/.claude/CLAUDE.md
#   ./install.sh --force         replace an existing statusLine setting
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
DEST="$CLAUDE_DIR/eta-statusline"
BIN="${CLAUDE_ETA_BIN:-$HOME/.local/bin}"
SETTINGS="$CLAUDE_DIR/settings.json"
MD="$CLAUDE_DIR/CLAUDE.md"
ADD_MD=1
FORCE=0
for a in "$@"; do
  case "$a" in
    --no-claude-md) ADD_MD=0 ;;
    --force) FORCE=1 ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }

mkdir -p "$DEST" "$BIN" "$CLAUDE_DIR/eta"
install -m 755 "$HERE/statusline.py" "$DEST/statusline.py"
install -m 755 "$HERE/claude-eta" "$DEST/claude-eta"
ln -sf "$DEST/claude-eta" "$BIN/claude-eta"
echo "✓ installed scripts to $DEST"
echo "✓ linked $BIN/claude-eta"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "! $BIN is not on your PATH; add it so Claude can run claude-eta" ;; esac

# Merge the statusLine setting.
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
cp "$SETTINGS" "$SETTINGS.bak-eta-$(date +%Y%m%d%H%M%S)"
python3 - "$SETTINGS" "$DEST/statusline.py" "$FORCE" <<'EOF'
import json, sys
path, script, force = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
with open(path) as f:
    s = json.load(f)
cur = s.get("statusLine")
if cur and script not in json.dumps(cur) and not force:
    print(f"! statusLine already set ({cur.get('command')}); rerun with --force to replace it")
    sys.exit(0)
s["statusLine"] = {"type": "command", "command": f"python3 {script}", "padding": 0, "refreshInterval": 1}
with open(path, "w") as f:
    json.dump(s, f, indent=2)
    f.write("\n")
print("✓ statusLine set in", path)
EOF

if [ "$ADD_MD" = 1 ]; then
  if [ -f "$MD" ] && grep -q "claude-eta start" "$MD"; then
    echo "✓ CLAUDE.md already has the progress-bar rule"
  else
    { [ -s "$MD" ] && printf '\n'; cat "$HERE/CLAUDE-snippet.md"; } >> "$MD"
    echo "✓ added the progress-bar rule to $MD"
  fi
fi

echo "Done. Restart Claude Code (or start a new session) to see it."
