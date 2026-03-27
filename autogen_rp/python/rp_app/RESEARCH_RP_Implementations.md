# AutoGen Roleplay (RP) System Implementations - Research Summary

**Date Researched:** March 13, 2026  
**Framework:** Microsoft AutoGen  
**Scope:** Community implementations of roleplay systems using AutoGen v0.2 and v0.4

---

## Executive Summary

While Microsoft AutoGen was designed as a general-purpose multi-agent AI framework (not specifically for roleplay), the community has adapted it extensively for narrative fiction, character simulation, and interactive storytelling. This document captures known RP implementations, patterns, and architectural approaches found in community projects, tutorials, and academic work.

**Important Version Note:** AutoGen underwent significant API changes between v0.2 and v0.4. Many documented RP implementations use the older v0.2 API (`GroupChat`, `ConversableAgent`) while newer implementations should use v0.4 (`SelectorGroupChat`, `AssistantAgent`).

---

## 1. D&D/TTRPG Simulator (v0.2 Implementation)

**Source:** [Matthijs van der Veer's Blog](https://www.vanderveer.io/autogen-dungeons-and-dragons/)  
**Version:** AutoGen 0.2  
**Architecture:** GroupChat with GroupChatManager

### Key Components

| Component | Role | Implementation |
|-----------|------|----------------|
| **DM Agent** | Dungeon master, story controller | `AssistantAgent` with high temperature (0.9), `human_input_mode="NEVER"` |
| **Player Agents** | Character bots | `AssistantAgent` with character system messages |
| **Human Player** | User participation | Same agent class with `human_input_mode="ALWAYS"` |
| **GroupChatManager** | Turn orchestration | LLM-based speaker selection |

### Architecture Pattern

```python
# v0.2 Pattern - GroupChat
group_chat = GroupChat(
    agents=[dm, player1, player2, human_player],
    messages=[],
    max_round=160,
    send_introductions=True
)
group_chat_manager = GroupChatManager(
    groupchat=group_chat,
    llm_config=llm_config2
)

# Start the game
dm.initiate_chat(
    group_chat_manager,
    message="Welcome to our first session...",
    summary_method="reflection_with_llm"
)
```

### Key Design Decisions

- **System Messages:** Written in second person ("You are an Orcish Barbarian...")
- **Temperature:** Set to 0.9 for creative/less predictable outputs
- **Conversation Pattern:** Full broadcast (all agents see all messages, like a real table)
- **Human Integration:** Human player uses same agent class with different `human_input_mode`

### Limitations Noted by Author

- LLMs cannot generate truly random results (dice rolling would need code execution)
- No persistent character state between sessions
- DM and players can speak for each other (no strict separation of agency)

---

## 2. Multi-Agent Book Writing System (v0.2 Implementation)

**Source:** [GitHub - adamwlarson/ai-book-writer](https://github.com/adamwlarson/ai-book-writer)  
**Version:** AutoGen 0.2+  
**Architecture:** Specialized agents with defined workflow

### Agent Roles

| Agent | Responsibility |
|-------|--------------|
| **Story Planner** | High-level story arcs and plot points |
| **World Builder** | Consistent setting management |
| **Memory Keeper** | Continuity tracking |
| **Writer** | Prose generation |
| **Editor** | Content review and improvement |
| **Outline Creator** | Detailed chapter outlines |

### Architecture Pattern

```python
# Agent creation with specialized system messages
outline_agents = BookAgents(agent_config)
agents = outline_agents.create_agents()

# Workflow: Outline → Book
outline_gen = OutlineGenerator(agents, agent_config)
outline = outline_gen.generate_outline(prompt, num_chapters=25)

book_agents = BookAgents(agent_config, outline)
agents_with_context = book_agents.create_agents()
book_gen = BookGenerator(agents_with_context, agent_config, outline)
book_gen.generate_book(outline)
```

### Output Structure

```
book_output/
├── outline.txt
├── chapter_01.txt
├── chapter_02.txt
└── ...
```

### Key Features

- Structured chapter generation with consistent formatting
- Story continuity through explicit memory agent
- World-building consistency checks
- Multi-chapter narrative support

---

## 3. StoryWriter Framework (Academic Research)

**Source:** [ACM Digital Library](https://dl.acm.org/doi/10.1145/3746252.3761616), [arXiv](https://arxiv.org/pdf/2506.16445)  
**Framework:** Multi-agent story generation using AutoGen concepts  
**Approach:** Planning → Writing → Refinement

### Three-Stage Pipeline

1. **Planning Agent:** Event-based outline generation
2. **Writing Agent:** Non-Linear Narration (NLN) approach
3. **Re-writing Agent:** ReIO (Re-write Input and Output) for final synthesis

### Key Innovation

- **MaPS (Multi-agent Pipeline Strategy):** Breaks long story generation into manageable subtasks
- **Event-based outlines:** Structured approach to plot development
- **NLN:** Handles non-linear narrative elements

---

## 4. Fantasy Book Generator with DALL-E (v0.2)

**Source:** [Mervin Praison's Blog](https://mer.vin/2024/03/autogen-ai-agents-to-write-books/)  
**Version:** AutoGen 0.2  
**Features:** Multi-modal cover generation

### Agent Workflow

1. **Author Proxy:** Defines book requirements
2. **Chapter Outliner:** Structures chapters
3. **Content Writer:** Fills chapter details
4. **Character Developer:** Provides backstories
5. **Editor:** Polishes text
6. **Cover Designer:** DALL-E integration for visual covers

### Sample Output Pattern

```
author_proxy → chat_manager: Book requirements
chapter_outliner → chat_manager: Chapter structure
content_writer → chat_manager: Chapter prose
character_developer → chat_manager: Character sheets
editor → chat_manager: Final review
```

---

## 5. v0.4 Modern Implementations

**Note:** Most documented RP implementations found use v0.2. v0.4+ implementations appear to be less documented in community tutorials.

### v0.4 API Changes Relevant to RP

| v0.2 (Legacy) | v0.4 (Current) |
|--------------|----------------|
| `GroupChat` | `SelectorGroupChat` |
| `ConversableAgent` | `AssistantAgent` |
| `GroupChatManager` | `SelectorGroupChat` (built-in) |
| `initiate_chat()` | `team.run()` |
| `human_input_mode` | Not directly applicable |

### SelectorGroupChat for RP (v0.4)

```python
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination

# v0.4 Pattern
team = SelectorGroupChat(
    participants=[character1, character2, narrator],
    model_client=openai_client,
    selector_prompt="""Select the next character to speak based on:
    - Who was addressed in the last message
    - Dramatic flow and tension
    - Who hasn't spoken recently""",
    termination_condition=MaxMessageTermination(max_messages=10)
)
```

### Key Differences v0.2 → v0.4

- **Speaker Selection:** v0.4 uses `selector_prompt` + optional custom selector function
- **Human Integration:** v0.4 requires `UserProxyAgent` or manual input handling
- **State Persistence:** v0.4 has built-in `save_state()` / `load_state()`
- **Termination:** Explicit termination conditions in v0.4 vs. max_round in v0.2

---

## 6. Community Discussion Patterns

### From r/AutoGenAI and Related Communities

**Common RP Use Cases Discussed:**

1. **Quest Generation:** NPCs with goals and dialogue trees
2. **Character Simulation:** Persistent personalities in conversation
3. **DM/GM Tools:** Automated content generation for tabletop sessions
4. **Interactive Fiction:** Choice-based narrative with character agents

**Reported Challenges:**

- **System message perspective confusion:** GroupChatManager sees all system messages in one prompt, causing "you are X" confusion when selecting next speaker (GitHub Issue #319)
- **Model limitations:** GPT-3.5 struggles with complex multi-character scenes; GPT-4+ recommended
- **No native state management:** Characters don't remember previous sessions without custom implementation
- **Cross-character bleed:** Agents speaking for each other (common issue in free-form implementations)

---

## 7. Architectural Patterns Summary

### Pattern A: Direct Group Chat (v0.2)

All agents in `GroupChat`, messages broadcast to everyone. Simplest but has bleed issues.

**Pros:** Simple, flexible  
**Cons:** Characters narrate for each other, no output control

### Pattern B: Workflow Pipeline (v0.2/v0.4)

Sequential agents: Planner → Writer → Editor. Used for long-form content generation.

**Pros:** Structured output, quality control  
**Cons:** Not interactive, no real-time roleplay

### Pattern C: Selector-Based Turn Taking (v0.4)

`SelectorGroupChat` with custom selector function controlling who speaks when.

**Pros:** Controlled turn flow, can enforce alternation  
**Cons:** Requires careful prompt engineering

### Pattern D: Narrator-Mediated (Custom)

Characters output structured data (JSON), narrator renders to prose. Separation of decision and narration.

**Pros:** Prevents cross-character bleed, consistent prose style  
**Cons:** Latency (two LLM calls per turn), loss of character voice quirks

---

## 8. Key Takeaways for RP Development

1. **Version Matters:** Most documented examples are v0.2. v0.4 API is significantly different.

2. **State Management is Manual:** AutoGen doesn't provide character memory/persistence out of the box. Community implementations add custom state layers.

3. **Cross-Character Bleed is Common:** Without strict architectural separation (like structured output + narrator), agents frequently speak for each other.

4. **Temperature Matters:** Creative RP benefits from higher temperature (0.7-0.9), but this increases unpredictability.

5. **GroupChat vs. SelectorGroupChat:** 
   - v0.2 `GroupChat` = broadcast to all
   - v0.4 `SelectorGroupChat` = LLM decides next speaker
   - Neither inherently prevents one character from dominating

6. **Human Integration:** In v0.2, human players use `human_input_mode`. In v0.4, use `UserProxyAgent` or custom input handling.

---

## 9. References

1. [Building A Quick D&D Simulator With AutoGen](https://www.vanderveer.io/autogen-dungeons-and-dragons/) - Matthijs van der Veer
2. [ai-book-writer GitHub Repository](https://github.com/adamwlarson/ai-book-writer) - Adam Larson
3. [StoryWriter: A Multi-Agent Framework for Long Story Generation](https://dl.acm.org/doi/10.1145/3746252.3761616) - ACM Digital Library
4. [AutoGen AI Agents To Write Books](https://mer.vin/2024/03/autogen-ai-agents-to-write-books/) - Mervin Praison
5. [Group Chat v0.2 Documentation](https://microsoft.github.io/autogen/0.2/docs/notebooks/agentchat_groupchat/) - Microsoft
6. [SelectorGroupChat v0.4 Documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html) - Microsoft
7. [AutoGen Team Workflows](https://www.gettingstarted.ai/autogen-teams/) - Getting Started AI

---

## 10. Research Limitations

- **Reddit/Community Content:** Many AutoGen community discussions are on Reddit, which was not accessible during research due to access restrictions.
- **Version Ambiguity:** Some implementations don't explicitly state their AutoGen version.
- **Private Implementations:** Many RP systems built with AutoGen are likely private/unpublished.

---

*Document generated for research purposes on RP systems using Microsoft AutoGen framework.*
