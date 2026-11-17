"""Goodbye FuffaGuru: check a social-media trading guru before you trust them with money.

The package is a small toolbox for one job: turning what a trader *shows* and
*says* into something you can measure on real prices, and then asking whether
the result beats chance.

Modules
-------
capture     follow a trader: download the public history and record live streams
transcribe  speech to text with timestamps (faster-whisper, optional)
frames      frames and contact sheets from videos (ffmpeg)
trades      trade CSV schema and verification on OHLC bars
prereg      freeze a recipe (JSON/YAML) with a sha256 fingerprint before testing
nulltests   random direction at the same instants, fake levels, bootstrap, costs in R
metrics     win rate by trades vs by days, expectancy over time, drawdown
recipes     a generic level-based recipe used by the examples and the fake-level test
synthetic   synthetic random-walk markets with no edge by construction
report      the "Reality Check" markdown report and its verdict
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
