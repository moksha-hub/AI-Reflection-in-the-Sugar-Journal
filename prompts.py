# -*- coding: utf-8 -*-
"""
Static prompt library for the Reflective Loop.

Every strategy × depth × language combination has a curated, age-appropriate
fallback question. If the LLM produces invalid output, the child always sees
one of these safe, pre-written questions — never raw model output.
"""

# ---------------------------------------------------------------------------
# System prompt template — constrains LLM to produce exactly ONE question
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are a reflective guide for a young learner aged 6–14.
Your ONLY job is to ask ONE short, open-ended reflection question.
Rules:
- Ask exactly ONE question. No follow-ups. No statements.
- Never answer the question yourself.
- Never generate creative content, stories, or code.
- Never ask for personal information (name, address, family).
- Your entire response must end with a question mark.
- Use simple, encouraging language appropriate for a child.
Language: {language}"""


# ---------------------------------------------------------------------------
# Static fallback prompts: strategy × depth × language
# ---------------------------------------------------------------------------

PROMPTS = {
    "en": {
        "socratic": {
            1: "What did you create in this activity?",
            2: "Why did you choose to do it that way instead of another way?",
            3: "Where have you seen patterns like this in the real world?",
            4: "If you could teach someone else how to do this, what would be the most important thing to explain?",
        },
        "kwl": {
            1: "What did you already know before you started?",
            2: "What new thing did you learn that surprised you?",
            3: "How does what you learned connect to something you already knew?",
            4: "What is something you still want to find out after this activity?",
        },
        "what_so_what_now_what": {
            1: "What happened during this activity?",
            2: "Why do you think that matters?",
            3: "How could you use what you learned in a different project?",
            4: "What is the hardest version of this project you can imagine making?",
        },
    },
    "es": {
        "socratic": {
            1: "¿Qué creaste en esta actividad?",
            2: "¿Por qué elegiste hacerlo de esa manera?",
            3: "¿Dónde has visto patrones como este en el mundo real?",
            4: "Si pudieras enseñarle a alguien cómo hacer esto, ¿qué sería lo más importante de explicar?",
        },
        "kwl": {
            1: "¿Qué sabías antes de empezar?",
            2: "¿Qué cosa nueva aprendiste que te sorprendió?",
            3: "¿Cómo se conecta lo que aprendiste con algo que ya sabías?",
            4: "¿Qué es algo que todavía quieres descubrir después de esta actividad?",
        },
        "what_so_what_now_what": {
            1: "¿Qué pasó durante esta actividad?",
            2: "¿Por qué crees que eso es importante?",
            3: "¿Cómo podrías usar lo que aprendiste en un proyecto diferente?",
            4: "¿Cuál es la versión más difícil de este proyecto que puedes imaginar?",
        },
    },
    "hi": {
        "socratic": {
            1: "इस गतिविधि में तुमने क्या बनाया?",
            2: "तुमने ऐसा क्यों करने का फैसला किया?",
            3: "तुमने असली दुनिया में ऐसे पैटर्न कहाँ देखे हैं?",
            4: "अगर तुम किसी को यह सिखाओगे तो सबसे ज़रूरी बात क्या होगी?",
        },
        "kwl": {
            1: "शुरू करने से पहले तुम क्या जानते थे?",
            2: "तुमने कौन सी नई चीज़ सीखी जिसने तुम्हें चौंकाया?",
            3: "जो तुमने सीखा वह किसी पहले से जानी हुई चीज़ से कैसे जुड़ता है?",
            4: "इस गतिविधि के बाद तुम और क्या जानना चाहते हो?",
        },
        "what_so_what_now_what": {
            1: "इस गतिविधि के दौरान क्या हुआ?",
            2: "तुम्हें क्यों लगता है कि यह महत्वपूर्ण है?",
            3: "जो तुमने सीखा उसे तुम किसी अलग प्रोजेक्ट में कैसे इस्तेमाल कर सकते हो?",
            4: "इस प्रोजेक्ट का सबसे कठिन संस्करण क्या होगा जो तुम बना सकते हो?",
        },
    },
    "fr": {
        "socratic": {
            1: "Qu'as-tu créé dans cette activité ?",
            2: "Pourquoi as-tu choisi de le faire de cette façon ?",
            3: "Où as-tu vu des motifs comme celui-ci dans le monde réel ?",
            4: "Si tu pouvais enseigner à quelqu'un comment faire ça, quelle serait la chose la plus importante à expliquer ?",
        },
        "kwl": {
            1: "Que savais-tu avant de commencer ?",
            2: "Quelle chose nouvelle as-tu apprise qui t'a surpris ?",
            3: "Comment ce que tu as appris se connecte-t-il à quelque chose que tu savais déjà ?",
            4: "Qu'est-ce que tu veux encore découvrir après cette activité ?",
        },
        "what_so_what_now_what": {
            1: "Que s'est-il passé pendant cette activité ?",
            2: "Pourquoi penses-tu que c'est important ?",
            3: "Comment pourrais-tu utiliser ce que tu as appris dans un projet différent ?",
            4: "Quelle est la version la plus difficile de ce projet que tu puisses imaginer ?",
        },
    },
    "pt": {
        "socratic": {
            1: "O que você criou nesta atividade?",
            2: "Por que você escolheu fazer assim?",
            3: "Onde você já viu padrões como esse no mundo real?",
            4: "Se você pudesse ensinar alguém a fazer isso, o que seria mais importante explicar?",
        },
        "kwl": {
            1: "O que você já sabia antes de começar?",
            2: "O que de novo você aprendeu que te surpreendeu?",
            3: "Como o que você aprendeu se conecta com algo que já sabia?",
            4: "O que você ainda quer descobrir depois desta atividade?",
        },
        "what_so_what_now_what": {
            1: "O que aconteceu durante esta atividade?",
            2: "Por que você acha que isso é importante?",
            3: "Como você poderia usar o que aprendeu em um projeto diferente?",
            4: "Qual é a versão mais difícil deste projeto que você consegue imaginar?",
        },
    },
}


# ---------------------------------------------------------------------------
# Peer-awareness questions for collaborative sessions
# ---------------------------------------------------------------------------

PEER_QUESTIONS = {
    "en": {
        "socratic": "What surprised you about how your partner approached the problem?",
        "kwl": "What did your collaborator teach you that you didn't already know?",
        "what_so_what_now_what": "How did working together change what you ended up making?",
    },
    "es": {
        "socratic": "¿Qué te sorprendió de cómo tu compañero abordó el problema?",
        "kwl": "¿Qué te enseñó tu compañero que no sabías?",
        "what_so_what_now_what": "¿Cómo cambió lo que hiciste al trabajar en equipo?",
    },
    "hi": {
        "socratic": "तुम्हारे साथी ने समस्या को कैसे हल किया, इसमें तुम्हें क्या चौंकाया?",
        "kwl": "तुम्हारे साथी ने तुम्हें क्या सिखाया जो तुम पहले नहीं जानते थे?",
        "what_so_what_now_what": "साथ मिलकर काम करने से तुम्हारी बनाई चीज़ कैसे बदल गई?",
    },
    "fr": {
        "socratic": "Qu'est-ce qui t'a surpris dans l'approche de ton partenaire ?",
        "kwl": "Qu'est-ce que ton partenaire t'a appris que tu ne savais pas ?",
        "what_so_what_now_what": "Comment le fait de travailler ensemble a-t-il changé ce que vous avez créé ?",
    },
    "pt": {
        "socratic": "O que te surpreendeu na forma como seu parceiro abordou o problema?",
        "kwl": "O que seu parceiro te ensinou que você não sabia?",
        "what_so_what_now_what": "Como trabalhar junto mudou o que vocês acabaram fazendo?",
    },
}
