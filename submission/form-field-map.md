# Project Submission field map

This file maps the prepared material to the official 2026 Space Apps Project
tab inspected on 15 November 2026 while signed in to team QORVEX. The live
form remains authoritative if it changes.

| Live Project-tab item | Prepared content | Final check |
|---|---|---|
| Project Name | `Fyrora` | Replace the default `Project QORVEX`; use this spelling everywhere. |
| Summary * | Paste-ready core answer below | Live counter is 1,500 characters; NASA suggests 50–200 words. |
| Project Demonstration * | `submission/demo/fyrora-space-apps-demo-final.pdf`; deployment path `/demo/fyrora-space-apps-demo.pdf` | Seven English slides. The deployed URL must require no login, password, permission, or registration. |
| Project * | Public judge-facing web application — pending | Use the verified deployment URL, not the private repository. Test signed out and on mobile. |
| Project Details * | `submission/project-page.en.md`, edited into one coherent English narrative | Explain function, benefit, impact, tools, creativity, process, limitations, and evidence. |
| Use of Super Intelligence (SI) * | Use `submission/si-disclosure.en.md` and select every applicable option | This is required. Code/data assistance must also be acknowledged in descriptive text and metadata. |
| NASA Data * | NASA FIRMS; Aqua MODIS active-fire data; S-NPP VIIRS active-fire data | Add each as a separate public `Link Text` + `Link URL` row. At least one NASA resource is mandatory. |
| Space Agency Partner & Other Data | Copernicus EFFIS plus all external code, text, images, libraries, tools, and references used | Every external resource must be listed even if open source or free. |
| Team members | Official team page | Must match `CONTRIBUTORS.md` for work included in Fyrora. |
| License | MIT | `LICENSE` must be present in the public source. |
| Agree to Terms and Conditions * | Final verification only | Check only after the final public artifacts have been reviewed. |
| Confirm All Work is Original * | Final verification only | Requires complete attribution of every external resource. |
| Submit for Judging | Final action in Project tab | Do not click until every required field and public link is verified. |

## Live SI options

The required multi-select currently contains:

- Ideation or Brainstorming
- Research or Information Gathering
- Data Analysis and Interpretation
- Building SI/ML Into the Project
- Coding, Debugging, or Troubleshooting
- Writing, Editing, or Translation
- Visual Design or Image Creation
- Presentation, Video, or Audio
- Other Project-Related SI Use
- None / Did not use SI or SI tools

For the repository in its current state, `None` would be inaccurate. The final
selection must reflect every use that remains in the submitted artifacts.

## Paste-ready core answer

Fyrora turns two satellite records that cannot be compared directly into a
coverage-aware historical fire calendar. It matches Aqua MODIS and S-NPP VIIRS
passes in time, places both sensors on the same 10 km equal-area grid, and maps
VIIRS context to a MODIS-equivalent hotspot count. Users can explore region,
year, and day/night views, or run a bounded Western Iberia AOI analysis and
download its daily series. Unsupported matched-detection days remain unknown
rather than being reported as zero. The prototype is for historical analysis,
not emergency warning.

## Visibility and timing notes

- The live form says that `Save Progress` makes changes visible to anyone who
  visits the Project page, while the official guide says saved work remains
  visible only to the team until submission. Treat saving as potentially public.
- The project and demo links must be public for Global Award eligibility.
- Submission closes at 23:59 on 15 November 2026 in the Van event time zone.
- The form may be edited and resubmitted before the deadline; judges receive the
  final saved submission.
