# Reading an OpenAPI spec without crying

OpenAPI (formerly Swagger) specs are great if you only need the endpoint list,
and infuriating the moment you actually try to generate a client. Notes from
doing this a few times.

## Where to find the spec

Most APIs publish it at a well-known path. Try these in order:

```
/openapi.json      # OpenAPI 3.x, JSON
/openapi.yaml      # OpenAPI 3.x, YAML
/swagger.json      # often Swagger 2.0 — a different schema!
/v3/api-docs       # Spring Boot default
/redoc             # a *rendered* page, not the spec — don't curl this
```

Check the `openapi:` / `swagger:` top-level key to know which version you're on:

```bash
curl -s https://api.example.com/openapi.json | python -c \
  "import sys,json; d=json.load(sys.stdin); print(d.get('openapi') or d.get('swagger'))"
```

`3.0.x` and `2.0` are *not* interchangeable. Tooling that wants 3.x will choke
on a 2.0 file. Convert with `swagger2openapi` if needed.

## What actually matters in the file

For day-to-day work you only need four sections. Ignore the rest.

- `servers[].url` — the base URL. Specs lie about this constantly; a spec
  generated for localhost often ships with `http://localhost:8080`. Override it.
- `paths` — the endpoints. Each has methods, parameters, and request/response
  schemas referenced via `$ref`.
- `components.securitySchemes` — how to authenticate. Values are usually
  `http`+`bearer`, `apiKey`, or `oauth2`.
- `components.schemas` — the object shapes. `$ref` targets point here.

## Resolving $refs by hand

Specs are full of `{"$ref": "#/components/schemas/User"}`. To see what a `User`
is without a tool:

```bash
curl -s https://api.example.com/openapi.json \
  | python -c "import sys,json; print(json.dumps(json.load(sys.stdin)['components']['schemas']['User'], indent=2))"
```

Quick and dirty but it works when you just want one shape.

## Generating a client

```bash
# Official generator (Java-based, slow, but most complete)
npx @openapitools/openapi-generator-cli generate \
  -i openapi.json -g python -o ./client

# If the spec is 3.0 and you want typed models, this is nicer:
pip install openapi-python-client
openapi-python-client generate --path openapi.json
```

Reality check: generated clients are hit-or-miss. I've had good luck with
`openapi-python-client` on clean specs and bad luck with the Java generator
producing 400 files for a 6-endpoint API. Read the generated code before you
commit it.

## Validating a spec

A spec with a typo silently breaks every consumer. Validate before shipping:

```bash
npx @redocly/cli lint openapi.yaml
npx swagger-cli validate openapi.json
```

`redocly lint` catches the common stuff: missing operationIds, unreferenced
schemas, examples that don't match their schema.

## Generating docs from the spec

```bash
npx @redocly/cli build-docs openapi.yaml -o docs.html
```

Produces a single self-contained HTML file with a "try it" console. Good enough
for internal docs; no server needed.

## Gotchas that cost me time

- **`nullable` vs `optional`.** In OpenAPI 3.0 a field can be absent
  (`required: false`) *and* present-but-null (`nullable: true`). Generated code
  handles these differently. Read the schema, don't assume.
- **`allOf` composition.** Models built from `allOf` are flattened by some
  generators and kept as mixins by others. If a model is missing fields, look
  for `allOf`.
- **`additionalProperties: true`** means the object can carry arbitrary keys.
  Typed clients often drop them. If you need them, use the raw dict.
- **Date formats.** `format: date-time` should be RFC 3339, but I've seen
  servers return epoch millis anyway. Parse defensively.
- **Broken `$ref`s across files.** Multi-file specs (`$ref: './user.yaml'`)
  confuse simple tools. Bundle first: `npx swagger-cli bundle openapi.yaml -o bundled.json`.
