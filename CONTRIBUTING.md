# Contributing

Thanks for helping people check before they pay.

**Welcome:** anonymous case studies (use the "New anonymous case" issue template), better null tests,
fixes for platform changes (TikTok, YouTube, Instagram move fast), translations, documentation.

**Ground rules**
- **Anonymity.** No names, handles, channel names, exact dates, recognisable quotes or images of
  real traders anywhere: code, docs, tests, issues, commit messages.
- **No captured content.** Never commit or attach videos, frames, transcripts or market data you
  are not allowed to share. `data/`, `secrets/` and media files are ignored by git for this reason.
- **No secrets.** Never commit cookies, tokens or `config/settings.json`.
- **Data, not accusations.** Write "the rules as taught, tested, give X", never judgements of people.
- **Statistics.** Preregister before testing, count your trials, include costs, keep the nulls.

**Development**
```
python scripts/bootstrap.py --core      # or: pip install -e ".[all]"
python -m pytest
```
Tests must not need network, ffmpeg or a real account: use synthetic data, fake pages and fake processes.
Keep functions small and documented; command builders pure, so they can be tested.

By contributing you agree that your contribution is released under the MIT licence.
