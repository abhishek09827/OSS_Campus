# LinkedIn Activity Coral Source

This directory contains a production-style Coral community source spec for LinkedIn Activity.

## What it exposes

- `linkedin_activity.posts` for post-level engagement analysis
- `linkedin_activity.profile` for skills, headline, and connections count
- `linkedin_activity.reactions` for user reaction history

## Setup

1. Set `LINKEDIN_ACCESS_TOKEN` in your environment.
2. Register the source with Coral.
3. Validate the manifest with the Coral CLI if your version supports `coral source validate`.

## Example queries

```sql
SELECT headline, skills, connections_count
FROM linkedin_activity.profile
LIMIT 1;
```

```sql
SELECT id, like_count, comment_count, share_count
FROM linkedin_activity.posts
ORDER BY created_at DESC
LIMIT 5;
```

```sql
SELECT reaction_type, reacted_at
FROM linkedin_activity.reactions
ORDER BY reacted_at DESC
LIMIT 10;
```

