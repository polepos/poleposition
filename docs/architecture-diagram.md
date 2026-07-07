# Architecture Diagram

This diagram shows the current PolePosition lifecycle flow: CLI commands,
service-layer responsibilities, generated FastAPI project structure, optional
integrations, tests, migrations, and Docker support.

It includes the current module archetypes across two axes, interface
(HTTP routes vs. internal) and persistence (with vs. without a database):
`api`, `crud`, `ai-prompt`, `api-only`, `service`, and `service-only`.

<iframe
  src="assets/diagram/poleposition-cli-architecture.html"
  title="PolePosition architecture diagram"
  style={{width: "100%", minHeight: "780px", border: 0}}
></iframe>
