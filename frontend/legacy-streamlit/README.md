# N7 UI Module

N7 is the Streamlit frontend for the project. It manages the interactive user flow, captures travel preferences through multiple input modes, sends requests to the backend API, and renders ranked location and activity results.

## Responsibilities

- Configure the Streamlit page and inject custom styling
- Initialize and manage session state
- Render the input view and collect user payloads
- Send recommendation requests to the local backend API
- Render result views and handle empty or error states

## Entry Point

```python
app.py
```

## Request Behavior

When the user submits input, N7 sends a `POST` request to:

```text
http://localhost:{API_PORT}/recommend
```

with:

- JSON request body from the active input view
- `X-Internal-Key` header for protected API access
- a `60` second request timeout

## State Flow

N7 uses Streamlit session state to manage three main phases:

1. input mode: show the active input interface and collect a payload
2. pending request: send the payload to the backend and wait for a response
3. result mode: render recommendation results after a successful response

The main session keys used in `app.py` are:

- `mode`
- `payload`
- `results`
- `activity_results`

## UI Behavior

- if input is submitted, the app switches to results mode and reruns
- if the backend returns `200 OK`, the JSON response is stored in session state
- if the backend returns an error status, the UI shows a server error message
- if the request fails entirely, the UI shows a connection error message
- if the results page is opened without available data, the UI offers a return button

## Runtime Notes

- page layout is configured as `wide`
- the sidebar starts collapsed
- styling and view rendering are delegated to local `styles/`, `views/`, and `state.py`
- logging is configured through the project logging helper
