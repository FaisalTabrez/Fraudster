# End to end checks

Priya owns browser-level tests after the frozen P0 UI is merged. The bootstrap keeps this directory as the agreed boundary. E2E checks must use fixture mode or local inert URLs, must never open submitted links, and must assert that unavailable coverage and the Demo data badge remain visible.
