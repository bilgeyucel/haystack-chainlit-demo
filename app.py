import os
import chainlit as cl

from haystack.agents.base import Tool
from haystack.agents.conversational import ConversationalAgent
from haystack.agents.memory import ConversationSummaryMemory
from haystack.nodes import PromptNode, WebRetriever, PromptTemplate
from haystack.pipelines import WebQAPipeline
from haystack.agents.types import Color

search_api_key = os.environ.get("SEARCH_API_KEY")
if not search_api_key:
    raise ValueError("Please set the SEARCH_API_KEY environment variable")
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

web_prompt = """
Synthesize a comprehensive answer from the following most relevant paragraphs and the given question.
Provide a clear and concise answer, no longer than 10-20 words.
\n\n Paragraphs: {documents} \n\n Question: {query} \n\n Answer:
"""

web_prompt_node = PromptNode(
    "gpt-3.5-turbo", default_prompt_template=PromptTemplate(prompt=web_prompt), api_key=openai_api_key
)

web_retriever = WebRetriever(api_key=search_api_key, top_search_results=3, mode="snippets")
pipeline = WebQAPipeline(retriever=web_retriever, prompt_node=web_prompt_node)
web_qa_tool = Tool(
    name="Search",
    pipeline_or_node=pipeline,
    description="useful for when you need to Google questions if you cannot find answers in the the previous conversation",
    output_variable="results",
    logging_color=Color.MAGENTA,
)

conversational_agent_prompt_node = PromptNode(
    "gpt-4",
    api_key=openai_api_key,
    max_length=256,
    stop_words=["Observation:"],
    model_kwargs={"temperature": 0.5, "top_p": 0.9},
)
memory = ConversationSummaryMemory(conversational_agent_prompt_node, summary_frequency=2)

agent = ConversationalAgent(
    prompt_node=conversational_agent_prompt_node, tools=[web_qa_tool], memory=memory
)

cl.HaystackAgentCallbackHandler(agent)

@cl.on_message
async def main(message: str):
    response = await cl.make_async(agent.run)(message)
    await cl.Message(author="Agent", content=response["answers"][0].answer).send()