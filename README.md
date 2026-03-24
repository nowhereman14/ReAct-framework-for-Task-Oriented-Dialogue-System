# ReAct-framework-for-Task-Oriented-Dialogue-System

State-of-the-art Task-Oriented Dialogue (TOD) systems based on Large Language Models (LLMs) generate natural and fluent responses, but struggle to dinamically retrieve information for external databases, often leading to hallucinations due to their reliance on static parametric knowledge. This problem can be addresed by adapting the ReAct agentic framework to a Task-Oriented Dialogue system, enabling LLMs to actively access and reason over external knowledge sources.

A series of custom tools and designed prompts were used to guide the model through an iterative sequence of thoughts, actions, and observations in order to produce factual responses to information-seeking queries.

 The evaluation was carried out using a series of automated metric, as well as an LLM-as-a-judge apporach suing the Prometheus evaluation library.
