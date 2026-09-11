# TTS Provider — Upgrade Path & Trade-offs

## v1 Provider: pyttsx3 (Current)

**Why pyttsx3 for v1:**
- Completely free — no API key or cloud account needed
- Works fully offline — no internet dependency
- Zero cost at any scale
- Simple integration — 2 lines to speak text

**Limitations:**
- Robotic voice quality — not natural sounding
- No emotion or tone control
- Limited voice options (depends on OS)
- Not suitable for production user-facing audio

---

## v2 Upgrade Options (Cloud Providers)

| Provider | Voice Quality | Cost | Latency | Notes |
|---|---|---|---|---|
| **Google Cloud TTS** | Very Good | $4/1M chars | Low | SSML support, 380+ voices |
| **AWS Polly** | Good | $4/1M chars | Very Low | Neural voices, streaming |
| **ElevenLabs** | Excellent | $5/month (starter) | Low | Most natural, emotion-aware |
| **Azure Cognitive** | Very Good | $4/1M chars | Low | 400+ voices, real-time |

## Recommended Upgrade: Google Cloud TTS

```python
# Future v2 implementation (out of scope for B1)
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()
# ... see Google Cloud docs for full implementation
```

## Migration Steps (when ready):
1. Add `GOOGLE_TTS_API_KEY` to `.env`
2. Install `google-cloud-texttospeech`
3. Replace `speak_text()` internals — keep same function signature
4. No changes needed in callers