Product Requirements Document (PRD)
Coimbatore Mappillai - The Audio Architect Protocol
1. Executive Summary
Coimbatore Mappillai is a mobile-first, audio-immersion Tamil learning system designed to build "Operational Capacity" for living in Coimbatore. Unlike traditional language learning tools that focus on reading and writing, this system prioritizes listening comprehension and spoken connectivity through high-quality, dual-voice AI-generated podcasts. The goal is to maximize "Operational Capacity"—the ability to navigate daily life, handle transactions, and build social connections—rather than academic fluency.

2. Core Philosophy
2.1 The 800 Lemma Theory (Critical Mass)
Goal: Reach "Operational Capacity" by mastering the 800 high-frequency "glue" words (verbs, connectors, pronouns) that constitute 80% of spoken connectivity.
Why: This specific threshold is the tipping point where the user can effectively "survive" in Coimbatore, understand Tamil media, and continue learning through osmosis. It transforms the environment from "noise" into "input."
2.2 Dopamine-Driven Design
The "Zinger" Motivation: The curriculum is designed to provide immediate social rewards. Every lesson includes "Zingers"—phrases designed to surprise locals and delight in-laws.
The "Deep Cover" Persona: The user adopts a persona of a secret agent or undercover operator. This gamification provides an internal narrative that turns mundane study into a high-stakes mission, generating the dopamine needed to sustain effort.
2.3 ADHD-Friendly Architecture
Friction Reduction: The "Audio First" and "Mobile Bridge" workflows are designed to minimize the steps between "thought" and "action."
Momentum Management: The system balances "Hyperfocus" (deep dives into grammar/culture) with "Novelty" (rapid-fire drills, new scenarios) to prevent the "loss of interest" cycle typical of ADHD neurotypes.
Dual-Voice Dialogue: The constant switching between Host and Guest keeps the auditory cortex engaged, preventing "zone out."
2.4 Technical Pillars
Audio First: Language acquisition happens through extensive listening.
Tamil Script Only: All spoken Tamil is rendered in Tamil Script for perfect TTS pronunciation.
Feedback-Driven: The curriculum adapts based on user feedback.
3. System Architecture
3.1 The Protocol (The "Brain")
Located in the protocol/ directory, this defines the pedagogical logic and role-based workflows for content generation.

The Director: Defines the strategy, learning goals, and "Beat Sheets" for each lesson.
The Architect: Creative writer who converts Beat Sheets into engaging, dual-voice narrative scripts.
The Producer: Technical executor who ensures TTS compatibility, handles "Kongu" localization, and stitches audio segments.
3.2 The Curriculum (The Content)
Structure: 8 Weeks, 56 Days of content.
Source of Truth: 
curriculum/levels.json
 defines the vocabulary for each level.
Progress Tracking: 
progress/learner.json
 tracks word mastery via comfortable/struggled/mastered word lists across three tiers:
Tier 1 (Survival - 200 words): Essentials for navigation and transactions.
Tier 2 (Comfortable - 500 words): Social connectivity and family conversation.
Tier 3 (Embedded - 800+ words): Cultural fluency and media consumption.
3.3 The Factory (The Engine)
A Python-based pipeline for generating audio assets.

Input: Markdown scripts with role indicators (**Host:**, **Guest:**).
Process:
scripts/generate_dialogue.py
: Parses the script.
Engine: edge-tts (Microsoft Edge Neural Voices).
Voices:
Host: ta-IN-ValluvarNeural (Male, Explainer).
Guest: ta-IN-PallaviNeural (Female, Native Speaker).
Output: High-quality MP3 files (weekX_dayY.mp3).
3.4 The Feedback Loop (The Bridge)
A mechanism to capture user progress from mobile devices and sync it back to the central curriculum.

Capture: User talks to a "Mobile LLM" (e.g., Gemini on iOS) about their session.
Format: The LLM generates a structured JSON block containing event data (e.g., struggled_words).
Transport: iOS Shortcut ("Log Tamil") sends the JSON payload to a Webhook (Home Assistant).
Sync: 
scripts/sync_progress.py
 pulls data from the webhook/store and updates learner.json on the local machine.
4. Functional Requirements
4.1 Content Generation
Role-Based Scripts: The system must support generating scripts that strictly distinguish between Host and Guest roles.
Script Validation: The system should ideally validate that Tamil lines use Tamil script to prevent TTS errors.
Audio Synthesis: The generator must produce clear, well-paced audio with distinct voices for each role.
4.2 Progress Tracking
Granular Logging: Users must be able to log completion of specific lessons and identify specific words they struggled with.
Data Persistence: Progress data must be persisted in a machine-readable format (learner.json) that survives session resets.
Adaptive Feedback: The system should be able to query the "struggled words" list to inform the creation of review ("Remix") episodes.
4.3 Mobile Integration
Portable Context: The core protocol and curriculum files must be packable (
Tamil_Protocol_Context.zip
) for upload to mobile LLM contexts.
Frictionless Logging: The logging process must be "voice-first" or "one-tap" to encourage usage while walking/commuting.
5. Technical Specifications
Language: Python 3.x
Dependencies: edge-tts, requests (for webhook syncing).
Data Formats: JSON for structured data, Markdown for content/scripts.
Deployment: Local execution for generation; Mobile/Cloud for consumption and logging.