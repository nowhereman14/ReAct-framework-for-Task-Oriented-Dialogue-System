# ReAct-framework-for-Task-Oriented-Dialogue-System

State-of-the-art Task-Oriented Dialogue (TOD) systems based on Large Language Models (LLMs) generate natural and fluent responses, but struggle to dinamically retrieve information for external databases, often leading to hallucinations due to their reliance on static parametric knowledge (Dhuliawala et al., 2023). This problem can be addresed by adapting the ReAct agentic framework to a Task-Oriented Dialogue system, enabling LLMs to actively access and reason over external knowledge sources.

In this project, following the method proposed my Merkel et al. (2026), a series of custom tools and designed prompts were used to guide the model through an iterative sequence of thoughts, actions, and observations in order to produce factual responses to information-seeking queries. Moreover, a REST API was developed to provide the ReAct system with dynamic access to the database, enabling structured queries over instances.

The evaluation was carried out using a series of automated metric, as well as an LLM-as-a-judge apporach suing the Prometheus evaluation library.


# Data

Our study was based on the MultiWoz 2.2 dataset (Zang et al., 2020), a fully-labeled collection of human written conversations spanning over multiple domains and topics, being by far the larger annotated task-oriented copus nowadays. This corpus, unlike the SIMMC 2.1 dataset used by Merk et al (2026), is not multimodal, so we can test the ReAct framework in simpler situations. The domains selected in this work are hotels and restaurants.

# The ReAct framework

We designed an agentic system which actuvely retries information about relevant instances through a REST API, preventing acces to unrelated information. We implement an adaptation of the ReAct framework (Yao et al., 2023) tailored in the MultiWoz dataset and equipt it with a serie of tools specialised in information retrieval.

The system receives the instruction prompt, the dialogue history and the user's query as inputs and generates the final response through an iterative sequence of thoughts, actions, and observations. The actions require the use of the aforementioned tools:

- Look[]: returns the medatada of all the instances of the selected travel scene.
- Search[]: retrieves the the instances in the scene that satisfy an specific query.
- Finish[answer]: an action used by the model to indicate the final response that the systems returns.

![Diagrama sin título (5)](https://github.com/user-attachments/assets/32bed0ce-3f91-4b35-8c85-26a5445dcfb3)


