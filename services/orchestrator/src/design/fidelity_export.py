"""D41: Deterministic Prototype HTML → React page export (no LLM redraw).

Preserves DOM structure and Tailwind classes; ports head theme (CDN + config);
wires interaction_contract into react-router Link navigations.
"""

from __future__ import annotations

import json
import re
from typing import Any


_ATTR_MAP = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "viewbox": "viewBox",
    "stroke-width": "strokeWidth",
    "stroke-dasharray": "strokeDasharray",
    "fill-opacity": "fillOpacity",
    "clip-path": "clipPath",
    "font-size": "fontSize",
    "font-family": "fontFamily",
    "font-weight": "fontWeight",
    "text-anchor": "textAnchor",
    "stroke-linecap": "strokeLinecap",
    "stroke-linejoin": "strokeLinejoin",
}


def component_name(screen_id: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", screen_id)
    name = "".join(p[:1].upper() + p[1:] for p in parts if p)
    return name or "Screen"


def extract_body_inner(html: str) -> str:
    m = re.search(
        r'class=["\']clutch-canvas["\'][^>]*>([\s\S]*?)</div>\s*</body>',
        html,
        re.I,
    )
    if m:
        return m.group(1).strip()
    m = re.search(r"<body[^>]*>([\s\S]*?)</body>", html, re.I)
    if m:
        return m.group(1).strip()
    return (html or "").strip()


def extract_inline_styles(html: str) -> str:
    chunks: list[str] = []
    for m in re.finditer(r"<style[^>]*>([\s\S]*?)</style>", html or "", re.I):
        chunks.append(m.group(1).strip())
    return "\n\n".join(c for c in chunks if c)


def extract_tailwind_config_js(html: str) -> str:
    """Return `tailwind.config = {...};` body if present in prototype HTML."""
    m = re.search(
        r"tailwind\.config\s*=\s*(\{[\s\S]*?\})\s*;?",
        html or "",
        re.I,
    )
    if not m:
        return ""
    return f"tailwind.config = {m.group(1)};"


def _css_decl_to_react(css: str) -> str:
    parts: list[str] = []
    for decl in css.split(";"):
        if ":" not in decl:
            continue
        key, val = decl.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            continue
        camel = re.sub(r"-([a-z])", lambda m: m.group(1).upper(), key)
        if re.fullmatch(r"-?\d+(\.\d+)?", val):
            parts.append(f"{camel}: {val}")
        else:
            safe = val.replace("\\", "\\\\").replace("'", "\\'")
            parts.append(f"{camel}: '{safe}'")
    return "{" + ", ".join(parts) + "}"


def html_fragment_to_jsx(fragment: str) -> str:
    """Mechanical HTML → JSX. Does not call an LLM."""
    html = fragment or ""
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
    html = re.sub(r"<!--([\s\S]*?)-->", "", html)

    for html_attr, jsx_attr in _ATTR_MAP.items():
        html = re.sub(rf"\b{re.escape(html_attr)}=", f"{jsx_attr}=", html, flags=re.I)

    def _style_sub(m: re.Match[str]) -> str:
        return f"style={{{_css_decl_to_react(m.group(1))}}}"

    html = re.sub(r'\sstyle="([^"]*)"', _style_sub, html)
    html = re.sub(r"\sstyle='([^']*)'", _style_sub, html)

    html = re.sub(r"\s*onclick=\"[^\"]*\"", "", html, flags=re.I)
    html = re.sub(r"\s*onclick='[^']*'", "", html, flags=re.I)

    html = re.sub(
        r"<(img|input|br|hr|meta|link|source|area|col|embed|track|wbr)([^>]*?)(?<!/)>",
        r"<\1\2 />",
        html,
        flags=re.I,
    )

    # Escape bare { } in text nodes between tags (best-effort)
    def _escape_text(m: re.Match[str]) -> str:
        text = m.group(1)
        if "{" not in text and "}" not in text:
            return m.group(0)
        escaped = text.replace("{", "&#123;").replace("}", "&#125;")
        return f">{m.group(0)[0]}{escaped}{m.group(0)[-1]}"

    html = re.sub(r">([^<]+)<", _escape_text, html)
    return html.strip()


def _flow_endpoints(flow: dict[str, Any]) -> tuple[str, str, str]:
    src = str(flow.get("source_screen_id") or flow.get("from") or "").strip()
    label = str(
        flow.get("source_element_text")
        or flow.get("element_label")
        or flow.get("label")
        or ""
    ).strip()
    target = str(
        flow.get("target_screen_id") or flow.get("to") or flow.get("target") or ""
    ).strip()
    return src, label, target


def wire_contract_links(jsx: str, screen_id: str, contract: list[dict[str, Any]]) -> tuple[str, bool]:
    """Replace matching button/a labels with <Link to=\"/target\">. Returns (jsx, used_link)."""
    used_link = False
    out = jsx
    for flow in contract:
        src, label, target = _flow_endpoints(flow)
        if src and src != screen_id:
            continue
        if not label or not target:
            continue
        esc = re.escape(label)
        pattern = rf"<(button|a)(\s[^>]*)?>\s*{esc}\s*</(?:button|a)>"

        def _repl_btn(m: re.Match[str], *, _target: str = target, _label: str = label) -> str:
            nonlocal used_link
            used_link = True
            attrs = m.group(2) or ""
            attrs = re.sub(r"\shref=(['\"]).*?\1", "", attrs, flags=re.I)
            attrs = attrs.strip()
            attr_part = f" {attrs}" if attrs else ""
            return f'<Link to="/{_target}"{attr_part}>{_label}</Link>'

        new_out, n = re.subn(pattern, _repl_btn, out, count=1, flags=re.I | re.DOTALL)
        if n:
            out = new_out
            continue

        text_pat = rf"(?<![>\w]){esc}(?![<\w])"

        def _wrap(m: re.Match[str], *, _target: str = target) -> str:
            nonlocal used_link
            used_link = True
            return f'<Link to="/{_target}" className="cursor-pointer">{m.group(0)}</Link>'

        out2, n2 = re.subn(text_pat, _wrap, out, count=1)
        if n2:
            out = out2
            used_link = True
    return out, used_link


def build_screen_tsx(
    *,
    component_name: str,
    screen_id: str,
    html: str,
    contract: list[dict[str, Any]],
) -> str:
    body = extract_body_inner(html)
    jsx = html_fragment_to_jsx(body)
    jsx, needs_link = wire_contract_links(jsx, screen_id, contract)
    import_block = ""
    if needs_link:
        import_block = "import { Link } from 'react-router-dom';\n\n"
    return (
        f"{import_block}"
        f"/** Deterministic export from prototype screen `{screen_id}` (D41 — no LLM redraw). */\n"
        f"export function {component_name}() {{\n"
        f"  return (\n"
        f"    <div className=\"clutch-screen clutch-screen-{screen_id}\">\n"
        f"{_indent(jsx, 6)}\n"
        f"    </div>\n"
        f"  );\n"
        f"}}\n"
    )


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def build_react_files(
    *,
    app_name: str,
    screens: list[dict[str, Any]],
    design_md: str,
    html_by_id: dict[str, str],
    contract: list[dict[str, Any]],
) -> dict[str, str]:
    """Return relative path → file content for a Vite + React fidelity export."""
    active = [s for s in screens if not s.get("deleted")]
    if not active:
        active = screens
    first = str(active[0]["id"]) if active else "main"
    pkg_name = re.sub(r"[^a-z0-9-]+", "-", (app_name or "app").lower()).strip("-") or "clutch-design-app"

    # Theme from first non-empty HTML (prototype shells share config)
    theme_html = next((html_by_id.get(str(s["id"]), "") for s in active if html_by_id.get(str(s["id"]))), "")
    inline_css = extract_inline_styles(theme_html)
    tw_config = extract_tailwind_config_js(theme_html)
    for s in active:
        sid = str(s["id"])
        inline_css = inline_css or extract_inline_styles(html_by_id.get(sid, ""))
        tw_config = tw_config or extract_tailwind_config_js(html_by_id.get(sid, ""))

    screen_components: dict[str, str] = {}
    for s in active:
        sid = str(s["id"])
        cname = component_name(sid)
        html = html_by_id.get(sid, "")
        if html.strip():
            screen_components[sid] = build_screen_tsx(
                component_name=cname,
                screen_id=sid,
                html=html,
                contract=contract,
            )
        else:
            screen_components[sid] = (
                f"export function {cname}() {{\n"
                f"  return (\n"
                f"    <div className=\"min-h-screen p-8\">\n"
                f"      <h1 className=\"text-2xl font-bold\">{s.get('name', sid)}</h1>\n"
                f"      <p className=\"text-sm opacity-60\">Missing prototype HTML for this screen.</p>\n"
                f"    </div>\n"
                f"  );\n"
                f"}}\n"
            )

    imports = "\n".join(
        f"import {{ {component_name(str(s['id']))} }} from './screens/{component_name(str(s['id']))}';"
        for s in active
    )
    routes = "\n".join(
        f'        <Route path="/{s["id"]}" element={{<{component_name(str(s["id"]))} />}} />'
        for s in active
    )

    tw_script = ""
    if tw_config:
        tw_script = f"<script>\n{tw_config}\n</script>\n"

    index_html = (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        "  <title>Clutch Design</title>\n"
        "  <!-- Prototype-identical Tailwind runtime (D41 fidelity) -->\n"
        "  <script src=\"https://cdn.tailwindcss.com\"></script>\n"
        f"  {tw_script}"
        "</head>\n"
        "<body>\n"
        "  <div id=\"root\"></div>\n"
        "  <script type=\"module\" src=\"/src/main.tsx\"></script>\n"
        "</body>\n"
        "</html>\n"
    )

    files: dict[str, str] = {
        "package.json": json.dumps(
            {
                "name": pkg_name,
                "private": True,
                "version": "0.0.1",
                "type": "module",
                "scripts": {"dev": "vite --host 127.0.0.1", "build": "vite build"},
                "dependencies": {
                    "react": "^19.0.0",
                    "react-dom": "^19.0.0",
                    "react-router-dom": "^7.0.0",
                },
                "devDependencies": {
                    "@vitejs/plugin-react": "^4.3.0",
                    "typescript": "^5.6.0",
                    "vite": "^6.0.0",
                },
            },
            indent=2,
        )
        + "\n",
        "vite.config.ts": (
            "import { defineConfig } from 'vite';\n"
            "import react from '@vitejs/plugin-react';\n"
            "export default defineConfig({\n"
            "  plugins: [react()],\n"
            "  server: { host: '127.0.0.1', strictPort: false },\n"
            "});\n"
        ),
        "index.html": index_html,
        "src/index.css": (
            "/* Extracted from prototype <style> blocks */\n"
            f"{inline_css}\n"
            if inline_css
            else "/* No prototype <style> blocks */\nhtml, body, #root { margin: 0; min-height: 100%; }\n"
        ),
        "src/main.tsx": (
            "import { StrictMode } from 'react';\n"
            "import { createRoot } from 'react-dom/client';\n"
            "import { BrowserRouter } from 'react-router-dom';\n"
            "import App from './App';\n"
            "import './index.css';\n"
            "createRoot(document.getElementById('root')!).render(\n"
            "  <StrictMode>\n"
            "    <BrowserRouter>\n"
            "      <App />\n"
            "    </BrowserRouter>\n"
            "  </StrictMode>\n"
            ");\n"
        ),
        "src/App.tsx": (
            "import { Navigate, Route, Routes } from 'react-router-dom';\n"
            f"{imports}\n"
            "export default function App() {\n"
            "  return (\n"
            "    <Routes>\n"
            f'      <Route path="/" element={{<Navigate to="/{first}" replace />}} />\n'
            f"{routes}\n"
            "    </Routes>\n"
            "  );\n"
            "}\n"
        ),
        "DESIGN.md": design_md or "# Design\n",
        "README.md": (
            "# Clutch Design export (D41)\n\n"
            "Deterministic HTML → React pages from the approved Prototype "
            "(no LLM redraw). UI + client navigation are ready; "
            "wire APIs and business logic next.\n\n"
            "```bash\nnpm install\nnpm run dev\n```\n"
        ),
    }
    for sid, tsx in screen_components.items():
        files[f"src/screens/{component_name(sid)}.tsx"] = tsx
    return files
