# B8 Cross-Device Voice Flow Testing

## Tested
- Browser/device 1: Chrome (Desktop / Windows 11)
- Browser/device 2: Safari / Chrome (macOS / iOS)
- Browser/device 3: Chrome (Mobile / Android)

## Results
- TTS: Blocked (401 Auth Issue)
- Audio playback: Blocked (401 Auth Issue)
- Live STT: Blocked (401 Auth Issue)
- Turn-taking: Blocked (401 Auth Issue)

## Issues Found
- Candidate ID flow returns 401 Invalid/Missing API Token.
- This prevented/limited end-to-end interview testing.

## Conclusion
Cross-device testing was performed as far as the current environment allowed.
The authentication issue has been documented as a blocker.
