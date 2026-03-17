# PubSave Demo -- Voiceover Script

**Total runtime target: ~90 seconds**

Use arrow keys (or spacebar) to advance slides while screen recording.

---

## Slide 1 -- Title (0:00 -- 0:10)

> "PubSave. A personal tool for saving PubMed papers from your terminal.
> Built with FastAPI, PostgreSQL, and Docker Compose.
> 11 API endpoints, 92 tests, and 8 CLI commands."

## Slide 2 -- Problem (0:10 -- 0:25)

> "If you work with research papers, you know the pain.
> Papers scattered across browser tabs, PMIDs on sticky notes,
> no way to search or organize what you've read.
> PubSave fixes that with a CLI and a clean, searchable API."

## Slide 3 -- Architecture (0:25 -- 0:40)

> "The architecture is simple. The CLI talks to a FastAPI backend,
> which stores everything in PostgreSQL -- papers, tags, relationships.
> It also connects to PubMed's E-utilities API
> so you can fetch full paper metadata with just a PMID.
> Docker compose up, pip install, and you're ready."

## Slide 4 -- CLI Commands (0:40 -- 0:55)

> "Eight commands cover everything you need.
> Fetch papers from PubMed. List and search your collection.
> Tag and untag papers. Delete with confirmation.
> Short IDs work everywhere -- type six characters instead of a full UUID."

## Slide 5 -- Live Demo: Fetch (0:55 -- 1:10)

> "Here's the workflow. Type pubsave fetch with a PubMed ID.
> PubSave hits the PubMed API, pulls the title, all 32 authors,
> the abstract, journal name, DOI, publication date --
> and saves it all to your database. One command."

## Slide 6 -- Live Demo: Tag & Search (1:10 -- 1:25)

> "Once saved, tag papers however you want.
> Then search across your collection -- by tag, by keyword,
> or by author name.
> Two papers tagged genetics? Found. That leprosy paper? One keyword."

## Slide 7 -- Features (1:25 -- 1:35)

> "Under the hood: Docker Compose for one-command setup,
> short ID resolution so you never type a full UUID,
> compact mode for the CLI, ANSI sanitization,
> and a full test suite -- 92 tests with real Postgres."

## Slide 8 -- CTA (1:35 -- 1:40)

> "PubSave. Save papers. Tag them. Search them.
> Pubsave fetch, and you're running."

---

## Recording Tips

1. **Screen recorder**: QuickTime (File > New Screen Recording) or OBS
2. **Resolution**: Record at 1920x1080 for best quality
3. **Browser**: Open `demo/index.html` in Chrome, press F11 for fullscreen
4. **Audio**: Use your Mac's built-in mic, or a headset for better quality
5. **Pacing**: Pause ~1 second between slides for the transition animation
6. **Post-production**: Trim the start/end in iMovie or QuickTime
