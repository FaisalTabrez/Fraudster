# Text detector

This service is a text-only adaptation of the category guidance reviewed in
[SmishX](https://github.com/yizhu-joy/SmishX) at commit
`116a8c827741e0572563f678d25ed04306b1e3ff`. No upstream runtime source or model
asset is copied. The pinned MIT notice is retained in
`third_party/licenses/SmishX-LICENSE.txt`.

The adapter sends only the submitted message text to the configured structured-output
provider. It does not fetch, follow, expand, or browse URLs, and it creates no output
files. Provider output is accepted only when it matches the four-category schema and
every evidence quote is an exact substring of the submitted text.

## Claude API configuration

The default live provider is Anthropic's native Messages API. Configure the secret only
on the backend:

```dotenv
TEXT_PROVIDER=anthropic
TEXT_MODEL=claude-haiku-5-5
TEXT_API_KEY=replace-with-an-anthropic-api-key
TEXT_API_BASE_URL=https://api.anthropic.com
TEXT_TIMEOUT_SECONDS=8
```

The adapter sends `POST /v1/messages` with Anthropic's version header and a constrained
JSON output schema. It accepts only a normally completed response with one JSON text
block, validates that output again with Pydantic, and rejects evidence quotes that are
not exact substrings of the submitted message. Provider error bodies and raw responses
are never returned to the browser.

For an existing OpenAI-compatible endpoint, set `TEXT_PROVIDER=openai_compatible` and
provide the corresponding base URL and model. Responses identify the provider,
adapter/model, and the `smishx-text-v1` prompt version. A model category is categorical
output, not a probability or calibrated risk score.
