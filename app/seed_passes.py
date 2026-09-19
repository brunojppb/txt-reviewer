"""Seed data for the editing passes: the ordered list of lenses a run can use."""

GROUPS = (
    "Writing cleanup",
    "Clarity",
    "Cohesion and flow",
    "Sentences",
    "Shape",
)

PASSES: list[dict] = [
    # --- Writing cleanup ---
    {
        "slug": "sand-off-filler-words",
        "title": "Sand off filler words",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for filler words that add no meaning. Words like very, really, "
            "actually, basically, simply, just, quite, and rather count as "
            "instances when the sentence says the same thing without them. Read "
            "the sentence with the word removed. If nothing changes, flag it. Do "
            "not flag a word that carries real meaning: actually can mark a "
            "contrast with a stated belief, and just can mean only. Do not flag "
            "filler inside a direct quotation from a source. Report at most the "
            "15 most important instances. Quote the exact words from the text, "
            "verbatim and short. In the note, name the problem and say what it "
            "costs the reader. Send the words to cut as an edit on the finding, "
            "with an empty replacement. The target must be the exact words from "
            "the text."
        ),
    },
    {
        "slug": "cut-hedges-and-intensifiers",
        "title": "Cut hedges and intensifiers",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for hedges and intensifiers that blur a claim. Hedges include "
            "somewhat, perhaps, tends to, in some sense, and it seems. "
            "Intensifiers include extremely, deeply, utterly, and absolutely. An "
            "instance is a hedge or an intensifier that the claim does not need, "
            "or a stack of two or more in one sentence. Do not flag a hedge that "
            "states real uncertainty the writer can defend, such as a limit on "
            "evidence. Do not flag an intensifier that marks a true extreme. "
            "Report at most the 15 most important instances. Quote the exact "
            "words from the text, verbatim and short. In the note, name the "
            "problem and say what it costs the reader. Send the words to cut "
            "as an edit on the finding, with an empty replacement. The target "
            "must be the exact words from the text."
        ),
    },
    {
        "slug": "cut-redundant-pairs",
        "title": "Cut redundant word pairs",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for paired words that mean the same thing. Each and every, "
            "first and foremost, hopes and dreams, full and complete, and any "
            "and all are instances. The test: drop one half of the pair and check "
            "whether the meaning survives. If it does, flag the pair. Do not flag "
            "a pair whose halves differ, such as terms and conditions in a "
            "contract, or a fixed legal or technical name. Do not flag a pair the "
            "writer repeats for a stated rhythm in a deliberate list. Report at "
            "most the 15 most important instances. Quote the exact words from the "
            "text, verbatim and short. In the note, name the problem and say what "
            "it costs the reader. Send the words to cut as an edit on the "
            "finding, with an empty replacement. The target must be the exact "
            "words from the text."
        ),
    },
    {
        "slug": "cut-redundant-modifiers",
        "title": "Cut redundant modifiers",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for modifiers already contained in the word they modify. Past "
            "history, final outcome, future plans, advance warning, basic "
            "fundamentals, and completely finish are instances. The test: remove "
            "the modifier and check whether the meaning changes. If it does not, "
            "flag it. Do not flag a modifier that draws a real contrast, such as "
            "final draft where earlier drafts exist, or advance notice where the "
            "timing matters. Do not flag a fixed term from a field or a product "
            "name. Report at most the 15 most important instances. Quote the "
            "exact words from the text, verbatim and short. In the note, name the "
            "problem and say what it costs the reader. Send the words to cut as "
            "an edit on the finding, with an empty replacement. The target must "
            "be the exact words from the text."
        ),
    },
    {
        "slug": "cut-redundant-categories",
        "title": "Cut redundant category words",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for a word that names the category a nearby word already "
            "belongs to. A period of time, an area of research, in a state of "
            "confusion, pink in color, large in size, and the process of testing "
            "are instances. The reader knows that pink is a color and that a week "
            "is time. Do not flag a category word that separates two real senses, "
            "such as a field of study against a field of grass. Do not flag a "
            "defined term in a technical document. Report at most the 15 most "
            "important instances. Quote the exact words from the text, verbatim "
            "and short. In the note, name the problem and say what it costs the "
            "reader. Send the words to cut as an edit on the finding, with an "
            "empty replacement. The target must be the exact words from the "
            "text."
        ),
    },
    {
        "slug": "replace-phrases-with-words",
        "title": "Replace phrases with single words",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for a multi-word phrase that one plain word covers. In order "
            "to, due to the fact that, for the purpose of, in the event that, at "
            "this point in time, with regard to, and has the ability to are "
            "instances. Flag the phrase when a single common word carries the "
            "same sense. Do not flag a phrase that adds a shade the short word "
            "drops, such as a cause the writer wants to stress. Do not flag a "
            "fixed phrase from law, a standard, or an interface label. Report at "
            "most the 15 most important instances. Quote the exact words from the "
            "text, verbatim and short. In the note, name the problem and say what "
            "it costs the reader. Send the plain equivalent as an edit on the "
            "finding. The target must be the exact words from the text, and the "
            "replacement must be the shortest wording that keeps the meaning."
        ),
    },
    {
        "slug": "turn-negatives-into-affirmatives",
        "title": "Turn negatives into affirmatives",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for a negative that hides a plain claim. Not unlike, not "
            "uncommon, did not remember, does not have many, and not without merit "
            "are instances. A stack of two or more negatives in one clause is an "
            "instance too, because the reader must unwind each one. Do not flag a "
            "negative that states the real point, such as a rule that forbids "
            "something or a result that did not happen. Do not flag a negative "
            "that marks a contrast with a claim made just before. Report at most "
            "the 15 most important instances. Quote the exact words from the "
            "text, verbatim and short. In the note, name the problem and say what "
            "it costs the reader. Send the plain equivalent as an edit on the "
            "finding. The target must be the exact words from the text, and the "
            "replacement must be the shortest wording that keeps the meaning."
        ),
    },
    {
        "slug": "trim-metadiscourse",
        "title": "Trim talk about the writing",
        "group": "Writing cleanup",
        "suggests_edits": True,
        "prompt": (
            "Look for sentences and clauses about the writing rather than the "
            "subject. I think that, it should be noted that, in this section I "
            "will argue, as mentioned above, and it is interesting to observe are "
            "instances. Flag the words that announce a move instead of making it. "
            "Do not flag a signpost that a long or technical document needs, such "
            "as a pointer to a section the reader must find. Do not flag a hedge "
            "that marks who holds an opinion when the source matters. Report at "
            "most the 15 most important instances. Quote the exact words from the "
            "text, verbatim and short. In the note, name the problem and say what "
            "it costs the reader. Send the words to cut as an edit on the "
            "finding, with an empty replacement. The target must be the exact "
            "words from the text."
        ),
    },
    # --- Clarity ---
    {
        "slug": "find-the-real-actors",
        "title": "Find the real actors",
        "group": "Clarity",
        "prompt": (
            "Look for sentences where the reader cannot tell who does what. An "
            "instance is a sentence with no actor at all, an actor buried in a "
            "prepositional phrase, or a vague actor such as the system, the "
            "organization, or it. Ask of each main clause: who acts here? If the "
            "answer needs a guess, flag the sentence. Do not flag a sentence about "
            "a state rather than an action. Do not flag a sentence where the actor "
            "is named in the sentence before and stays clear. Report at most the "
            "15 most important instances. Quote the exact words from the text, "
            "verbatim and short. In the note, name the problem and say what it "
            "costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "restore-actions-to-verbs",
        "title": "Restore actions to verbs",
        "group": "Clarity",
        "prompt": (
            "Look for actions turned into nouns. The analysis of, the decision to, "
            "made an evaluation, gave consideration to, and the implementation of "
            "are instances. These nouns often end in -tion, -ment, -ance, or "
            "-ity, and they sit next to a weak verb. Flag the noun when the "
            "sentence hides its action there. Do not flag a noun that names a "
            "thing, a document, or a defined term, such as an assessment the team "
            "publishes. Do not flag a noun that refers back to a point already "
            "made. Report at most the 15 most important instances. Quote the exact "
            "words from the text, verbatim and short. In the note, name the "
            "problem and say what it costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "delete-empty-verbs",
        "title": "Delete empty verbs",
        "group": "Clarity",
        "suggests_edits": True,
        "prompt": (
            "Look for verbs that carry no action. Is, has, make, do, perform, "
            "conduct, provide, and undertake count as instances when the real "
            "action sits in a nearby noun or adjective. Phrases such as performs a "
            "review, makes a contribution, and is supportive of are instances. Do "
            "not flag a linking verb that states a real identity or a real "
            "condition, such as a definition. Do not flag have when it means "
            "possession. Do not flag a verb that is the only action available. "
            "Report at most the 15 most important instances. Quote the exact words "
            "from the text, verbatim and short. In the note, name the problem and "
            "say what it costs the reader. Send the plain equivalent as an edit "
            "on the finding. The target must be the exact words from the text, "
            "and the replacement must be the shortest wording that keeps the "
            "meaning."
        ),
    },
    {
        "slug": "prefer-characters-as-subjects",
        "title": "Make characters the subjects",
        "group": "Clarity",
        "prompt": (
            "Look for main clauses whose subject is an abstraction rather than a "
            "person or a concrete thing. Subjects such as the consideration of "
            "risk, the availability of resources, and the expectation is that are "
            "instances, because a person or a thing acts somewhere else in the "
            "sentence. Flag the subject and say who or what really acts. Do not "
            "flag an abstract subject in a field where the abstraction is the "
            "topic, such as a proof about numbers. Do not flag a short subject "
            "the reader already knows. Report at most the 15 most important "
            "instances. Quote the exact words from the text, verbatim and short. "
            "In the note, name the problem and say what it costs the reader. Never "
            "propose new wording."
        ),
    },
    {
        "slug": "join-subjects-and-verbs",
        "title": "Put subjects beside their verbs",
        "group": "Clarity",
        "prompt": (
            "Look for a long interruption between a subject and its verb. A "
            "relative clause, a string of prepositional phrases, or an aside of "
            "more than about eight words between the two counts as an instance. "
            "The reader must hold the subject in mind while the sentence wanders. "
            "Flag the gap. Do not flag a short modifier of a few words. Do not "
            "flag an interruption that the sentence needs to fix the reference, "
            "and that no other slot can hold. Report at most the 15 most "
            "important instances. Quote the exact words from the text, verbatim "
            "and short. In the note, name the problem and say what it costs the "
            "reader. Never propose new wording."
        ),
    },
    {
        "slug": "join-verbs-and-objects",
        "title": "Put verbs beside their objects",
        "group": "Clarity",
        "prompt": (
            "Look for a long interruption between a verb and its object. An "
            "adverbial phrase, a list of conditions, or a clause of more than "
            "about eight words between the two counts as an instance. The reader "
            "waits for the object and loses the thread. Flag the gap and name the "
            "verb that is left hanging. Do not flag a short adverb next to the "
            "verb. Do not flag a sentence where the object is a long clause that "
            "must come last. Report at most the 15 most important instances. Quote "
            "the exact words from the text, verbatim and short. In the note, name "
            "the problem and say what it costs the reader. Never propose new "
            "wording."
        ),
    },
    {
        "slug": "name-responsibility",
        "title": "Name who is responsible",
        "group": "Clarity",
        "prompt": (
            "Look for sentences that hide the actor behind a fault, a loss, or a "
            "decision. Mistakes were made, the delay occurred, the data was lost, "
            "and a decision was reached are instances when the text never names "
            "who acted. An abstract actor that cannot act, such as the timeline "
            "or the budget, is an instance too. Do not flag a sentence where the "
            "writer states that the actor is unknown. Do not flag a sentence where "
            "the actor appears clearly in the same paragraph. Report at most the "
            "15 most important instances. Quote the exact words from the text, "
            "verbatim and short. In the note, name the problem and say what it "
            "costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "control-passive-voice",
        "title": "Control the passive voice",
        "group": "Clarity",
        "prompt": (
            "Look for passive verbs that hide the actor or break the flow. An "
            "instance is a passive whose actor matters to the reader and never "
            "appears, or a passive that puts old information last and new "
            "information first. Do not flag a passive that keeps the topic of the "
            "passage in the subject slot. Do not flag a passive that drops an "
            "actor nobody needs, such as a standard step in a method. Do not flag "
            "a passive that moves a long phrase to the end. Judge each passive on "
            "its work, not on its form. Report at most the 15 most important "
            "instances. Quote the exact words from the text, verbatim and short. "
            "In the note, name the problem and say what it costs the reader. Never "
            "propose new wording."
        ),
    },
    {
        "slug": "untangle-noun-strings",
        "title": "Untangle long noun strings",
        "group": "Clarity",
        "prompt": (
            "Look for three or more nouns in a row used as one name. Customer "
            "data retention policy review and outbox event worker process are "
            "instances. The reader must guess which noun modifies which. Flag the "
            "string and say where the reading breaks. Do not flag an established "
            "technical name, a product name, or a code identifier that the field "
            "uses as one term. Do not flag a two-noun pair. Do not flag a string "
            "the document defines on first use. Report at most the 15 most "
            "important instances. Quote the exact words from the text, verbatim "
            "and short. In the note, name the problem and say what it costs the "
            "reader. Never propose new wording."
        ),
    },
    # --- Cohesion and flow ---
    {
        "slug": "start-with-known-information",
        "title": "Start sentences with known information",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for sentences that open with something new to the reader. An "
            "instance is a sentence whose first words introduce a term, a name, "
            "or an idea that no earlier sentence set up, while the link to the "
            "paragraph sits at the end. Check each sentence against the one "
            "before it. Do not flag the first sentence of a document or a "
            "section. Do not flag a sentence that opens a deliberate turn, such as "
            "a contrast the writer marks. Report at most the 15 most important "
            "instances. Quote the exact words from the text, verbatim and short. "
            "In the note, name the problem and say what it costs the reader. Never "
            "propose new wording."
        ),
    },
    {
        "slug": "put-new-information-last",
        "title": "Put new information last",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for sentences that spend their ending on old or minor words. An "
            "instance is a sentence whose key term, number, or claim sits in the "
            "middle while a stale phrase, a qualifier, or a date closes the "
            "sentence. The end of a sentence is where the reader looks for the "
            "point. Do not flag a short sentence where the whole content is new. "
            "Do not flag an ending the next sentence picks up as its opening. "
            "Report at most the 15 most important instances. Quote the exact words "
            "from the text, verbatim and short. In the note, name the problem and "
            "say what it costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "repair-topic-flow",
        "title": "Repair the topic flow",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for a passage whose sentences keep switching subjects. An "
            "instance is a run of three or more sentences where each one opens on "
            "a different topic, so the reader cannot tell what the passage is "
            "about. Quote the opening words of the sentence where the chain "
            "breaks. Do not flag a shift the writer marks and then holds for "
            "several sentences. Do not flag a list where each item names a "
            "different thing on purpose. Report at most the 15 most important "
            "instances. Quote the exact words from the text, verbatim and short. "
            "In the note, name the problem and say what it costs the reader. Never "
            "propose new wording."
        ),
    },
    {
        "slug": "repair-stress-flow",
        "title": "Repair weak sentence endings",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for sentences that end weakly. An instance is a sentence that "
            "closes on a trailing qualifier, a vague phrase such as in many ways, "
            "an aside in brackets, or a repeated term, while the term the reader "
            "needs sits earlier. The last words of a sentence carry the weight, "
            "and a weak ending drops it. Do not flag an ending that the next "
            "sentence takes up. Do not flag a short sentence with one clear "
            "point. Report at most the 15 most important instances. Quote the "
            "exact words from the text, verbatim and short. In the note, name the "
            "problem and say what it costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "state-the-paragraph-point",
        "title": "State the paragraph point",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for paragraphs with no clear point near the start. An instance "
            "is a paragraph whose first two sentences give background, an example, "
            "or a detail, while the claim arrives at the end or never arrives. A "
            "paragraph that makes two unrelated claims is an instance too. Quote "
            "the opening words of the paragraph. Do not flag a short transition "
            "paragraph. Do not flag a paragraph that holds back the point for a "
            "stated reason, such as the close of an argument built earlier. Report "
            "at most the 15 most important instances. Quote the exact words from "
            "the text, verbatim and short. In the note, name the problem and say "
            "what it costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "keep-subjects-consistent",
        "title": "Keep subjects consistent throughout",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for a passage where the subjects of the sentences do not form a "
            "set. An instance is a run of sentences that names one thing by "
            "several labels, or that moves between a person, a process, and an "
            "abstraction with no link. The reader cannot see the cast of the "
            "passage. Quote the subject where the set breaks. Do not flag a change "
            "of subject that the writer signals and holds. Do not flag a passage "
            "that compares two parties on purpose. Report at most the 15 most "
            "important instances. Quote the exact words from the text, verbatim "
            "and short. In the note, name the problem and say what it costs the "
            "reader. Never propose new wording."
        ),
    },
    {
        "slug": "check-paragraph-order",
        "title": "Check the paragraph order",
        "group": "Cohesion and flow",
        "prompt": (
            "Look for paragraphs that sit in the wrong place. An instance is a "
            "paragraph that gives a definition after the term is used, an example "
            "before the claim it supports, or a detail that would help the reader "
            "several paragraphs earlier. A paragraph that repeats an earlier one "
            "is an instance too. Quote the opening words of the paragraph and name "
            "the place it belongs near. Do not flag an order the document states, "
            "such as numbered steps. Do not flag a deliberate delay the writer "
            "explains. Report at most the 15 most important instances. Quote the "
            "exact words from the text, verbatim and short. In the note, name the "
            "problem and say what it costs the reader. Never propose new wording."
        ),
    },
    # --- Sentences ---
    {
        "slug": "break-up-sprawl",
        "title": "Break up sprawling sentences",
        "group": "Sentences",
        "prompt": (
            "Look for sentences that keep adding clauses. An instance is a "
            "sentence that strings three or more clauses with and, which, or "
            "that, or a sentence that runs past about forty words and asks the "
            "reader to hold several ideas at once. Trailing clauses tacked on "
            "after the main point count too. Do not flag a long sentence built as "
            "a clear list with parallel parts. Do not flag a long sentence whose "
            "clauses follow one line of thought in order. Report at most the 15 "
            "most important instances. Quote the exact words from the text, "
            "verbatim and short. In the note, name the problem and say what it "
            "costs the reader. Never propose new wording."
        ),
    },
    {
        "slug": "fix-coordination-and-parallelism",
        "title": "Fix coordination and parallelism",
        "group": "Sentences",
        "prompt": (
            "Look for joined parts that do not match. An instance is a list whose "
            "items switch grammatical form, a pair joined by and where the halves "
            "are of different kinds, or a correlative such as not only or either "
            "whose two sides do not line up. A coordination that joins parts of "
            "unequal weight is an instance too. Do not flag a deliberate break "
            "that the sentence marks. Do not flag a list of unlike items where "
            "each item still takes the same form. Report at most the 15 most "
            "important instances. Quote the exact words from the text, verbatim "
            "and short. In the note, name the problem and say what it costs the "
            "reader. Never propose new wording."
        ),
    },
    {
        "slug": "vary-sentence-length",
        "title": "Vary sentence length and rhythm",
        "group": "Sentences",
        "prompt": (
            "Look for long runs of sentences with the same length or the same "
            "build. An instance is a run of four or more sentences of about the "
            "same length, or a run that opens the same way each time, such as "
            "subject then verb with no change. The reader stops hearing the "
            "sentences and skims. Quote the opening words of the run. Do not flag "
            "short sentences used in a row for a clear effect, such as a series of "
            "steps. Do not flag a list. Report at most the 15 most important "
            "instances. Quote the exact words from the text, verbatim and short. "
            "In the note, name the problem and say what it costs the reader. Never "
            "propose new wording."
        ),
    },
    {
        "slug": "shorten-long-openers",
        "title": "Shorten long sentence openers",
        "group": "Sentences",
        "prompt": (
            "Look for a long windup before the subject. An instance is a sentence "
            "that opens with more than about ten words of introductory clauses, "
            "conditions, or qualifiers before the reader meets the subject. "
            "Stacked openers, such as a time phrase and a condition and an aside, "
            "count as one instance. Do not flag a short opener of a few words that "
            "sets the frame. Do not flag an opening condition that the sentence "
            "needs first, such as a rule that applies only in one case. Report at "
            "most the 15 most important instances. Quote the exact words from the "
            "text, verbatim and short. In the note, name the problem and say what "
            "it costs the reader. Never propose new wording."
        ),
    },
    # --- Shape ---
    {
        "slug": "motivate-the-problem",
        "title": "Motivate the problem up front",
        "group": "Shape",
        "prompt": (
            "Look at the opening and ask whether it tells the reader why the piece "
            "matters. An instance is an opening that gives background with no "
            "trouble to solve, an opening that states a topic but no gap, or an "
            "opening that asks the reader to wait several paragraphs for the "
            "stakes. Quote the opening words that carry the fault. Do not flag an "
            "opening that names the problem in plain terms, even a short one. Do "
            "not flag a form where the reader expects no setup, such as a "
            "reference entry. Report at most the 15 most important instances. "
            "Quote the exact words from the text, verbatim and short. In the note, "
            "name the problem and say what it costs the reader. Never propose new "
            "wording."
        ),
    },
    {
        "slug": "land-the-point",
        "title": "Land the point",
        "group": "Shape",
        "prompt": (
            "Look at where the piece states its main point and how it ends. An "
            "instance is a point the reader cannot find in the opening or the "
            "close, a point stated in a middle paragraph and never repeated, or an "
            "ending that adds a new idea, trails off, or only repeats the opening "
            "words. Quote the sentence that should carry the point. Do not flag a "
            "form that states the point in a heading or a summary block. Do not "
            "flag a short close that follows from the argument. Report at most the "
            "15 most important instances. Quote the exact words from the text, "
            "verbatim and short. In the note, name the problem and say what it "
            "costs the reader. Never propose new wording."
        ),
    },
]
