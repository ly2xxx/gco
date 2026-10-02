<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@d8bc04e -->
# Intent: Public GitHub Pages introduction to the Chinese golf community

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
People who land on the GCO repository — prospective members, guests, and anyone curious about the club — currently find a developer-oriented README about a Streamlit dashboard and raw scoring data, with no plain-language entry point explaining what the Chinese golf community is. There is no public, shareable URL that can be sent to someone who is not a developer, so the club's identity is invisible outside the repo. The cost is that interested people bounce, and members have nothing simple to share.

## Outcome
A publicly reachable GitHub Pages site exists at https://ly2xxx.github.io/gco/ containing a short, self-contained introduction to the Chinese golf community and the GCO club. README.md links to that URL so a reader can get the human-facing overview before the technical detail. The page content most likely belongs alongside the existing published club material in `docs/`, which already holds the charter and PDF/visual assets.

## Done when
- Visiting https://ly2xxx.github.io/gco/ in a browser returns a rendered page (not a 404) without any login.
- The page contains a short introduction to the Chinese golf community, readable in a couple of minutes, with no dead links or missing images.
- The page renders usably on both a desktop and a phone-width viewport.
- README.md contains a visible link to https://ly2xxx.github.io/gco/.
- The page content is consistent with the club facts already stated in the repository (charter, tournaments, players) and does not contradict them.
- The existing tests still pass.

## Not in scope
- Any change to the Streamlit dashboard, its pages, or its data flow.
- Restyling, translating, or republishing the full charter / PDF documents.
- A multi-page website, navigation menu, blog, or CMS.
- A custom domain or any DNS change.
- Membership signup, contact forms, analytics, or tracking.
- Automating content updates from the app's data sources.
- Rewriting or restructuring the rest of README.md beyond adding the link.

## Open questions
- Language of the page: the idea does not say. Assumed English as the primary language, matching README.md, with Chinese club and player names kept as-is.
- Audience: "Chinese golf community" could mean the GCO club specifically or the broader community. Assumed the page introduces the GCO club as part of the wider Chinese golf community, drawing only on facts already in the repository.
- How much detail counts as "short": assumed a single landing page of roughly a few short sections (who we are, what we play, how the season works), not a full club history.
- Whether the link should also appear anywhere else (e.g. the dashboard): assumed README.md only, since that is all the idea asks for.
- No existing intent.md was supplied for this idea, so this document is a new intent rather than a revision; nothing was carried over from a prior version.
