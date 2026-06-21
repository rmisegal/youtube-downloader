"""Movie-agent tools: YouTube search + segments-JSON → playlist builder.

These are the project's "hands" for the LLM movie-maker agent (.claude/skills):
``--search`` finds candidate YouTube videos (with durations) for the Video Content
Matcher, and ``--build-movie`` turns the matcher's segments JSON into a playlist the
mixer produces into one film.
"""
