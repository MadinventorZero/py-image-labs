#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Setting up Brand Image Generator..."

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Create vendor placeholder (no CDN deps at runtime)
mkdir -p ui/js/vendor

# Generate integrity manifest
python3 integrity.py --generate

# Generate launcher
cat > "Brand Image Generator.command" << 'LAUNCHER'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
python3 run.py
LAUNCHER
chmod +x "Brand Image Generator.command"

echo ""
echo "Setup complete. Double-click 'Brand Image Generator.command' to launch."
