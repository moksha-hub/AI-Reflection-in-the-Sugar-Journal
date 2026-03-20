# Journal Integration Notes

The prototype is intentionally shaped around the Sugar Journal integration surface rather than a generic chatbot API.

## Expected Journal-side flow

1. Sugar Journal observes a create or revisit/save event.
2. Journal code collects raw datastore metadata.
3. The metadata is sent to `POST /reflect-from-journal`.
4. `JournalMetadataAdapter` normalizes the metadata into a stable request.
5. `ReflectionEngine` returns one bounded reflection question.
6. Journal detail view renders that question in a lightweight panel.

## Metadata assumptions

The adapter currently handles:

- `bundle_id`
- `activity`
- `title`
- `buddies`
- locale passed directly or derived from environment

The service deliberately does not require the Journal to send private content from the child's work.

## Triggering notes

- `model.created` is the primary clean trigger
- `model.updated` requires filtering because metadata-only edits can also fire it
- `update_mtime=False` matters for suppressing spurious reflection runs

This keeps the prototype aligned with the current `jarabe/journal` signal model.
