# Security Policy

Thanks for helping keep PolePosition and its users safe.

## Supported versions

PolePosition is pre-1.0 (beta). Only the latest release published to
[PyPI](https://pypi.org/project/poleposition/) receives security fixes. Fixes
are not backported to older versions; upgrade to the latest release.

| Version              | Supported          |
| -------------------- | ------------------ |
| Latest PyPI release  | :white_check_mark: |
| Any older release    | :x:                |

## Reporting a vulnerability

Please report security issues **privately**. Do not open a public issue, pull
request, or discussion for a suspected vulnerability.

- Preferred: use GitHub's private vulnerability reporting. Go to the
  repository's **Security** tab and choose **Report a vulnerability**, or open
  <https://github.com/polepos/poleposition/security/advisories/new>. This
  creates a private advisory visible only to the maintainers.

Please include enough detail to reproduce: affected version, environment,
steps, and the impact you observed. A minimal proof of concept helps a lot.

### What to expect

- Acknowledgement of your report within about 3 business days.
- An initial assessment (in scope, severity, next steps) within about 7 days.
- Coordinated disclosure: we will agree on a timeline with you and credit you
  in the release notes and advisory unless you prefer to stay anonymous.

The project is maintained on a best-effort basis, so timelines may vary; we
will keep you updated.

## Scope

**In scope**

- The published `poleposition` package and CLI code.
- The project templates the CLI generates, where a generated default could
  introduce a vulnerability in a scaffolded project.

**Out of scope / your responsibility**

- Dependencies of a project you generate. PolePosition's CLI itself declares no
  runtime dependencies; generated projects pin their own dependencies (for
  example `fastapi[standard]`) and you resolve them with `uv lock`. Keep those
  updated and watch your own Dependabot alerts.
- The example applications under `examples/`. They are demonstrations; their
  pinned lockfiles are kept current but are not a supported deployment target.

## Good-faith research

We will not pursue or support action against researchers who report in good
faith, avoid privacy violations and service disruption, and give us reasonable
time to remediate before public disclosure.
