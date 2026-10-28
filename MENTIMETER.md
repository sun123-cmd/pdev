# Live classroom polls

The two poll slides in `index.html` and `lesson.html` use official Mentimeter results embeds. The manual vote counters have been removed. QR images are bundled locally and point to the participant pages, not to the results viewer.

| Poll | Participant link | Owner edit page |
| --- | --- | --- |
| Count the iterations | https://www.menti.com/alnayk3q9jtp | https://www.mentimeter.com/app/presentation/al4mi9g5ghh1greb736xydcbwmmruvop/edit |
| Resetting the total | https://www.menti.com/alnepyswfh35 | https://www.mentimeter.com/app/presentation/ale5g61gwz7d62mvwso38kvvnvbth9pu/edit |

Each poll has a separate presentation, so the results viewer opens on the correct question. Students scan the new QR code for poll 2. Both use the Artichoke theme, single-selection answers, and instant results. The presentations belong to the Mentimeter account that created them; public repository access does not grant edit permission. In Poll 1, an unused second-question draft is marked Skipped slide; keep it skipped.

Before class, verify participation is enabled and the first question remains active in both presentations. Preview both QR links and result frames. If an embed cannot load on the classroom network, use the Open results link below it. To rerun a session, manage previous responses from the owner's Mentimeter account.

To replace a poll, get its official code from Share → Participants → Embed slides → Copy code. Replace the matching iframe `src` and Open results link in both HTML files. Replace the matching participant link and regenerate its QR image as well. Do not embed the participant page as the results source.

Validation: both result frames and participant question/option pages were inspected in the browser; lesson navigation, answer reveal, and the loop trace were checked. No test responses were submitted, so real-time update after submission remains a classroom preflight check.

Official embed documentation: https://help.mentimeter.com/en/articles/410896-embed-your-menti-on-a-webpage
