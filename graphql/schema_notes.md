# GraphQL schema notes

Notes from poking at real GraphQL endpoints. Assumes you already know the basic
query/mutation split.

## Introspection: get the schema as JSON

GraphQL has a built-in introspection system. You can dump the whole schema with
a single query. This is how tools like GraphiQL and Apollo autocomplete work.

```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    types {
      name
      kind
      fields {
        name
        type { name kind ofType { name kind } }
      }
    }
  }
}
```

Fire it at the endpoint with `curl`:

```bash
curl -s https://countries.trevorblades.com/ \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ __schema { queryType { name } types { name } } }"}' \
  | python -m json.tool | head -40
```

Many production endpoints disable introspection (`__schema` returns an error).
If it's off, ask for the SDL file or use `graphql-cli` against a running dev
instance.

## Getting the SDL

If introspection is enabled, fetch the raw schema definition:

```bash
# needs: npm i -g graphql-cli  (or use get-graphql-schema)
npx get-graphql-schema https://countries.trevorblades.com/ > schema.graphql
```

Now you have a `schema.graphql` you can grep and read offline. Much nicer than
guessing field names.

## Nested fields and N+1

GraphQL's selling point is that you fetch exactly what you need in one round
trip. That's also its trap: a deeply nested query can hammer the backend even
though the client sent one request.

```graphql
{
  continents {
    countries {
      languages { name }
    }
  }
}
```

That's one HTTP request but potentially thousands of DB lookups server-side.
Real servers add depth/complexity limits and return errors like
`"Query is too complex: 1042 > max 500"`. If you see that, split the query.

## Errors come back with HTTP 200

Unlike REST, a GraphQL endpoint usually returns `200 OK` even when the query
failed. You have to check the `errors` key:

```json
{
  "data": { "country": null },
  "errors": [
    { "message": "Cannot query field \"captial\" on type \"Country\".",
      "locations": [{"line": 1, "column": 24}] }
  ]
}
```

Note `data` can be partially populated when only some fields errored. The spec
allows `data` and `errors` to coexist.

## Variables, not string interpolation

Wrong:

```python
query = f'{{ country(code: "{user_input}") {{ name }} }}'   # injection risk
```

Right:

```python
query = "query($code: ID!) { country(code: $code) { name } }"
variables = {"code": user_input}
```

The server parses and validates variables against the schema. This is the only
safe way to pass dynamic values.

## Pagination

GraphQL has no built-in pagination standard, but the Relay "connections" spec is
everywhere:

```graphql
query($cursor: String) {
  users(first: 20, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges { node { id name } }
  }
}
```

`pageInfo.hasNextPage` tells you when to stop; `endCursor` is what you feed back
as `after`. See rest/pagination.py for the REST-side equivalent.

## Tools worth knowing

- **GraphiQL / Apollo Sandbox** — browser IDE with schema-aware autocomplete.
  Point it at any endpoint that has introspection on.
- **graphql-cli** — `graphql get-schema` for SDL, `graphql query` to run saved
  queries from files.
- **`gql` (python)** — if you want typed results instead of dicts. Adds a
  codegen step; only worth it on a big schema.

## Caveat

Field names in this file are illustrative. Always run introspection against the
actual endpoint before copy-pasting a query — I've lost time to `capital` vs
`capitalCity` more than once.
