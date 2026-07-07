import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import asyncio
from dotenv import load_dotenv

# Load environment variables (Make sure FIREWORKS_API_KEY, OPENAI_API_KEY, and LANGSMITH_API_KEY are set)
load_dotenv()

# Enable LangSmith Tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "Activity1_RAG_Eval"

from langchain_fireworks import ChatFireworks
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

import pandas as pd
from ragas import evaluate, EvaluationDataset
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics import answer_correctness, faithfulness, context_precision

# 1. Define the Models
# Replace the Fireworks endpoint with your specific deployed endpoint string if needed.
# Using 'gpt-4o-mini' for the OpenAI baseline (or 'gpt-4.1-mini' if available in your org)
fireworks_endpoint = os.environ.get("FIREWORKS_CHAT_MODEL", "accounts/fireworks/models/mixtral-8x7b-instruct") # Placeholder
llm_fireworks = ChatFireworks(model=fireworks_endpoint, api_key=os.environ.get("FIREWORKS_API_KEY"))
llm_openai = ChatOpenAI(model="gpt-4o-mini", api_key=os.environ.get("OPENAI_API_KEY"))

# 2. Define a Dummy Retriever (for demonstration)
def dummy_retriever(query: str) -> str:
    # In a real app, this would search a vector database
    return "A woodchuck burrowing might displace roughly 700 pounds of dirt, which folklore converts to 'wood'."

# 3. Create RAG Chains
prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer the question based only on the provided context: {context}"),
    ("human", "{question}")
])

def create_rag_chain(llm):
    return (
        {"context": dummy_retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

chain_fireworks = create_rag_chain(llm_fireworks).with_config({"run_name": "Fireworks_RAG"})
chain_openai = create_rag_chain(llm_openai).with_config({"run_name": "OpenAI_RAG"})

# 4. Dataset for Evaluation
eval_dataset = [
    {
        "question": "How much wood would a woodchuck chuck?",
        "reference": "About 700 pounds, based on the volume of dirt they typically excavate."
    },
    {
        "question": "What is a woodchuck's main activity in the context of the riddle?",
        "reference": "In reality, they dig dirt to create burrows, rather than chucking wood."
    }
]

# Evaluation wrapper
def predict_fireworks(inputs: dict) -> dict:
    answer = chain_fireworks.invoke(inputs["question"])
    return {"output": answer, "context": dummy_retriever(inputs["question"])}

def predict_openai(inputs: dict) -> dict:
    answer = chain_openai.invoke(inputs["question"])
    return {"output": answer, "context": dummy_retriever(inputs["question"])}

# 5. Evaluation wrapper for Ragas (v0.2.x+ format)
def generate_ragas_dataset(predict_func, dataset):
    samples = []
    
    for item in dataset:
        # Generate the answer using the pipeline
        result = predict_func({"question": item["question"]})
        
        # Create a SingleTurnSample for each evaluation point
        sample = SingleTurnSample(
            user_input=item["question"],
            retrieved_contexts=[result["context"]],
            response=result["output"],
            reference=item["reference"]
        )
        samples.append(sample)
        
    return EvaluationDataset(samples=samples)

def evaluate_models():
    print("Generating answers for Fireworks AI...")
    fw_dataset = generate_ragas_dataset(predict_fireworks, eval_dataset)
    
    print("Generating answers for OpenAI...")
    openai_dataset = generate_ragas_dataset(predict_openai, eval_dataset)

    # The metrics requested: 
    # context_precision = retrieval quality
    # faithfulness = answer faithfulness
    # answer_correctness = end-to-end accuracy
    metrics = [context_precision, faithfulness, answer_correctness]

    print("\nRunning Ragas Evaluation for Fireworks AI...")
    results_fw = evaluate(dataset=fw_dataset, metrics=metrics, llm=llm_fireworks, embeddings=OpenAIEmbeddings())
    print("Fireworks Results:")
    print(results_fw)
    
    print("\nRunning Ragas Evaluation for OpenAI...")
    results_openai = evaluate(dataset=openai_dataset, metrics=metrics, llm=llm_openai, embeddings=OpenAIEmbeddings())
    print("OpenAI Results:")
    print(results_openai)

if __name__ == "__main__":
    evaluate_models()
