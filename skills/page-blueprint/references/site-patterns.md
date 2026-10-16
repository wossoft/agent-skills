# Website page patterns

Public, search-facing pages: `landing`, `article`, `hub`, and `comparison`. They use the same `Pattern` + `Changes` mechanism as [patterns.md](patterns.md); read that file first for the mechanism and the `Changes` operations.

The difference from admin patterns: **copy lives in the content source, not in the blueprint.** The blueprint decides which content goes into which block and how blocks are arranged; it does not repeat headlines or paragraphs.

## Content source

```yaml
content: content/pricing.md        # Markdown source, e.g. produced by seo-content-architect
```

- `from: "#标题"` takes the section under that heading (including its subsections) from the content file. `from: top` is the text before the first `##` heading. `from: h1` is the page title.
- Blocks without `from` are pure UI (navigation, CTA buttons, forms) and may carry short labels directly.
- When a block needs content the file does not have, mark it `# assumed` and list it under `Open questions`. Do not write the missing copy into the blueprint.
- When the content file carries SEO front matter (`page_type`, `cta`, `related_pages`, `parent`), use it: `cta` drives the primary CTA, `related_pages` drives related links, `parent` drives the breadcrumb.

## page_type → pattern

| SEO `page_type` | Pattern |
| --- | --- |
| homepage, product, service, landing, tool landing | `landing` |
| tutorial, guide, blog post, documentation, glossary entry | `article` |
| category, topic hub, cluster pillar | `hub` |
| comparison, alternatives, "X vs Y" | `comparison` |
| interactive tool, calculator, configurator | none — full `Layout` |

## Rules every website pattern follows

These are requirements for implementation, so search engines and AI search can read the page:

- Exactly one `h1`, normally the content title. Heading levels follow the content's heading structure; do not pick heading levels for visual size.
- Main content is in the server-rendered HTML. Content inside `Tabs`, `Accordion`, or `Collapsible` is present in the HTML even when visually collapsed.
- Internal links are real anchors with `href`, not click handlers. Breadcrumbs follow `parent` and emit `BreadcrumbList` structured data when the SEO plan calls for it.
- Images that carry meaning have descriptive alt text; decorative images have empty alt text.
- The site header and footer come from `_layout.md`; patterns describe only the page body.

---

## landing

Homepage, product, service, or campaign page whose job is one conversion.

```yaml
content: content/index.md
hero:
  title: from(h1)
  subtitle: from(top)
  primary: 免费试用 -> navigate(/signup)        # defaults to the content's `cta`
  secondary: 预约演示 -> navigate(/demo)         # optional
  media: product-screenshot                     # screenshot | illustration | video | none
blocks:                                         # in page order
  - features: { from: "#核心功能", layout: grid }       # grid | alternating
  - steps: { from: "#如何开始" }
  - proof: { from: "#客户案例", kind: logos }          # logos | testimonials | stats | case-studies
  - pricing: { from: "#价格" }
  - faq: { from: "#常见问题" }
  - cta: { title: 准备好开始了吗？, action: 免费试用 -> navigate(/signup) }
```

Block types and their default expansion:

| Block | Expands to |
| --- | --- |
| `features` | `Section` + `Grid` of `Card` (one per `###` subsection; 3 columns, 2 on md, 1 on sm), or alternating text/media rows |
| `steps` | Numbered `Stack` of steps, one per list item or `###` subsection |
| `proof` | Logo row, `Carousel` of testimonial `Card`s, stats `Grid`, or case-study cards linking to their pages |
| `pricing` | `Grid` of plan `Card`s, recommended plan highlighted with a `Badge`; a comparison `Table` below when the content has one |
| `faq` | `Accordion`, one item per `###` question; emit `FAQPage` structured data only if the SEO plan calls for it |
| `cta` | Full-width `Section` with heading and one primary `Button` |
| `content` | Plain prose block rendering the section as Markdown |
| `related` | `Grid` of link `Card`s from `related_pages` |

Ids: `#hero`, then the block name (`#features`, `#faq`); repeated types get a suffix (`#content-2`). The primary CTA appears in the hero and in the final `cta` block; keep their wording identical.

## article

Tutorial, guide, blog post, or documentation page whose job is to be read.

```yaml
content: content/guides/order-sync.md
meta: [author, updatedAt, readingTime]          # shown under the title
toc: auto                                       # auto (from h2/h3) | none
cta: { position: end, action: 免费试用 -> navigate(/signup) }   # end | inline-after:"#某节" | none
author_box: true
related: auto                                   # auto from related_pages | none | explicit list
```

Expands to:

```text
Breadcrumb#breadcrumb
Stack#header        h1, meta line, optional summary from(top)
Split#body          article prose (side: right, size: sm aside on lg)
  Stack#article     Markdown body; code blocks, tables, callouts rendered from content
  Stack#toc         sticky TOC on lg; collapsed "目录" Collapsible above the article on md and below
Section#cta         per `cta.position`
Card#author         when author_box
Grid#related        link cards, 3 columns, 1 on sm
```

Defaults: the TOC highlights the current section; headings have anchor links; the readable column width is limited regardless of screen size; `updatedAt` is shown when it differs from the publish date.

## hub

Topic hub or category page that organizes a cluster and links to its children.

```yaml
content: content/guides/index.md
intro: from(top)
featured: [/guides/getting-started]             # optional; highlighted children
groups:                                         # explicit groups, or `auto` from children's topic_cluster
  - 入门: [/guides/getting-started, /guides/first-order]
  - 进阶: [/guides/order-sync, /guides/webhooks]
card: [title, description, page_type]           # what each child card shows
filters: none                                   # none | tags | search — only when there are many children
blocks:                                         # optional landing blocks after the groups
  - faq: { from: "#常见问题" }
  - cta: { title: 需要帮助？, action: 联系我们 -> navigate(/contact) }
```

Expands to `Breadcrumb#breadcrumb`, `Section#intro` (h1 + intro), `Grid#featured` (larger cards), one `Section#group-<n>` per group with a `Grid` of link `Card`s, then any landing `blocks`. Every child of the hub must appear in a group, so no child is orphaned; children listed in the SEO plan but missing here are reported in the review summary.

## comparison

"X vs Y" or alternatives page whose job is to help a reader decide.

```yaml
content: content/compare/us-vs-competitor.md
items: [我们的产品, 竞品 A, 竞品 B]               # column order; first is highlighted
verdict: from("#结论")                          # shown right after the h1: answer first
table:
  from: "#功能对比"                              # Markdown table in the content
  sticky: header                                # header row and first column stay visible
  highlight: 我们的产品
details: from("#详细对比")                       # one subsection per item or dimension
blocks:
  - faq: { from: "#常见问题" }
  - cta: { title: 开始免费试用, action: 免费试用 -> navigate(/signup) }
```

Expands to `Stack#header` (h1), `Card#verdict`, `Table#comparison`, `Section#details`, then `blocks`. On sm the table becomes one `Card` per item with the same rows, unless it has three or fewer columns. Comparison claims come from the content source with their citations; the blueprint never adds or rewords them.
