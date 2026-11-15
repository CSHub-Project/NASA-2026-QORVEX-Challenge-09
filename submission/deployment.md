# Judge-facing deployment

## Preferred free URL

The preferred free-hosting target is `fyrora.web.app` because it is shorter
than the equivalent Pages and Vercel subdomains and still keeps the full brand
name. The address is not reserved until a Firebase project with the matching ID
is created; do not print it in the video or project page before the live URL is
verified.

`firebase.json` serves the existing `dist/` directory without changing the
scientific build. The repository remains private and no deployment should occur
until the judge-facing source and demo are approved for release.

## Fallback order

1. `fyrora.web.app`, if the Firebase project ID is available.
2. `fyrora.pages.dev`, if the Cloudflare project name is available.
3. GitHub Pages, using the existing workflow and repository path.
4. A purchased custom domain later; hosting does not need to change.

## Optional NASA participant domain offer

The 2026 Global Offers page provides one free non-premium domain, one year of
hosting, and SSL for one year through `spaceapps.earth` and Porkbun, GoDaddy
Registry's registration partner. Redemption requires contact information, a
valid email address, an emailed launch code, and completion of a free Porkbun
registration. This offer is optional; it is not required for submission and
should not be claimed until the final public name and renewal plan are accepted.

For a newly created project site, NASA recommends submitting a FortiGuard Web
Filter Classification request (for example, `Web-based Applications`) with
company name `N/A`. It is optional but can reduce the risk that judges cannot
open a new domain.

## Release checks

- Rebuild `dist/` from the tagged source.
- Confirm that no `.env`, key, credential, or raw protected granule is present.
- Test the root page and every linked data artifact while signed out.
- Test English, Persian, AOI analysis, and Judge Mode on mobile.
- Add the verified URL to the Project tab and video description.
- Request FortiGuard classification for a new custom domain, then retest from a
  signed-out browser and a second network.
- Keep the local `dist/` server as the presentation fallback.
