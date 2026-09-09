---
name: seo-content-architect
description: Plan an SEO-first website content architecture before UI design or frontend implementation. Use when defining site identity, topics, search intents, SERP-backed page types, sitemap, Markdown content sources, internal links, and page metadata for a new or reworked website. Not for isolated copy edits or technical SEO audits.
---

# SEO Content Architect

Define what the website is, what it should cover, and how its pages relate before designing or building the interface.

## Work content first

- Complete the content architecture before UI design or frontend implementation. If the request also includes design or development, finish and expose the architecture artifacts first, then use them as the design input.
- Start from the user's business, product, audience, market, language, and conversion goals. Inspect an existing site's pages and content when available.
- Separate confirmed facts, research findings, and assumptions. Ask only when a missing choice would materially change the site's identity or scope; otherwise proceed with a clearly marked assumption.
- Keep the output proportional to the site. Prefer a small, coherent architecture over a large speculative sitemap.

Use this order:

`Business -> Site Identity -> Search Research -> SERP -> Topic Cluster -> Sitemap -> Markdown Content -> Internal Links -> SEO Metadata -> Design`

## 1. Define the site identity

Create `site-identity.md` before planning pages. State:

- who the site or organization is;
- what it offers;
- whom it serves;
- which problems it solves;
- its primary conversion or business outcomes;
- the core topics it can credibly own;
- topics it should not cover;
- its useful differentiation and evidence, without inventing claims.

Use the topic exclusions to prevent adjacent high-volume queries from expanding the site beyond its purpose.

## 2. Research search intent and the live SERP

Before defining an important page, search the current web results for its likely primary query and meaningful variants. Important pages include the homepage, core product, service, or tool pages, cluster hubs, and pages expected to drive material acquisition or conversion.

For each important intent, record:

- **Search Intent:** the job the searcher is trying to complete;
- **Content Type:** product page, tool, tutorial, comparison, documentation, category, landing page, or another type actually represented in the SERP;
- **Content Format:** guide, list, calculator, template, reference, interactive workflow, and so on;
- **Content Angle:** the dominant promise or framing;
- **Competing Pages:** the main relevant results and their URLs;
- **SERP Gaps:** what existing results omit, obscure, or handle poorly;
- **Information Gain:** specific data, expertise, tool capability, workflow, examples, or perspective this site can uniquely add.

Record the research date, locale, and language when they affect the results. Treat rankings and SERP features as time-sensitive observations, not permanent facts. Cite the pages used as evidence.

Let the observed intent and SERP determine the page type. Do not force every query into an article. If live search is unavailable or the user disallows it, do not fabricate SERP findings; mark the page as unverified and provide the queries that still need research.

## 3. Build topics and intent clusters

- Derive a limited set of core topics from the site identity, then group supporting topics beneath them.
- Model one primary page for one search intent. Map close keyword variants to that page instead of generating one page per keyword.
- Before adding a page, compare it with existing and planned pages for audience, intent, promised outcome, likely SERP overlap, and content scope. Merge, retarget, or defer pages that would compete with one another.
- Prioritize business relevance, conversion potential, product fit, credibility, and achievable information gain over raw search volume.
- Do not create an important page unless it has a clear information gain. If the site cannot add something useful, exclude or defer the page.
- Use programmatic SEO only when every generated page is grounded in real data, a useful tool capability, or genuinely distinct content. Query permutations and AI-filled templates are not sufficient differentiation.

## 4. Create the sitemap

Create `sitemap.md` as the canonical page inventory. Keep the hierarchy shallow enough to understand and specific enough to guide implementation.

For every page include:

| Field | Meaning |
| --- | --- |
| Path | Proposed canonical URL path. |
| Core Topic | The site-level subject this page supports. |
| Topic Cluster | The narrower group of pages sharing a search journey. |
| Goal | What this page must help the visitor or business accomplish. |
| Search Intent | The single primary intent owned by the page. |
| Primary Query | The representative query, not a reason to create keyword variants. |
| Page Type | Type supported by SERP evidence and user need. |
| CTA | The next meaningful action. |
| Parent | The structural parent page. |
| Related Pages | Semantically related pages outside the strict parent-child path. |
| Information Gain | Why this page deserves to exist. |
| Status | `researched`, `unverified`, `brief`, `draft`, or `ready`. |

Maintain one canonical owner for each primary intent. Identify conflicts explicitly rather than hiding duplicates under different URLs.

## 5. Make Markdown the page source

Create a `content/` directory. Each SEO page has one `.md` source file whose path or filename maps clearly to the sitemap entry. Do not put multiple independently indexable intents into one source file.

Start each page with equivalent metadata:

```yaml
---
title: ""
path: ""
core_topic: ""
topic_cluster: ""
goal: ""
search_intent: ""
primary_query: ""
page_type: ""
cta: ""
parent: ""
related_pages: []
information_gain: ""
status: brief
---
```

After the metadata, write the actual page content or a content brief at the depth authorized by the user. Mark briefs as briefs; do not present outlines as finished content. Include only sections needed to satisfy the intent and deliver the claimed information gain.

Do not impose a minimum word count. Remove repetition, generic introductions, and AI filler rather than expanding copy to reach an arbitrary length.

## 6. Design internal links

Create `internal-links.md` with a concise link map containing source page, destination page, relationship, reader reason, and suggested anchor concept.

- Use links to express both hierarchy and semantic relationships.
- Link hubs to children and children back to their relevant hub.
- Add cross-cluster links only when they help the reader continue a related task.
- Ensure every indexable page has a discoverable path and at least one intentional internal inbound link; flag orphan pages.
- Prefer descriptive, natural anchors. Do not force exact-match anchors or add links solely for keyword repetition.

## 7. Add metadata after the content structure

Once intent, page purpose, and content are stable, add page titles, meta descriptions, canonical paths, and sharing metadata where useful. Keep them aligned with the actual page promise and avoid inventing claims that the content does not support.

Do not use metadata work as a substitute for resolving duplicate intent, weak content, or an unclear site identity.

## Required deliverables

Produce at least:

```text
site-identity.md
sitemap.md
internal-links.md
content/
  index.md
  ...one Markdown source per SEO page
```

Also preserve the current SERP evidence for important pages in `serp-research.md` or in clearly linked research sections within the page sources. Keep this evidence concise and actionable.

End with unresolved decisions and explicitly unverified SERPs, if any. The architecture is ready for design only when the site's identity, page ownership, hierarchy, content source, and important internal relationships are clear.
