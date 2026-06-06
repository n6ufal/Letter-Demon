# Architecture

## How It Works

### Word Selection Pipeline

From input to output, the engine follows a fixed sequence of steps.

#### 1. Trap Endings Index

When you load `trap_endings.txt`, the engine parses it line by line, skipping blanks and comments, trimming whitespace, lowercasing everything, then removes duplicates while preserving order.

Each ending gets a score based on its position:

```python
ending_scores = {
    ending: len(trap_endings) - index
    for index, ending in enumerate(trap_endings)
}
```

First entry gets the highest score. Last gets 1. Anything not in the list gets 0.

So a file with three endings gives you:

```
ocy  ->  score 3  (hardest to follow)
loh  ->  score 2
sz   ->  score 1
```

#### 2. Prefix Search

You type a prefix like "ca". The engine runs a bisect-based binary search on the sorted word list to find every word that starts with those letters. Binary search is O(log n), which on a 100k+ word dictionary is roughly 51x faster than scanning the list from the top.

Matching is case-insensitive, so "Ca", "CA", and "ca" all hit the same results.

#### 3. Scoring

For each candidate word, the engine checks what suffix it ends with and looks that up against `ending_scores`. It starts with the longest possible suffix and works down until it finds a match:

```
"happiness"   -> ends with "ness" -> score 3
"development" -> ends with "ment" -> score 2
"running"     -> ends with "ing"  -> score 1
"cat"         -> no match         -> score 0
```

The word with the highest trap score wins. If multiple words tie, the tiebreaker depends on your strategy:

- **Trap Words** picks the highest-scoring word, tiebroken by longest
- **Long Words** ignores trap scores entirely, just finds the longest match
- **Short Words** ignores trap scores entirely, just finds the shortest match

#### 4. Exception Filter

Before anything gets typed, the engine checks the exceptions set, a plain Python set of lowercase words. Set lookups are O(1) so this adds no noticeable overhead. Words on the list get skipped.

#### 5. Fallback

If no word is found for the prefix under your main strategy, the engine falls back to your backup strategy. If that's also empty, it returns None and shows an error state.

#### 6. Cache

When you load a dictionary, the engine precomputes scores for every word upfront and stores them in `_trap_score_cache`. That's where the 5-30 second wait on first load comes from. After that, lookups are instant.

The cache clears automatically when you load a new dictionary or change your trap endings.

### Typing Simulation

Keystroke delay is sampled from a log-normal distribution:

```
delay ~ LogNormal(μ, σ)
```

Log-normal means the distribution is right-skewed. Most keystrokes cluster around your base speed, but occasionally one takes longer, which is how people actually type. A uniform random distribution would feel robotic by comparison.

`μ` is derived from your configured base speed. `σ` scales with jitter intensity. Delays are clamped to [30ms, 500ms] to keep inputs physically plausible. Every character gets its own independently sampled delay with no pattern between keystrokes.

**Parameters:**
- **Base speed** (default: 170ms) is the median keystroke delay
- **Jitter intensity** (default: 75%) controls variance
- **Pre-delay** (default: 500ms) is the wait before the first keystroke
- **Post-delay** (default: 500ms) is the wait after the last keystroke and Enter
