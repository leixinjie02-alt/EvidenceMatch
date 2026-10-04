# Video demo script (about 5 minutes)

Every number below comes from the `run_v23_*` files. Read the "SAY" lines aloud; do the "DO" lines on screen.

## Before recording

1. In a terminal, in the project folder: `pip install -r requirements.txt`, then `python app.py`.
2. Open `http://127.0.0.1:8000` in Chrome. Zoom the page to 125%.
3. Have your résumé PDF and your OpenRouter key ready. Paste the key only into the password box; it shows as dots.
4. Open the GitHub repository page in a second tab.
5. The instructor requires **your face and your screen in the same video**, 5 minutes give or take 3 (anything past 8 minutes is not watched). The simplest way: start a Zoom or Teams meeting alone, turn the camera on, share your screen, and press Record. Check the recording shows both.
6. Record one part at a time. If you make a mistake, redo only that part.

## Part 1 — The problem (0:00–0:40)

DO: Show the app's first screen.

SAY: "Hi, I'm Lei Xinjie. This is EvidenceMatch, my PE6201 project. When I ask a chat assistant to tailor my résumé to a job posting, it overclaims. In my first test, it turned a small evaluation exercise into 'achieving significant improvements in AI system performance'. I can't defend that sentence in an interview. EvidenceMatch checks each job requirement against my real résumé, and every sentence it writes must quote the résumé."

## Part 2 — Upload and confirm (0:40–1:20)

DO: Click "Choose File", pick your résumé PDF. Scroll through the evidence list. Tick the confirm box.

SAY: "I upload my résumé. The backend removes any line with a phone number or email, then splits the résumé into one evidence unit per bullet. Mine has 27. Nothing goes to the model until I confirm this list. The server keeps nothing between requests."

## Part 3 — One live run (1:20–2:30)

DO: Leave the job on "JD19 · SimplifyNext · AI Engineer (Graduate)". Paste the key. Click "Match this job". Wait for the result. Scroll slowly down the requirements table.

SAY: "I pick a real graduate AI engineer posting and run one GPT-4o call. It costs about two cents. Each requirement is copied word for word from the posting and labelled Strong, Partial or Missing. Next to each label is the exact quote from my résumé and the gap. A Python validator has already checked that every quote really exists in my résumé and that no number was invented. If one check fails, the whole output is blocked."

## Part 4 — Human review (2:30–3:20)

DO: Scroll to the draft bullets. For each one, read the quote, then click a verdict. Click "Save my review". Show the metrics panel.

SAY: "These are the draft bullets. The validator proves a quote exists. It cannot prove the quote supports the sentence. So I review every bullet myself, and nothing is adopted automatically. When I save, the app computes my Unsupported Claim Rate. One run is an anecdote, and the app says so."

## Part 5 — The evaluation, honestly (3:20–4:30)

DO: Click "Recorded evaluation" at the top right. Point at each row as you mention it.

SAY: "Here is the real evaluation. Before running anything, a seeded script fixed ten held-out postings. On those, the model wrote fifteen bullets and I judged all fifteen supported. But fifteen is small: the 95 percent upper bound is 20 percent, so my 5 percent target is not demonstrated. And a later re-read questioned one bullet I had passed. Requirement labels agreed with mine on 45 of 50, against 40 percent for a keyword rule. That is an upper bound, because I could see the model's label while judging. Now the weaknesses. The validator blocked four of ten runs, and none had a fake quote. Two were blocked only because the quote was short, like 'SQL'. The model also declined to write bullets for five of ten postings. And my automatic overclaim flags never fired. So the system is safe but too strict, and the human reviewer is the only real check on meaning."

## Part 6 — Trade-offs and close (4:30–5:00)

DO: Switch to the GitHub tab and show the README.

SAY: "I chose one prompted model call, not retrieval or an agent, because my résumé fits in one prompt. I rent the model and own the validation, which is what makes the output trustworthy. The limits are clear: one résumé, one model, one run per posting, and one reviewer, me. Next I would relax the short-quote rule, test on new postings, and get a second reviewer. The code, the tests and every recorded run are in the repository. Thank you."

## If something goes wrong while recording

- "Enter your OpenRouter API key": the key box is empty. Paste the key again.
- The call fails with HTTP 401 or 402: the key is wrong or has no credit. Do not show the key on screen while fixing it.
- No key at hand: click "No key? Run the offline demo". Say clearly on camera that this is a canned response, not model output.
- The result says "Blocked by the validator": keep it in the video and say that this is the fail-closed behaviour described in Part 5.
