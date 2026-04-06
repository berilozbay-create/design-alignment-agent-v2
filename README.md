Design Alignment Agent v2
A significant evolution of the original hackathon submission. V2 introduces dual-style selection, a 6-card structured exploration system, voice/text preference feedback, and a signal-driven Round 2 that uses labeled visual references to generate refined proposals.
What changed from V1:
Dual style selection — users now pick two styles (primary and secondary) instead of one. The system generates a structured 6-card layout: pure primary, primary variation, primary-led blend, pure secondary, secondary variation, and secondary-led blend.
Progressive card loading — cards appear one by one as they generate rather than all at once. A and D (static references) appear at 5 and 30 seconds with artificial delays for a consistent feel.
Voice and text feedback — after seeing 6 cards, users describe what they liked and disliked in their own words or by voice. Any language is supported. Gemini extracts structured design signals from the comment.
Signal-driven Round 2 — Round 2 no longer generates mechanical material variations. Instead it uses the user's stated preferences to generate 3 refined proposals. All 6 Round 1 cards are sent to Gemini as labeled visual references (A-F stamped with Pillow) so it can identify and reproduce specific liked elements.
Reliable generation — sequential image generation with 25-second cooldowns prevents API rate limit errors. Polling architecture shows each card as it arrives.
Final hero image fixed — the final proposal image now correctly reflects the user's Round 2 selection.
