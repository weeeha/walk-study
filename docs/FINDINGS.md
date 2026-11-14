# Findings and decisions

**TL;DR**

- Recorded motion capture is far better than generated walks for copying how a character moves, and three free libraries cover old, young and tactical walks.
- No library has an unstable armed person, and no take records a weapon. That group is made of nearby takes, and the weapons are drawn from the hand positions.
- Two Ubisoft takes cannot be shared, so they sit in an optional file that is not in this repository.

Written by Claude on 14 November 2026 from the record of the working session (13 November 2026) and this repository's history. The repository holds only the finished state in two pull requests, so the reasons below come from the session. Anything that could not be traced to either is under Unverified or left out.

## What was explored

**The question.** Can a person learn how different characters walk (an old person, a young one, a trained operator, an unstable armed person) by watching rendered examples and copying them, without recording themselves?

**What was built to answer it.** One HTML page that plays recorded walks on a drawn mannequin:

- 21 takes in five groups: everyday adult, elderly, young, tactical and armed, unstable and agitated.
- Each take is a window of about 14 seconds cut from the source recording, resampled to 30 frames a second, with the leg scaled to 0.88 m.
- Four fixed views plus free orbit, three playback speeds, frame stepping, foot marks, head and hand trails, a footfall timeline, and a side by side comparison of two takes.
- Notes for each character on what to copy.
- Two scripts that download the source recordings and convert them into `clips.json`.

## What was found

1. **Generated walks look generic.** The first version drew five characters from about 25 numbers each (steps per minute, step length, knee bend, lean, arm swing and so on). On first viewing they were judged too generic. They are built from averages, so they lack the small uneven things a performer adds, and those are what a person would copy.

2. **Three free libraries cover three of the four characters.**

   | Library | What it gave | Takes used here |
   |---|---|---|
   | 100STYLE | One performer walking in 100 acted styles | 11 |
   | CMU Graphics Lab Motion Capture Database | Many people, wide range of named characters | 10 |
   | Ubisoft LAFAN1 | The only free armed movement found: its "Aiming" set | 2, private only |

3. **None of these sources has a take of an unstable person with a gun.** The fifth group is seven nearby takes shown as they are: two drunk walks, an angry walk, a start and stop walk, a walk while being followed, and two scared walks.

4. **No take records a weapon.** The Ubisoft set recorded only the body, and its files do not say what the actors held. The hands still show it: one actor's hands stay 32 to 51 cm apart, which fits a long gun, and the other's stay about 13 cm apart at shoulder height, which fits a handgun. The 100STYLE performer in the SWAT style mimes a rifle.

5. **Two gripping hands are enough to place a rifle.** Two points fix a line, so the rifle is drawn along the line from one palm to the other, and only its roll is assumed (magazine down). A handgun gives one point because the hands are together, so its direction comes from a second point on the body, the midpoint of the shoulders.

6. **A number did not prove a weapon is being held.** A test of how often the hand spacing fits a rifle scored 1.0 on a neutral walk with swinging arms, so it does not separate armed takes from unarmed ones. The evidence for the props is what the takes look like.

7. **The recordings store where each joint is, not how each bone is twisted.** The facing of the ribcage, pelvis and head is rebuilt from pairs of joints. That is why one mannequin works on takes from three recording systems without converting any clip again.

8. **The Ubisoft files store the top of the head and the hand tips as zero-length points.** The head had no up direction and fell on its side, and the hands continued the forearm with no bend at the wrist. The converter now continues the neck's axis for the head and the hand's own axis for the tip (about 8 cm). After the fix, all 23 takes passed a data test: every head has a top at least 9 cm above the head joint, and the face is within 1 degree of square to it.

9. **The face cannot be assumed to point where the body walks.** On stooped takes that assumption put the face marker on the crown of the skull. The face is now set square to the head's own up axis, so a stooped walker looks at the floor.

10. **Several 100STYLE takes really carry the head pitched well forward** (Drunk, Angry, Start and stop, Being followed). The face looking down in those is the recording.

11. **The 100STYLE performer walks in a wide circle**, so those takes have a slight constant turn.

12. **The step numbers are approximate.** Footfalls are detected from ankle speed and height. The CMU "Old man walk" reads 146 steps a minute with 16 cm steps, against 69 steps a minute for the 100STYLE "Old" take, because the detection splits a shuffle into extra steps. Both values are in `clips.json`.

13. **The sharing terms differ by source.** 100STYLE is CC BY 4.0. LAFAN1 is CC BY-NC-ND 4.0, which does not allow sharing converted copies. CMU's own site, read on 14 November 2026, allows copying, changing and redistributing its data, including in products that are sold, with one limit: "you may not resell this data directly, even in converted form".

14. **The Ubisoft split holds.** The public `clips.json` contains no Ubisoft take, no Ubisoft file exists anywhere in the git history, and a logged-out request for `clips.ubisoft.json` on GitHub returned 404.

15. **A hidden preview pane draws no 3D.** During testing the stage came back blank with no error because the preview pane was hidden and the page was running in the background. The renders used for checking, and the screenshot in the README, come from headless Chrome instead.

16. **A credential scan flagged `clips.json`, and it was a false alarm.** The clip data is 16-bit numbers stored as base64. Small values leave every second byte at zero, which encodes to capital letters, and one run of them starts with the same four letters as an AWS key ID. The scanning tool was fixed, and this repository now reads clean.

## Decisions

| Decision | Why |
|---|---|
| Render examples to watch, with no capture step | The goal was to watch a movement and copy it, not to record oneself. |
| Use recorded takes in place of the generated walks | The generated walks were too generic to copy from. |
| Take most styles from 100STYLE | The same performer does every style, so the differences between takes are the style and not the body. |
| Add CMU takes | It has the widest range of named characters and real variety between bodies. |
| Call the fifth group "unstable and agitated" and not "armed" | No source has a take of an unstable person with a gun. |
| Dark interface | It was asked for, and the restyle went through an independent review whose points were fixed. |
| Draw a box mannequin on the recorded joints, not a ready-made 3D character | A ready-made character would need each of the three recording systems fitted to its skeleton, with a real chance of twisted limbs, and box forms show rotation more clearly. |
| Draw weapon props, with a Props checkbox to hide them | The armed takes were hard to read without a weapon, and the checkbox keeps the bare hands visible. |
| Choose the weapon type from the hand spacing | The dataset does not say what was held. |
| No prop on Crouched, Careful walk and search, or Sneaking | The hands in those takes are not holding anything. |
| Keep the Ubisoft takes in an optional file that git ignores and the page loads only when it is present | Their licence does not allow sharing converted copies, and this keeps one viewer for both the public and the private set. |
| Download the Ubisoft set only with `--with-ubisoft` | A default rebuild then produces only data that can be shared. |
| Make the page a complete HTML document | The repository copy has to run on any static server, not only inside the page host it was first published on. |
| Start the repository with a commit that holds only `.gitignore` | The rule that keeps the Ubisoft file out existed before any data was added. |
| Keep the repository private until the pull request was merged and checked | Nothing that cannot be shared was public at any point. |
| MIT licence for the code, with `clips.json` left outside it | The owner chose MIT, and the clip data stays under the terms of its sources. |

## Tried and dropped

- **A capture pipeline.** The first answer proposed recording oneself with tools such as Sports2D or FreeMoCap and measuring the result. Dropped because the request was for examples to watch.
- **Generated walks.** Five characters built from numbers. Replaced by recorded takes after the first viewing.
- **A capsule figure.** The first figure for the recorded takes used round tubes. Replaced when a better schematic body was asked for, because tubes hide how the chest turns against the hips.
- **A ready-made 3D character.** Considered and never fetched, for the reason in the decisions table.
- **The Bandai Namco Research motion dataset.** Considered and never loaded. It is non-commercial, and its elderly and young style names were not confirmed in its files.
- **Blending one armed, unstable walk from nearby takes.** Suggested and not attempted. The group shows the nearby takes unblended.
- **A numeric test as proof that a rifle is held.** It passed on an unarmed walk (finding 6), so it was not used as evidence.

## Open questions

- Should there be a public live demo? None exists. The published page is private and includes the Ubisoft takes, so it cannot be made public as it is.
- Are the weapon readings right: a rifle for the first Ubisoft actor and a handgun for the second?
- Is the wording of the README and of this document right to share? Both were drafted by Claude.
- Should the step detection be improved for shuffling walks, or are approximate numbers enough?
- Should this project get a page on the portfolio site?

## Unverified

- **Safari.** The page was only checked in Chrome. To check: open it in Safari, play a take, switch views, turn on comparison.
- **Most takes were never watched.** The by-eye checks covered about six takes after loading, five after the mannequin, five after the head fix and the three armed takes with props. The rest passed data tests only. To check: play each of the 21 takes once.
- **Trails after the dark restyle.** They were checked before it. To check: turn Trails on in any take.
- **Stress cases.** 200% zoom and very long take names were not tried.
- **The step numbers.** Speed, cadence and step length were not compared with any reference measurement.
- **The weapon types.** They are a reading of the hands. The dataset's authors would know.
- **The 100STYLE and LAFAN1 licences** were read from their own pages during the session and not read again when this document was written. CMU's terms were read again on 14 November 2026.
