# Examples

## Counter (`counter.html`)

A minimal htmx + django-cotton example. Clicking +/- updates the count without a full page reload.

### How it works

1. `counter.html` renders the full page using `<c-layout>` and `<c-counter>`
2. The +/- buttons use `hx-post` to hit the update endpoint
3. The server re-renders only the `<c-counter>` cotton component and swaps it in via htmx

### URL

`/examples/counter/`
