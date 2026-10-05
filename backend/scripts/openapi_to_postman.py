"""Build a Postman collection (v2.1) from the API's OpenAPI schema.

    python manage.py spectacular --format openapi-json --file ../docs/api/openapi.json
    python scripts/openapi_to_postman.py ../docs/api/openapi.json ../docs/api/vargani.postman_collection.json

Requests are grouped by tag. Every request sends `Authorization: Bearer {{accessToken}}` and
`X-Organization-ID: {{organizationId}}`; the login requests save the returned tokens into those variables.
"""

import json
import re
import sys

LOGIN_PATHS = {"/api/v1/auth/login/", "/api/v1/auth/verify/", "/api/v1/auth/otp/verify/", "/api/v1/auth/refresh/"}
SAVE_TOKENS = [
    "const data = pm.response.json();",
    "if (data.access) pm.collectionVariables.set('accessToken', data.access);",
    "if (data.refresh) pm.collectionVariables.set('refreshToken', data.refresh);",
]


def resolve(schema, spec, depth=0):
    if depth > 6 or not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return resolve(spec["components"]["schemas"][name], spec, depth + 1)
    return schema


def example(schema, spec, depth=0):
    """A small example body: required and writable fields, with readable placeholder values."""
    schema = resolve(schema, spec, depth)
    if not isinstance(schema, dict) or depth > 5:
        return None
    for key in ("allOf", "oneOf", "anyOf"):
        if key in schema:
            return example(schema[key][0], spec, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        out = {}
        for name, prop in props.items():
            prop_resolved = resolve(prop, spec, depth + 1)
            if prop_resolved.get("readOnly"):
                continue
            if required and name not in required and len(props) > 6:
                continue
            out[name] = example(prop, spec, depth + 1)
        return out
    if kind == "array":
        item = example(schema.get("items", {}), spec, depth + 1)
        return [item] if item is not None else []
    fmt = schema.get("format", "")
    if kind == "string":
        return {"uuid": "{{id}}", "date": "2026-09-01", "date-time": "2026-09-01T10:00:00+05:30", "decimal": "501.00",
                "email": "name@example.com", "binary": None}.get(fmt, "")
    if kind == "integer":
        return 1
    if kind == "number":
        return 1
    if kind == "boolean":
        return False
    return None


def build(spec):
    folders = {}
    for path, operations in sorted(spec["paths"].items()):
        for method, op in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            tag = (op.get("tags") or ["other"])[0]
            url_path = re.sub(r"\{(\w+)\}", r":\1", path)
            segments = [s for s in url_path.strip("/").split("/") if s]
            request = {
                "method": method.upper(),
                "header": [
                    {"key": "Authorization", "value": "Bearer {{accessToken}}"},
                    {"key": "X-Organization-ID", "value": "{{organizationId}}"},
                    {"key": "Accept-Language", "value": "{{language}}"},
                    {"key": "X-Client-Type", "value": "app"},
                ],
                "url": {
                    "raw": "{{baseUrl}}" + url_path,
                    "host": ["{{baseUrl}}"],
                    "path": segments,
                    "variable": [{"key": s[1:], "value": ""} for s in segments if s.startswith(":")],
                    "query": [
                        {"key": p["name"], "value": "", "disabled": True, "description": p.get("description", "")}
                        for p in op.get("parameters", [])
                        if p.get("in") == "query"
                    ],
                },
                "description": op.get("description", ""),
            }
            content = (op.get("requestBody") or {}).get("content", {})
            if "application/json" in content:
                body = example(content["application/json"].get("schema", {}), spec)
                request["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(body, indent=2, ensure_ascii=False),
                    "options": {"raw": {"language": "json"}},
                }
                request["header"].append({"key": "Content-Type", "value": "application/json"})
            elif "multipart/form-data" in content:
                props = resolve(content["multipart/form-data"].get("schema", {}), spec).get("properties", {})
                request["body"] = {
                    "mode": "formdata",
                    "formdata": [
                        {"key": k, "type": "file" if v.get("format") == "binary" else "text", "value": ""}
                        for k, v in props.items()
                    ],
                }
            item = {"name": op.get("summary") or f"{method.upper()} {path}", "request": request}
            if path in LOGIN_PATHS:
                item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": SAVE_TOKENS}}]
            folders.setdefault(tag, []).append(item)
    return {
        "info": {
            "name": "Vargani API",
            "description": spec["info"].get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000"},
            {"key": "accessToken", "value": ""},
            {"key": "refreshToken", "value": ""},
            {"key": "organizationId", "value": ""},
            {"key": "language", "value": "en"},
            {"key": "id", "value": ""},
        ],
        "item": [{"name": tag, "item": items} for tag, items in sorted(folders.items())],
    }


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    with open(source, encoding="utf-8") as fh:
        spec = json.load(fh)
    collection = build(spec)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, indent=2, ensure_ascii=False)
    count = sum(len(f["item"]) for f in collection["item"])
    print(f"{count} requests in {len(collection['item'])} folders → {target}")
