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

Configure `TEXT_MODEL` and `TEXT_API_KEY` to enable live inference. The optional
`TEXT_API_BASE_URL` defaults to `https://api.openai.com/v1`, and
`TEXT_TIMEOUT_SECONDS` defaults to `8`. Responses identify both the adapter/model and
the `smishx-text-v1` prompt version. A model category is categorical output, not a
probability or calibrated risk score.
