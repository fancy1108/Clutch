"""React code generator — Interaction Contract → React + Tailwind components.

Reads the interaction contract and screen HTMLs from a design session,
generates a working React application with:
  - One component per screen (HTML → JSX)
  - useState-based navigation
  - onClick handlers from the interaction contract
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from src.design.session_store import (
    read_manifest,
    resolve_screen_html_path,
    session_dir,
)

_CONTRACT_FILE = "interaction_contract.json"

# HTML attributes that need to become JSX equivalents
_ATTR_MAP: Dict[str, str] = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "viewbox": "viewBox",
    "stroke-width": "strokeWidth",
    "stroke-dasharray": "strokeDasharray",
    "fill-opacity": "fillOpacity",
}


def _html_to_jsx(html: str) -> str:
    """Convert an HTML string to JSX.

    Handles: className, htmlFor, self-closing tags, style strings.
    """
    # Replace attribute names
    for html_attr, jsx_attr in _ATTR_MAP.items():
        html = re.sub(rf'\b{html_attr}=', f'{jsx_attr}=', html)

    # Self-closing tags: <img ...> → <img ... />
    html = re.sub(r'<(img|input|br|hr|meta|link)([^>]*?)(?<!/)>', r'<\1\2 />', html)

    # Wrap inline styles in {{}}
    html = re.sub(r'style="([^"]*)"', r'style={{\1}}', html)

    # Wrap inline event handlers (onclick → onClick={...}):
    # Remove onclick attributes — we'll add our own via the contract
    html = re.sub(r'\s*onclick="[^"]*"', '', html, flags=re.IGNORECASE)

    return html


def _escape_jsx_text(text: str) -> str:
    """Escape { and } in JSX text content."""
    return text.replace("{", "&#123;").replace("}", "&#125;")


def generate_react_app(run_id: str) -> Dict[str, str]:
    """Generate React application code from a design session.

    Args:
        run_id: Design session run ID

    Returns:
        Dict mapping filename → file content for all generated files.
    """
    sdir = session_dir(run_id)
    manifest = read_manifest(sdir)
    screens: List[Dict[str, Any]] = manifest.get("screens", [])

    # Load contract
    contract_path = sdir / _CONTRACT_FILE
    flows: List[Dict[str, Any]] = []
    if contract_path.is_file():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        flows = contract.get("interactions", [])

    # Build screen lookup
    screen_by_id: Dict[str, Dict[str, Any]] = {s["id"]: s for s in screens}
    screen_names: Dict[str, str] = {}
    screen_components: Dict[str, str] = {}

    # Generate one component per screen
    for screen in screens:
        sid = screen["id"]
        name = screen.get("name", sid)
        screen_names[sid] = name
        component_name = _to_component_name(name)

        html_path = resolve_screen_html_path(sdir, screen)
        html = ""
        if html_path.is_file():
            html = html_path.read_text(encoding="utf-8")

        jsx = _html_to_jsx(html)

        # Find flows FROM this screen and inject onClick handlers
        outbound = [f for f in flows if f.get("from") == sid]
        for flow in outbound:
            source_text = flow.get("source_element_text", "")
            target_id = flow.get("to", "")
            if not source_text or not target_id:
                continue
            target_name = screen_names.get(target_id, target_id)
            # Replace the element containing this text with an onClick wrapper
            escaped_text = re.escape(source_text)
            handler = f'<button onClick={{() => setCurrentScreen("{target_id}")}} className="cursor-pointer hover:opacity-80 transition-opacity">{source_text}</button>'
            # Try to match a <button> or <a> containing exactly this text
            pattern = rf'(<(?:button|a)\b[^>]*?>\s*{escaped_text}\s*</(?:button|a)>)'
            if re.search(pattern, jsx, re.IGNORECASE | re.DOTALL):
                jsx = re.sub(pattern, handler, jsx, count=1, flags=re.IGNORECASE | re.DOTALL)
            else:
                # Fallback: wrap bare text in a clickable span
                pattern2 = rf'(?<![>\w]){escaped_text}(?![<\w])'
                if re.search(pattern2, jsx):
                    jsx = re.sub(pattern2, handler, jsx, count=1)

        screen_components[sid] = f"""function {component_name}() {{
  return (
    <div className="screen-{sid}">
      {jsx.strip()}
    </div>
  );
}}"""

    # Generate App component
    imports = "\n".join(
        f"import {{ {name} }} from './screens/{name}';"
        for name in sorted(set(_to_component_name(screen_names[sid]) for sid in screen_names))
    )

    screen_routes = "\n      ".join(
        f"""{{currentScreen === '{sid}' && <{_to_component_name(screen_names[sid])} />}}"""
        for sid in screen_names
    )

    first_screen = screens[0]["id"] if screens else ""

    app_code = f"""import React, {{ useState }} from 'react';
{imports}

export default function App() {{
  const [currentScreen, setCurrentScreen] = useState('{first_screen}');

  return (
    <div className="min-h-screen bg-gray-50">
      {screen_routes}
    </div>
  );
}}
"""

    # Collect all files
    files: Dict[str, str] = {
        "App.tsx": app_code,
    }
    for sid, code in screen_components.items():
        name = _to_component_name(screen_names[sid])
        files[f"screens/{name}.tsx"] = code

    # Generate index.tsx
    first_import = _to_component_name(screen_names[first_screen]) if first_screen else "App"
    files["index.tsx"] = f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

    # Generate package.json
    files["package.json"] = json.dumps({
        "name": "clutch-generated-app",
        "private": True,
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
        },
        "dependencies": {
            "react": "^19.0.0",
            "react-dom": "^19.0.0",
        },
        "devDependencies": {
            "@vitejs/plugin-react": "^4.0.0",
            "vite": "^6.0.0",
            "tailwindcss": "^4.0.0",
            "@tailwindcss/vite": "^4.0.0",
        },
    }, indent=2)

    # Generate vite config
    files["vite.config.ts"] = """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
});
"""

    # Generate index.css
    files["index.css"] = """@import "tailwindcss";
"""

    return files


def _to_component_name(name: str) -> str:
    """Convert a screen name to a valid React component name."""
    # Remove non-alphanumeric, capitalize words
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    words = cleaned.split()
    return ''.join(w.capitalize() for w in words) or 'Screen'
