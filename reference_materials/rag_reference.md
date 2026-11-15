
# Reference Material: Introduction to RAG

## 1. What is RAG?

RAG stands for Retrieval-Augmented Generation.

It is an AI architecture that combines information retrieval with the text-generation capabilities of a Large Language Model (LLM).

Instead of depending only on information learned during its training, an LLM-based application using RAG retrieves relevant information from an external knowledge source and supplies that information to the model before generating an answer.

The retrieved information acts as additional context for generating the response.

RAG does not inherently retrain or fine-tune the language model whenever a user asks a question.

## 2. Why do we need RAG?

Large Language Models have knowledge acquired during their training.

However, relying only on this knowledge can create several problems:

1. The model might not know information that was created after its training.
2. The model might not have access to private organizational information.
3. The model might produce incorrect or unsupported answers.
4. Updating the model's knowledge through fine-tuning can require additional training processes.

RAG addresses these limitations by allowing an application to retrieve relevant information from external sources at query time.

Examples of external knowledge sources include:

- Company documents.
- Employee handbooks.
- Product manuals.
- Research papers.
- Websites.
- Databases.
- Internal knowledge bases.

## 3. How does RAG work?

A typical RAG application has two major stages.

### Stage A: Document indexing (preparation stage)

Before users ask questions, the application prepares its knowledge source.

Step 1: Document ingestion

Documents are collected from sources such as PDFs, websites, text files or databases.

Step 2: Document processing

The application extracts usable text from the documents and processes it.

Step 3: Chunking

Large documents are divided into smaller pieces called chunks.

A chunk represents a smaller section of a document.

Chunking makes it easier to retrieve specific information instead of supplying an entire document to the LLM.

Step 4: Embedding generation

An embedding model converts each text chunk into a numerical representation called an embedding.

These numerical representations can help a search system identify text with similar meaning.

Step 5: Indexing and storage

The application stores the original text, embeddings and associated metadata in a searchable index or database.

A vector database is commonly used for vector similarity search, although RAG can also use keyword search or hybrid search.

### Stage B: Retrieval and generation (when a user asks a question)

Step 1: User query

The user submits a question to the application.

Example:

"What is the leave policy of my company?"

Step 2: Query processing

The application processes the user's question to prepare it for retrieval.

Depending on the retrieval method, it might convert the question into an embedding.

Step 3: Retrieval

The retriever searches the indexed knowledge source and identifies relevant chunks.

For example, it might retrieve paragraphs from the company's employee handbook that explain leave policies.

Step 4: Augmentation

The retrieved information is combined with the user's original question and instructions.

This creates an augmented prompt containing relevant external context.

Step 5: Generation

The augmented prompt is supplied to the LLM.

The LLM generates an answer using the retrieved information as context.

## 4. Important components of RAG

### Large Language Model (LLM)

A language model capable of understanding and generating text.

Its responsibility in a typical RAG application is to generate the final response using the supplied context.

### Document

An information source such as a PDF, text file, website or database record.

### Chunk

A smaller section created by dividing a larger document into manageable pieces.

### Embedding

A numerical representation of text that captures useful semantic information.

Embeddings allow text to be compared based on similarity of meaning.

### Embedding Model

A model that converts text into numerical embeddings.

### Retriever

A component responsible for finding relevant information from an indexed knowledge source.

### Vector Database

A database or vector index designed to store and search numerical vector representations.

It is commonly used to retrieve semantically similar document chunks.

### Context

The retrieved information supplied to the LLM to help it generate an informed response.

### Index

An organized data structure that supports efficient searching and retrieval.

## 5. Practical example: Company HR chatbot

Imagine an organization has an employee handbook containing information about:

- Leave policies.
- Salary policies.
- Working hours.
- Holidays.
- Employee benefits.

An employee asks:

"How many paid leaves can I take?"

Without RAG, the LLM might not know the organization's actual leave policy.

With RAG:

1. The employee asks the question.
2. The application searches the employee handbook.
3. The retriever finds the relevant leave-policy sections.
4. The retrieved information is supplied to the LLM.
5. The LLM generates an answer using the retrieved policy information.

The LLM is not required to memorize the organization's employee handbook during training.

It receives the relevant information as context when answering the question.

## 6. Benefits of RAG

1. External information can be used without retraining the LLM.
2. Knowledge can be updated by updating the external information source and its index.
3. Responses can be grounded in retrieved documents.
4. It can provide access to private or domain-specific information.
5. Relevant source information can support answer traceability.

## 7. Limitations of RAG

1. Incorrect or irrelevant retrieval can produce poor answers.
2. Incomplete source documents can lead to incomplete responses.
3. Poor chunking can affect retrieval quality.
4. Embedding and retrieval quality influence the final response.
5. RAG does not guarantee that an LLM will always produce a factually correct answer.
6. The system must maintain its external knowledge sources and indexes.

## 8. RAG versus Fine-Tuning

RAG and fine-tuning solve different problems.

RAG retrieves external information and supplies it to the LLM as context when generating a response.

Fine-tuning involves additional training of a model using selected training examples to modify its learned behaviour.

RAG is generally useful when an application needs access to external, frequently updated or private information.

Fine-tuning is generally useful when a model needs to adapt its behaviour, style or task-specific capabilities.

They can also be used together.

## 9. Important distinction

RAG does not guarantee the elimination of hallucinations.

The quality of the final response depends on several factors:

- Quality of the source documents.
- Document-processing quality.
- Chunking strategy.
- Retrieval accuracy.
- Relevance of supplied context.
- LLM's ability to use the supplied context correctly.

A RAG application should evaluate both retrieval quality and generated-answer quality.

## 10. References

The following sources provide the technical foundation for this document.

1. Original RAG research paper:

https://arxiv.org/abs/2005.11401

Title: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

2. Microsoft Learn:

https://learn.microsoft.com/en-us/azure/foundry/concepts/retrieval-augmented-generation

Topic: Retrieval-Augmented Generation and indexes.

3. AWS Prescriptive Guidance:

https://docs.aws.amazon.com/prescriptive-guidance/latest/retrieval-augmented-generation-options/

Topic: Retrieval-Augmented Generation options and architectures.

4. Google Cloud:

https://cloud.google.com/use-cases/retrieval-augmented-generation

Topic: What is Retrieval-Augmented Generation?
